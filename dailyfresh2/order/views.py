from django.shortcuts import render,redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.conf import settings
from goods.models import GoodsSKU
from user.models import Address
from django.http import *
from order.models import OrderInfo,OrderGoods
import datetime
from django.db import transaction
import os
from alipay import AliPay
from utils.user_util import LoginRequiredMixin

class OrderPlaceView(LoginRequiredMixin,View):

    def post(self,request):
        '''提交订单页面显示'''
        # 获取登录用户
        user=request.user
        #获取用户的收货地址
        try:
          address=Address.objects.get(user=user, is_default=True)
        except Address.DoesNotExist:
            address = None

        # 连接redis
        conn = settings.REDIS_CONN
        cart_key = 'cart_%d' % user.id

        # 临时变量:保存商品的总价格和总数目
        skus = []
        total_sku_amount = 0
        total_count = 0
        sku_ids = request.POST.getlist('sku_ids')
        sku_count = request.POST.get('sku_count')
        print(sku_count)
        if sku_count:
            for sku_id in sku_ids:
                try:
                  sku=GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    pass
                count=int(sku_count)
                #小计
                amount=sku.prince*count
                # 面向对象的动态语言:动态给sku对象绑定 count 和 amount
                sku.amount=amount
                sku.count=count
                skus.append(sku)
                # 累计金额和数量
                total_sku_amount+=amount
                total_count+=count
                #将获取的商品id和商品数存到redis
                conn.hset(cart_key,sku_id,sku_count)
        else:

            if not sku_ids:
                return redirect(reverse('cart:info'))
            #遍历sku_ids获取用户要购买的商品信息
            for sku_id in sku_ids:

                sku = GoodsSKU.objects.get(id=sku_id)
                count = conn.hget(cart_key, sku_id)
                # 小计
                count = int(count)
                amount = sku.prince *count
                # 面向对象的动态语言:动态给sku对象绑定 count 和 amount
                sku.amount = amount
                sku.count = count
                skus.append(sku)

                # 累计金额和数量
                total_sku_amount += amount
                total_count += count

        sku_ids = ','.join(sku_ids)  # [1,25]->1,25
        #运费
        transit_price=10
        total_pay= transit_price+total_sku_amount

        context = {
            'page_name': 1,
            'skus': skus,
            'total_sku_amount': total_sku_amount,
            'total_count': total_count,
            'total_pay':total_pay,
            'transit_price':transit_price,
            'address': address,
            'sku_ids':sku_ids
        }

        return render(request, 'order/place_order.html', context)

class OrderCommitView(LoginRequiredMixin,View):
    '''订单创建'''

    # ####轻松开启事务
    @transaction.atomic
    def post(self,request):

        # 获取登录用户
        user = request.user
        # 用户未登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        #接收参数
        addr_id=request.POST.get('addr_id')
        pay_method=request.POST.get('pay_method')
        sku_ids=request.POST.get('sku_ids')

        # 校验数据是否完整
        if not all([addr_id,sku_ids, pay_method]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            pay_method=int(pay_method)
        except ValueError:
            return JsonResponse({'res': 2, 'errmsg': '支护方式不存在'})

        if pay_method not in dict(OrderInfo.PAY_METHOD_CHOICES).keys():
            return JsonResponse({'res': 3, 'errmsg': '非法支护方式'})

        # 校验用户的收货地址
        try:
            address = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':4, 'errmsg': '地址不存在'})

        #todo:创建订单核心业务

        #组织参数
        #订单id:时间戳＋用户id
        order_id=datetime.datetime.today().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 运费
        transit_price = 10

        #总金额和数量
        total_sku_amount=0

        total_count=0

        #### 创建事务保存点
        save_point = transaction.savepoint()

        try:
            #todo:向df_order_info表添加一条订单记录
            order=OrderInfo.objects.create(
                order_id=order_id,
                user=user,
                addr=address,
                pay_method=pay_method,
                total_count=total_count,
                total_price=total_sku_amount,
                transit_price=transit_price,
            )
            #todo:用户订单中有几个商品，需要向df_order_goods表中加入几条记录
            # 连接redis
            conn = settings.REDIS_CONN
            cart_key = 'cart_%d' % user.id

            sku_ids=sku_ids.split(',')
            for sku_id in sku_ids:
                # '''每个订单有三次下单的机会'''
                for i in range(3):
                    try:
                        sku=GoodsSKU.objects.get(id=sku_id)

                        '''1.悲观锁：锁定被查询行直到事务结束'''
                        # sku = GoodsSKU.objects.select_for_update().get(id=sku_id)

                        '''2.使用乐观锁'''
                        #保留原来的库存
                        old_stock = sku.stock

                    except GoodsSKU.DoesNotExist:
                        # # 回滚到保存点
                        # transaction.savepoint_rollback(save_point)

                        return JsonResponse({'res':5, 'errmsg': '商品不存在'})

                    #从redis中查看用户所买商品数量
                    count=conn.hget(cart_key,sku_id)
                    count = int(count)
                    # 校验商品的库存
                    if int(count) > sku.stock:
                        # # 回滚到保存点
                        # transaction.savepoint_rollback(save_point)

                        return JsonResponse({'res':6, 'errmsg': '商品库存不足'})
                    # print("1uid:%s,stock:%s"%(user.id,sku.stock))
                    #
                    # import time
                    # time.sleep(10)

                    # #### 创建事务保存点
                    # save_point = transaction.savepoint()

                    # '''使用乐观锁'''
                    new_stock=old_stock-count
                    result=GoodsSKU.objects.filter(id=sku_id,stock=old_stock).update(stock=new_stock)
                    # print("2uid:%s,stock:%s,result:%s" % (user.id, sku.stock,result))
                    if result==0 and i<2:
                        # 还有机会,继续重新下单
                        continue
                    elif result==0 and i==2:
                        # 异常,回滚
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'res':7, 'errmsg': '下单异常'})

                        continue
                    # todo:向df_order_goods表添加一条记录
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.prince,
                    )
                    #更新商品的库存和销量

                    sku.stock-=count
                    sku.sales+=count
                    sku.save()

                    #累加计算订单商品的总数量和总价格
                    amount=sku.prince*count
                    total_sku_amount += amount
                    total_count += count

                    #结束循环
                    break

            #更新订单信息表中商品的总数量和总价格
            order.total_price=total_sku_amount
            order.total_count=total_count
            order.save()

        except Exception as e:
            print(e)
            # '''出现任何异常都强制回滚'''
            transaction.savepoint_rollback(save_point)
            return JsonResponse({'res': 7, 'errmsg':'下单失败'})

        #todo:清除购物车中对应记录
        conn.hdel(cart_key,sku_ids)

        return JsonResponse({'res':8, 'message': '创建成功'})

