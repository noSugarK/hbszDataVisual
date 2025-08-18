# apps/visual/urls.py
from django.urls import path
from . import views

app_name = 'visual'

urlpatterns = [
    path('', views.chart_hnt, name='chart_hnt'),
    path('chart-hntdata/', views.chart_hntdata, name='chart_hntdata'),
]
