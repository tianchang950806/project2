from django.conf.urls import url
from . import views

urlpatterns=[
    url(r'^index$',views.IndexView.as_view(),name='index'),
    url(r'^list/(\d+)/(\d+)$',views.ListView.as_view(),name='list'),
    url(r'^detail/(?P<goods_id>.*)$',views.DetailView.as_view(),name='detail'),
]