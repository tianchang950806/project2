# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0003_auto_20181024_1047'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodssku',
            name='status',
            field=models.SmallIntegerField(default=1, verbose_name='商品状态', choices=[(0, '下线'), (1, '上线')]),
        ),
    ]
