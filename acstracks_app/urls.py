from django.urls import path
from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    url(r'^track/(?P<pk>\d+)/$', views.track_detail, name='track_detail'),
]