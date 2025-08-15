# apps/region/urls.py
from django.urls import path
from . import views

app_name = 'region'

urlpatterns = [
    # 地区管理
    path('list/', views.region_list, name='region_list'),
    path('add/', views.region_add, name='region_add'),
    path('<int:region_id>/edit/', views.region_edit, name='region_edit'),
    path('<int:region_id>/delete/', views.region_delete, name='region_delete'),
]
