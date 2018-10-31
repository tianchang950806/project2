from django.shortcuts import render,redirect
from .models import *
from django.views.generic import View
from fdfs_client.client import Fdfs_client
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.urlresolvers import reverse
from redis import *
from order.models import OrderInfo,OrderGoods
from utils.user_util import LoginRequiredMixin


class IndexView(LoginRequiredMixin,View):
    def get(self,request):
        #获取缓存中的数据
        context=cache.get('goods_index')
        if context==None:
            print('设置了缓存...')
            #获取商品的种类信息
            types=GoodsType.objects.all()
            #获取首页轮播商品信息
            goods_banners=IndexGoodsBanner.objects.all().order_by('index')
            # 获取首页促销活动信息
            promotion_banners=IndexPromotionBanner.objects.all().order_by('index')
            for type in types:
                #获取type种类首页分类商品的图片展示信息
                image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')
                #获取type种类首页分类商品的文字展示信息
                title_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
                #动态的给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners=image_banners
                type.title_banners=title_banners

            context = {
                'title': '天天生鲜-首页',
                'guest_cart':1,
                'types':types,
                'goods_banners':goods_banners,
                'promotion_banners':promotion_banners,
            }
            #设置缓存
            cache.set('goods_index',context,3600)

        # 获取用户购物车中商品的数目，暂时设置为0,待完善
        cart_count = 0
        context.update(cart_count=cart_count)

        return render(request, 'goods/index.html',context)



class ListView(LoginRequiredMixin,View):
    def get(self,request,tid,pindex):
        # 获取商品的种类信息
        types = GoodsType.objects.all()

        type= GoodsType.objects.get(id=tid)
        # 获取新品信息
        news_SKU=GoodsSKU.objects.filter(type=type).order_by('create_time')[:2]

        sort=request.GET.get('sort')
        if sort=='prince':
            goods_list= GoodsSKU.objects.filter(type=type).order_by('prince')
        elif sort=='sales':
            goods_list = GoodsSKU.objects.filter(type=type).order_by('sales')
        else:
            goods_list = GoodsSKU.objects.filter(type=type).order_by('id')
            sort = 'default'
        #对数据进行分页
        paginator = Paginator(goods_list,1)
        try:
            pindex=int(pindex)
        except Exception as e:
            pindex=1

        if pindex>paginator.num_pages:
            pindex=1
        #获取第pindex的Page实例对象
        sku_page = paginator.page(pindex)

        #todo:进行页码的控制，页面上最多显示５个页码
        #1.总页数小于５页，页面上显示所有页码
        #2.如果当前页是前３页，显示１-5页
        #3.如果当前页是后３页，显示后５页
        #4.其他情况，显示当页的前２页　当页的后２页
        num_pages=paginator.num_pages
        if num_pages<5:
            pages=range(1,num_pages+1)
        elif pindex<=3:
            pages=range(1,6)
        elif num_pages-pindex<=2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(pindex-2,pindex+3)

        context={
            'tilte':'天天生鲜-列表页',
            'guest_cart': 1,
            'news_SKU':news_SKU,
            'sku_page':sku_page,
            'type':type,
            'sort':sort,
            'pages':pages,
            'types':types,
        }
        return render(request,'goods/list.html',context)


class DetailView(LoginRequiredMixin,View):
    '''详情页'''
    def get(self,request,goods_id):
        '''显示详情页'''
        # 获取商品的种类信息
        types = GoodsType.objects.all()
        try:
            sku=GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        #获取新品信息
        news_SKU=GoodsSKU.objects.filter(type=sku.type).order_by('create_time')[:2]

        #获取同一个SPU的其他规格商品
        same_spu_skus=GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        #获取订单的评论信息
        sku_orders=sku.ordergoods_set.all().order_by('create_time')[:30]
        if sku_orders:
            for sku_order in sku_orders:
                sku_order.ctime=sku_order.create_time
                sku_order.username=sku_order.sku.name

        user=request.user
        if user.is_authenticated():
            #添加用户的历史记录
            #连接redis
            conn=StrictRedis('192.168.12.191')
            #添加key
            history_key='history_%d'%user.id
            #移除列表中的good_id
            conn.lrem(history_key,0,goods_id)
            #把good_id插入到列表左侧
            conn.lpush(history_key,goods_id)
            #只保存用户最新浏览的５条信息
            conn.ltrim(history_key,0,4)

        context = {
            'tilte': '天天生鲜-列表页',
            'guest_cart': 1,
            'sku':sku,
            'news_SKU':news_SKU,
            'types':types,
            'same_spu_skus':same_spu_skus,
            'sku_orders':sku_orders

        }
        # 获取用户购物车中商品的数目，暂时设置为0,待完善
        cart_count = 0
        context.update(cart_count=cart_count)

        return render(request, 'goods/detail.html', context)




