from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.dashboard_login, name='dashboard_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),
    path('', views.dashboard_home, name='dashboard_home'),

    path('henvendelser/', views.dashboard_inquiries, name='dashboard_inquiries'),
    path('henvendelser/<int:pk>/', views.dashboard_inquiry_detail, name='dashboard_inquiry_detail'),

    path('prosjekter/', views.dashboard_projects, name='dashboard_projects'),
    path('prosjekter/nytt/', views.dashboard_project_create, name='dashboard_project_create'),
    path('prosjekter/rekkefolge/', views.dashboard_projects_reorder, name='dashboard_projects_reorder'),
    path('prosjekter/papirkurv/', views.dashboard_project_trash, name='dashboard_project_trash'),
    path('prosjekter/<int:pk>/rediger/', views.dashboard_project_edit, name='dashboard_project_edit'),
    path('prosjekter/<int:pk>/bilder/', views.dashboard_project_image_upload, name='dashboard_project_image_upload'),
    path('prosjekter/<int:pk>/bilder/ferdig/', views.dashboard_project_images_done, name='dashboard_project_images_done'),
    path('prosjekter/<int:pk>/dupliser/', views.dashboard_project_duplicate, name='dashboard_project_duplicate'),
    path('prosjekter/<int:pk>/slett/', views.dashboard_project_delete, name='dashboard_project_delete'),
    path('prosjekter/<int:pk>/gjenopprett/', views.dashboard_project_restore, name='dashboard_project_restore'),
    path('prosjekter/<int:pk>/slett-permanent/', views.dashboard_project_purge, name='dashboard_project_purge'),
    path('prosjekter/bilde/<int:pk>/slett/', views.dashboard_project_image_delete, name='dashboard_project_image_delete'),

    path('tomter/', views.dashboard_plots, name='dashboard_plots'),
    path('tomter/ny/', views.dashboard_plot_create, name='dashboard_plot_create'),
    path('tomter/<int:pk>/rediger/', views.dashboard_plot_edit, name='dashboard_plot_edit'),
    path('tomter/<int:pk>/status/', views.dashboard_plot_status, name='dashboard_plot_status'),
    path('tomter/<int:pk>/slett/', views.dashboard_plot_delete, name='dashboard_plot_delete'),

    path('nyheter/', views.dashboard_blog, name='dashboard_blog'),
    path('nyheter/ny/', views.dashboard_blog_create, name='dashboard_blog_create'),
    path('nyheter/<int:pk>/rediger/', views.dashboard_blog_edit, name='dashboard_blog_edit'),
    path('nyheter/<int:pk>/slett/', views.dashboard_blog_delete, name='dashboard_blog_delete'),

    path('aktivitet/', views.dashboard_activity, name='dashboard_activity'),
]
