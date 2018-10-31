from django.contrib import admin
from .models import *
from django.core.cache import cache

class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''新增或更新表中的数据调用'''
        super().save_model(request, obj, form, change)
        #发出任务，让celery work重新生成首页静态文件
        # from celery_tasks.tasks import task_generate_static_index
        # task_generate_static_index.delay()
        cache.delete('goods_index')


    def delete_model(self,request, obj):
        '''删除表中数据时调用'''
        super().save_model(request, obj)
        # from celery_tasks.tasks import task_generate_static_index
        # task_generate_static_index.delay()
        cache.delete('goods_index')


class GoodsSKUAdmin(BaseAdmin):
    pass

class GoodsTypeAdmin(BaseAdmin):
    pass

class GoodsAdmin(BaseAdmin):
    pass



admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(Goods,GoodsAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)
admin.site.register(GoodsImage)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexTypeGoodsBanner)
admin.site.register(IndexPromotionBanner)