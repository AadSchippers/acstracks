from django.urls import path, reverse_lazy
from django.conf.urls import url
from . import classviews, views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path('track/<int:pk>', views.track_detail, name='track_detail'),
    path('preference/', views.process_preferences, name='preference'),
    path('cleanup/', views.cleanup, name='cleanup'),
    path('statistics/', views.show_statistics, name='show_statistics'),
    path('heatmap/<str:profile>,<str:year>', views.heatmap, name='heatmap'),
    path('heatmap/', views.heatmap, name='heatmap'),
    path('publish/', views.publish, name='publish'),
    path(
        'publictrack/<str:publickey>',
        views.publictrack_detail,
        name='publictrack_detail'
        ),
    path(
        'public/<str:username>/<str:profile>',
        views.public_tracks,
        name='public_tracks'
        ),
    path('public/<str:username>', views.public_tracks, name='public_tracks'),
    path('public', views.public_tracks, name='public_tracks'),
    url(r'^login/$', classviews.MyLoginView.as_view(), name='login'),
    url(r'^password/$', classviews.MyPasswordChangeView.as_view(
        success_url=reverse_lazy('track_list'),
        template_name='registration/password.html'
        ), name='password'),
    url(r'^logout/$', views.logout_view, name='logout'),
]
