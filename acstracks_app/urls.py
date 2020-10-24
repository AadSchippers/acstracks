from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path('<int:intermediate_points_selected>', views.track_list, name='track_list'),
    path('<str:order_selected>,<str:profile_filter>,<int:intermediate_points_selected>', views.track_list, name='track_list'),
    path('track/<int:pk>', views.track_detail, name='track_detail'),
    path('track/<int:pk>,<str:order_selected>,<str:profile_filter>,<int:intermediate_points_selected>', views.track_detail, name='track_detail'),
    path('threshold/', views.threshold, name='threshold'),
    path('threshold/,<str:order_selected>,<str:profile_filter>,<int:intermediate_points_selected>', views.threshold, name='threshold'),
    url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
]
