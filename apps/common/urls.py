# apps/common/urls.py
from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('help/', views.help_view, name='help'),
]
