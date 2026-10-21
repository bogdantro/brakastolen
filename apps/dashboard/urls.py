from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.dashboard_login, name='dashboard_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),
    path('', views.dashboard_home, name='dashboard_home'),

    path('henvendelser/', views.dashboard_inquiries, name='dashboard_inquiries'),
    path('henvendelser/<int:pk>/', views.dashboard_inquiry_detail, name='dashboard_inquiry_detail'),

    path('tomter/', views.dashboard_plots, name='dashboard_plots'),
    path('tomter/ny/', views.dashboard_plot_create, name='dashboard_plot_create'),
    path('tomter/flere/', views.dashboard_plots_bulk, name='dashboard_plots_bulk'),
    path('tomter/kategorier/', views.dashboard_plot_categories, name='dashboard_plot_categories'),
    path('tomter/<int:pk>/rediger/', views.dashboard_plot_edit, name='dashboard_plot_edit'),
    path('tomter/<int:pk>/hurtig/', views.dashboard_plot_quick, name='dashboard_plot_quick'),
    path('tomter/<int:pk>/slett/', views.dashboard_plot_delete, name='dashboard_plot_delete'),

    path('nyheter/', views.dashboard_blog, name='dashboard_blog'),
    path('nyheter/ny/', views.dashboard_blog_create, name='dashboard_blog_create'),
    path('nyheter/<int:pk>/rediger/', views.dashboard_blog_edit, name='dashboard_blog_edit'),
    path('nyheter/<int:pk>/slett/', views.dashboard_blog_delete, name='dashboard_blog_delete'),

    path('aktivitet/', views.dashboard_activity, name='dashboard_activity'),
]