class OrderPayView(LoginRequiredMixin,View):
    '''订单支付'''
    def post(self, request):
        # 用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})
        try:
            order = OrderInfo.objects.get(user=user,
                                          order_id=order_id,
                                          pay_method=3,
                                          order_status=1)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '订单不存在'})

        app_private_key_string=os.path.join(settings.BASE_DIR, 'order/app_private_key.pem')
        alipay_public_key_string=os.path.join(settings.BASE_DIR, 'order/app_public_key.pem')
        # 业务初始化
        # 使用Python  sdk 调用支付宝接口
        alipay = AliPay(
            appid="2016092000551734",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=app_private_key_string,
            alipay_public_key_path=alipay_public_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        subject = '天天生鲜%s' % order_id
        total_pay = order.total_price + order.transit_price  # Decimal

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject=subject,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class CheckPayView(LoginRequiredMixin,View):
    '''检查用户支付情况'''

    def post(self, request):
        # 用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})
        try:
            order = OrderInfo.objects.get(user=user,
                                          order_id=order_id,
                                          pay_method=3,
                                          order_status=1)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '订单不存在'})

        app_private_key_string=os.path.join(settings.BASE_DIR, 'order/app_private_key.pem')
        alipay_public_key_string=os.path.join(settings.BASE_DIR, 'order/app_public_key.pem')
        # 业务初始化
        # 使用Python  sdk 调用支付宝接口
        alipay = AliPay(
            appid="2016092000551734",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=app_private_key_string,
            alipay_public_key_path=alipay_public_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 调用支付宝的交易查询接口
        while True:
            response=alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no #支付编号
                order.order_status = 4  # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败，可能一会就会成功
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                print(code)
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class CommentView(LoginRequiredMixin,View):
    '''用户评论内容'''
    def get(self,request,order_id):
        # 获取用户订单信息
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("orders:info"))
        order.skus = []
        order_skus = order.ordergoods_set.all()
        for order_sku in order_skus:
            sku = order_sku.sku
            sku.count = order_sku.count
            sku.amount = sku.prince * sku.count
            order.skus.append(sku)
        context = {'title': '用户评价页面', 'page_name': 1, 'page': 3,'order':order}
        return render(request,'user/user_center_comment.html',context)

    def post(self,request,order_id):
        """处理评论内容"""
        # 获取用户订单信息
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("order:info"))
        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)
        sku_ids = []
        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = content
            order_goods.save()
            sku_ids.append(sku_id)

        order.save()
        return redirect(reverse("goods:detail", kwargs={"goods_id": sku_ids[0]}))


















