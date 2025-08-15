# apps/category/urls.py
from django.urls import path
from . import views

app_name = 'category'

urlpatterns = [
    # 物资类别管理
    path('list/', views.category_list, name='category_list'),
    path('add/', views.category_add, name='category_add'),
    path('<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('<int:category_id>/delete/', views.category_delete, name='category_delete'),

]
