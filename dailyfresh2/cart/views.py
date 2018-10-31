from django.shortcuts import render
from django.views.generic import View
from django.http import *
from goods.models import GoodsSKU
from django.conf import settings
from utils.user_util import LoginRequiredMixin



class CarInfoView(LoginRequiredMixin,View):
    '''购物车页面'''
    def get(self,request):
        user=request.user
        if user.is_authenticated():
            # 连接redis
            conn = settings.REDIS_CONN
            # 添加key
            cart_key = 'cart_%d' % user.id
            # 获取信息
            cart_dict = conn.hgetall(cart_key)
            # 临时变量:
            skus = []
            total_sku_amount = 0
            total_count = 0
            # 遍历获取商品的信息
            for sku_id, count in cart_dict.items():
                try:
                  sku=GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    pass
                count=int(count)
                #小计
                amount=sku.prince*count
                # 面向对象的动态语言:动态给sku对象绑定 count 和 amount
                sku.amount=amount
                sku.count=count
                skus.append(sku)
                # 累计金额和数量
                total_sku_amount+=amount
                total_count+=count
            context={
                'page_name': 1,
                'skus':skus,
                'total_sku_amount':total_sku_amount,
                'total_count':total_count,
            }
            return render(request,'cart/cart.html', context)

class CarAddView(LoginRequiredMixin,View):
    '''实现添加购物车'''
    def post(self,request):
        '''购物车记录添加'''
        #获取登录用户
        user=request.user
        #用户未登录
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'请先登录'})

        #接收数据
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')


        #校验数据是否完整
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据不完整'})

        #校验添加的商品数量
        try:
            count=int(count)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg': '商品数目出错'})

        #校验商品是否存在
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        #业务处理：添加购物车记录

        conn=settings.REDIS_CONN
        # 添加key
        cart_key = 'cart_%d' % user.id
        #先尝试获取sku_id的值－－＞hget(cart_key,属性)
        #如果sku_id在hash中不存在,hget返回None
        cart_count=conn.hget(cart_key,sku_id)

        if cart_count:
            #累加购物车中商品的数目
            count+=int(cart_count)
        #校验商品的库存
        if count>sku.stock:
            return JsonResponse({'res':4, 'errmsg': '商品库存不足'})

        #设置hash中sku_id对应的值
        #hset-->如果sku_id已经存在，更新数据，如果sku_id不存在，添加数据
        conn.hset(cart_key,sku_id,count)

        total_count=get_cart_count(user)
        return JsonResponse({'res': 5,'total_count':total_count, 'errmsg': '添加成功'})

def get_cart_count(user):
    '''获取用户的购物车购买商品总数'''

    #保存用户购物车中商品的总数目
    total_count=0
    if user.is_authenticated():
        #连接redis
        conn = settings.REDIS_CONN
        # 添加key
        cart_key = 'cart_%d' % user.id
        #获取信息
        cart_dict=conn.hgetall(cart_key)

        #遍历获取商品的信息
        for sku_id,count in cart_dict.items():
            total_count+=int(count)

    return total_count


class CarUpdateView(LoginRequiredMixin,View):
    '''更新购物车'''
    def post(self,request):
        user = request.user
        # 用户未登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：更新购物车记录
        conn = settings.REDIS_CONN
        # 添加key
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        #更新数据
        conn.hset(cart_key, sku_id, count)

        return JsonResponse({'res': 5, 'errmsg': '更新成功'})

class CarDeleteView(LoginRequiredMixin,View):
    def post(self,request):
        user = request.user
        # 用户未登录
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：删除购物车记录
        conn = settings.REDIS_CONN
        # 添加key
        cart_key = 'cart_%d' % user.id
        #删除
        conn.hdel(cart_key,sku_id)

        return JsonResponse({'res': 4,'errmsg': '删除成功'})

class CarCountView(LoginRequiredMixin,View):
    def get(self,request):
        # 获取登录用户
        user = request.user
        # 保存用户购物车中商品的总数目
        total_count = 0
        if user.is_authenticated():
            # 连接redis
            conn = settings.REDIS_CONN
            # 添加key
            cart_key = 'cart_%d' % user.id
            # 获取信息
            cart_dict = conn.hgetall(cart_key)

            # 遍历获取商品的信息
            for sku_id, count in cart_dict.items():
                total_count += int(count)

        return JsonResponse({'total_count':total_count})





