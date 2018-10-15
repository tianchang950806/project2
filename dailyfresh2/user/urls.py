from django.conf.urls import url
from . import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    url(r'^register$',views.RegisterView.as_view() ,name='register'),
    url(r'^active/(?P<token>.*)$',views.ActiveView.as_view() ,name='active'),

    url(r'^login$',views.LoginView.as_view(),name='login'),
    url(r'^validate_code$', views.validate_code, name='validate_code'),

    url(r'^forget$',views.ForgetPwdView.as_view(),name='forget'),
    url(r'^reset/(?P<token>.*)$',views.ResetPwdView.as_view(),name='reset'),
    url(r'modify$',views.ModifyPwdView.as_view(),name='modify'),

    url(r'^info$',views.UserInfoView.as_view(),name='info'),  #用户信息页
    url(r'^order$',views.UserOrderView.as_view(),name='order'),#用户订单页
    url(r'^site$',views.UserSiteView.as_view(),name='site'), #用户收货地址页
]