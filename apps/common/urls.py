# apps/common/urls.py
from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('help/', views.help_view, name='help'),
    path('supplier/list/', views.supplier_list, name='supplier_list'),
    path('supplier/add/', views.supplier_add, name='supplier_add'),
    path('supplier/<int:supplier_id>/edit/', views.supplier_edit, name='supplier_edit'),
    path('supplier/<int:supplier_id>/delete/', views.supplier_delete, name='supplier_delete'),
    path('brand/list/', views.brand_list, name='brand_list'),
    path('brand/add/', views.brand_add, name='brand_add'),
    path('brand/<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('brand/<int:brand_id>/delete/', views.brand_delete, name='brand_delete'),
]
