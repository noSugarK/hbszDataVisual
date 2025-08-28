# apps/price/urls.py
from django.urls import path
from . import views, predict_view

app_name = 'price'

urlpatterns = [
    path('list/', views.price_list, name='price_list'),
    path('add/', views.price_add, name='price_add'),
    path('<int:price_id>/edit/', views.price_edit, name='price_edit'),
    path('<int:price_id>/delete/', views.price_delete, name='price_delete'),
    path('chart/', views.price_chart, name='price_chart'),
    path('chart-data/', views.price_chart_data, name='price_chart_data'),
    path('predict/', predict_view.price_predict_page, name='price_predict_page'),
    path('predict/api/', predict_view.price_predict_api, name='price_predict_api'),
]