# apps/projects/urls.py
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.project_add, name='project_add'),
    path('excel/', views.project_excel, name='project_excel'),
    path('list/', views.project_list, name='project_list'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    path('<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('mapping/add/', views.project_mapping_add, name='project_mapping_add'),
    path('mapping/excel/', views.project_mapping_excel, name='project_mapping_excel'),
    path('mapping/list/', views.project_mapping_list, name='project_mapping_list'),
    path('mapping/<int:mapping_id>/', views.project_mapping_detail, name='project_mapping_detail'),
    path('mapping/<int:mapping_id>/edit/', views.project_mapping_edit, name='project_mapping_edit'),
    path('mapping/<int:mapping_id>/delete/', views.project_mapping_delete, name='project_mapping_delete'),
    path('api/districts/', views.get_districts, name='get_districts'),
    path('api/project-mapping-info/', views.get_project_mapping_info, name='get_project_mapping_info'),
    path('api/specifications/', views.get_specifications, name='get_specifications'),
]
