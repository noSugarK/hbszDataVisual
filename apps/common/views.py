# apps/common/views.py
from django.shortcuts import render
from ..projects.models import Project, ProjectMapping
from ..region.models import Region
from ..users.models import User


def home(request):
    """首页视图"""
    context = {
        'title': '首页'
    }

    # 如果用户已登录且是管理员，添加统计信息
    if request.user.is_authenticated and request.user.is_admin:
        context.update({
            'projects_count': Project.objects.count(),
            'users_count': User.objects.count(),
            'regions_count': Region.objects.count(),
            'project_mappings_count': ProjectMapping.objects.count(),
        })

    return render(request, 'home.html', context)


def about(request):
    """关于页面"""
    return render(request, 'about.html')


def help_view(request):
    """帮助页面"""
    return render(request, 'help.html')

