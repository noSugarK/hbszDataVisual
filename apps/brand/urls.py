# apps/common/urls.py
from django.urls import path
from . import views

app_name = 'brand'

urlpatterns = [
    # 品牌
    path('list/', views.brand_list, name='brand_list'),
    path('add/', views.brand_add, name='brand_add'),
    path('<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('<int:brand_id>/delete/', views.brand_delete, name='brand_delete'),
]
