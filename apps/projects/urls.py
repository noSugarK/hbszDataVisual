# apps/projects/urls.py
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('project/add/', views.project_add, name='project_add'),
    path('project/list/', views.project_list, name='project_list'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('project/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('project-mapping/add/', views.project_mapping_add, name='project_mapping_add'),
    path('project-mapping/list/', views.project_mapping_list, name='project_mapping_list'),
    path('project-mapping/<int:mapping_id>/', views.project_mapping_detail, name='project_mapping_detail'),
    path('project-mapping/<int:mapping_id>/edit/', views.project_mapping_edit, name='project_mapping_edit'),
    path('project-mapping/<int:mapping_id>/delete/', views.project_mapping_delete, name='project_mapping_delete'),
    path('api/districts/', views.get_districts, name='get_districts'),
    path('api/project-mapping-info/', views.get_project_mapping_info, name='get_project_mapping_info'),
    path('api/specifications/', views.get_specifications, name='get_specifications'),

    # 地区管理
    path('region/list/', views.region_list, name='region_list'),
    path('region/add/', views.region_add, name='region_add'),
    path('region/<int:region_id>/edit/', views.region_edit, name='region_edit'),
    path('region/<int:region_id>/delete/', views.region_delete, name='region_delete'),

    # 物资类别管理
    path('category/list/', views.category_list, name='category_list'),
    path('category/add/', views.category_add, name='category_add'),
    path('category/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('category/<int:category_id>/delete/', views.category_delete, name='category_delete'),

    # 规格管理
    path('specification/list/', views.specification_list, name='specification_list'),
    path('specification/add/', views.specification_add, name='specification_add'),
    path('specification/<int:spec_id>/edit/', views.specification_edit, name='specification_edit'),
    path('specification/<int:spec_id>/delete/', views.specification_delete, name='specification_delete'),

    path('chart-data/', views.chart_data, name='chart_data'),
]
