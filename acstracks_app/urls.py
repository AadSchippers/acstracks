from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    url(r'^track/(?P<pk>\d+)/$', views.track_detail, name='track_detail'),
    url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
]
