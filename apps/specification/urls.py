# apps/specification/urls.py
from django.urls import path
from . import views

app_name = 'specification'

urlpatterns = [
    # 规格管理
    path('list/', views.specification_list, name='specification_list'),
    path('add/', views.specification_add, name='specification_add'),
    path('<int:spec_id>/edit/', views.specification_edit, name='specification_edit'),
    path('<int:spec_id>/delete/', views.specification_delete, name='specification_delete'),

]
