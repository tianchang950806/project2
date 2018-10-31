from django.conf.urls import url
from . import views



urlpatterns=[

    url(r'^recover/(\d+)$', views.RecoverView.as_view(), name='recover'),
    url(r'^check/(\d+)$', views.CheckView.as_view(), name='check'),

]