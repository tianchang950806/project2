from django.conf.urls import url
from . import views
from .views import OrderView

urlpatterns=[
    url(r'^$',OrderView.as_view(),name='place_order')
]