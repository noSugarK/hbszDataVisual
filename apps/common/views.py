from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Region, ConcretePrice

def home(request):
    """首页视图"""
    context = {
        'title': '首页'
    }
    return render(request, 'home.html', context)

def about(request):
    """关于页面"""
    return render(request, 'about.html')

def help_view(request):
    """帮助页面"""
    return render(request, 'help.html')
