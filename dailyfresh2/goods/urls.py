from django.conf.urls import url
from . import views

urlpatterns=[
    url(r'^$',views.index,name='index'),
    url(r'^detail/$',views.detail,name='detail'),
    url(r'^list/$',views.list,name='list'),


]