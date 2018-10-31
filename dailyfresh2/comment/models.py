from django.db import models
from db.base_model import BaseModel


class Comment(BaseModel):
    user = models.ForeignKey('user.User', verbose_name='用户')
    sku=models.ForeignKey('goods.GoodsSKU', verbose_name='商品SKU')
    content = models.CharField(verbose_name='内容', max_length=300)

    class Meta:
        db_table = 'df_goods_comment'
        verbose_name = '商品评价'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.content[:10]
