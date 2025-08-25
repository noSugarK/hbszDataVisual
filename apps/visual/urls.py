# apps/visual/urls.py
from django.urls import path
from . import views

app_name = 'visual'

urlpatterns = [
    path('', views.chart_hnt, name='chart_hnt'),
    path('chart-hntdata/', views.chart_hntdata, name='chart_hntdata'),
    path('hnt-bar/', views.chart_hnt_bar, name='chart_hnt_bar'),
    path('hnt-bar-data/', views.chart_hnt_bar_data, name='chart_hnt_bar_data'),
    path('hnt-line/', views.chart_hnt_line, name='chart_hnt_line'),
    path('hnt-line-data/', views.chart_hnt_line_data, name='chart_hnt_line_data'),

]
