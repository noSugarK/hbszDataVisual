# apps/visual/urls.py
from django.urls import path
from . import views

app_name = 'visual'
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('chart-data/', views.chart_data, name='chart_data'),
    path('project/add/', views.project_add, name='project_add'),
    path('project/', views.project_list, name='project_list'),
    path('get-districts/', views.get_districts, name='get_districts'),
    path('get-project-mapping-info', views.get_project_mapping_info, name='get_project_mappings_info'),
    path('get-specifications/', views.get_specifications, name='get_specifications'),
    path('debug-regions/', views.debug_regions, name='debug_regions'),  # 临时调试用
    path('project-mapping/add/', views.project_mapping_add, name='project_mapping_add'),
    path('project-mapping/list/', views.project_mapping_list, name='project_mapping_list'),

]
