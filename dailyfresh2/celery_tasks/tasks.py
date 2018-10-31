
from celery import Celery
from django.core.mail import send_mail


app = Celery('celery_tasks.tasks', broker='redis://192.168.12.191/2')


import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh2.settings")
django.setup()

@app.task
def task_send_mail(subject, message,sender,receiver,html_message):
    print('start...')
    send_mail(subject, message, sender, receiver, html_message=html_message)
    print('end...')


'''
1.broker开启redis: sudo redis-server /etc/redis/redis.conf
2.worker查看过程：celery -A celery_tasks.tasks worker -l info
'''





# from goods.models import GoodsType,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
# from django.template import loader
# from django.conf import settings
# from celery import Celery
#
#
#
# app = Celery('celery_tasks.tasks', broker='redis://192.168.12.191/2')
#
#
# import os
# import django
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh2.settings")
# django.setup()
#
# @app.task
# def task_generate_static_index():
#     '''产生首页静态文件'''
#     print('生成静态文件begin...')
#
#     # 获取商品的种类信息
#     types = GoodsType.objects.all()
#     # 获取首页轮播商品信息
#     goods_banners = IndexGoodsBanner.objects.all().order_by('index')
#     # 获取首页促销活动信息
#     promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
#     for type in types:
#         # 获取type种类首页分类商品的图片展示信息
#         image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
#         # 获取type种类首页分类商品的文字展示信息
#         title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
#         # 动态的给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
#         type.image_banners = image_banners
#         type.title_banners = title_banners
#
#     context = {
#         'title': '天天生鲜-首页',
#         'guest_cart': 1,
#         'cart_count': 0,
#         'types': types,
#         'goods_banners': goods_banners,
#         'promotion_banners': promotion_banners,
#     }
#
#     #使用模板
#     #1.加载模板文件，返回模板对象
#     temp=loader.get_template('static_index.html')
#     #模板渲染
#     static_index_html=temp.render(context)
#
#     #生成首页对应静态文件
#     save_path=os.path.join(settings.BASE_DIR,'static/html/index.html')
#     with open(save_path,'w') as file:
#         file.write(static_index_html)
#
#     print('生成静态首页end...')
