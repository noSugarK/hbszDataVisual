# apps/users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('list/', views.user_list, name='user_list'),
    path('register/', views.user_register, name='user_register'),
    path('detail/<int:user_id>/', views.user_detail, name='user_detail'),
    path('edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('profile/', views.user_profile, name='profile'),
]
