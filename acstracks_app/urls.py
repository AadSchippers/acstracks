from django.urls import path
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path('track/<int:pk>', views.track_detail, name='track_detail'),
    path('preference/', views.process_preferences, name='preference'),
    path('cleanup/', views.cleanup, name='cleanup'),
    path('statistics/', views.show_statistics, name='show_statistics'),
    path('heatmap/<str:profile>,<str:year>', views.heatmap, name='heatmap'),
    path('heatmap/', views.heatmap, name='heatmap'),
    path(
        'publictrack/<str:publickey>',
        views.publictrack_detail,
        name='publictrack_detail'
        ),
    url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_view, name='logout'),
]
