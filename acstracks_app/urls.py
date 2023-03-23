from django.urls import path, re_path, reverse_lazy
from . import classviews, views

urlpatterns = [
    path('', views.track_list, name='track_list'),
    path('track/<int:pk>', views.track_detail, name='track_detail'),
    path('preference/', views.process_preferences, name='preference'),
    path('cleanup/', views.cleanup, name='cleanup'),
    path('statistics/', views.show_statistics, name='show_statistics'),
    path('heatmap/<str:profile>,<str:year>', views.heatmap, name='heatmap'),
    path('heatmap/<str:profile>', views.heatmap, name='heatmap'),
    path('heatmap/', views.heatmap, name='heatmap'),
    path('publish/', views.publish, name='publish'),
    path('unpublish/<str:profile>', views.unpublish, name='unpublish'),
    path(
        'publictrack/<str:publickey>',
        views.publictrack_detail,
        name='publictrack_detail'
        ),
    re_path(r'^login/$', classviews.MyLoginView.as_view(), name='login'),
    re_path(r'^password/$', classviews.MyPasswordChangeView.as_view(
        success_url=reverse_lazy('track_list'),
        template_name='registration/password.html'
        ), name='password'),
    re_path(r'^logout/$', views.logout_view, name='logout'),
]
