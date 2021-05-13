from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path(
        '<int:intermediate_points_selected>',
        views.track_list,
        name='track_list'
        ),
    path(
        '<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.track_list,
        name='track_list'
        ),
    path('track/<int:pk>', views.track_detail, name='track_detail'),
    path(
        'track/<int:pk>,<str:date_start>,<str:date_end>,' +
        '<str:order_selected>,<str:profile_filter>,' +
        '<int:intermediate_points_selected>',
        views.track_detail,
        name='track_detail'
        ),
    path('preference/', views.process_preferences, name='preference'),
    path(
        'preference/,<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.process_preferences,
        name='preference'
        ),
    path('cleanup/', views.cleanup, name='cleanup'),
    path(
        'statistics/' +
        '<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.show_statistics,
        name='show_statistics'
        ),
    path(
        'heatmap/<str:new_profile>,<str:new_year>,<str:new_date_start>,' +
        '<str:new_date_end>,' +
        '<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.heatmap,
        name='heatmap'
        ),
    path(
        'heatmap/<str:new_profile>,<str:new_year>,' +
        '<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.heatmap,
        name='heatmap'
        ),
    path(
        'heatmap/' +
        '<str:date_start>,<str:date_end>,<str:order_selected>,' +
        '<str:profile_filter>,<int:intermediate_points_selected>',
        views.heatmap,
        name='heatmap'
        ),
    path(
        'publictrack/<str:publickey>',
        views.publictrack_detail,
        name='publictrack_detail'
        ),
    path(
        'publictrack/<str:publickey>,<int:intermediate_points_selected>',
        views.publictrack_detail,
        name='publictrack_detail'
        ),
    url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
]
