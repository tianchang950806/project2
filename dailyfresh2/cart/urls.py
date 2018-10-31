from django.conf.urls import url
from . import views



urlpatterns=[

    url(r'^add$', views.CarAddView.as_view(), name='add'),
    #购物车页面
    url(r'^$', views.CarInfoView.as_view(), name='info'),
    #购物车更新
    url(r'^update$', views.CarUpdateView.as_view(), name='update'),
    # 购物车删除
    url(r'^delete$', views.CarDeleteView.as_view(), name='delete'),
    #获取购物车商品总数
    url(r'^count$', views.CarCountView.as_view(), name='count'),
]