# apps/users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import UserLoginForm, UserRegisterForm
from .models import User


def user_login(request):
    """用户登录视图"""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # 使用Django的认证系统
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'欢迎回来，{username}！')
                # 修复重定向逻辑
                next_page = request.GET.get('next', 'visual:dashboard')  # 默认重定向到仪表板
                try:
                    return redirect(next_page)
                except:
                    # 如果next_page无效，则重定向到仪表板
                    return redirect('visual:dashboard')
            else:
                messages.error(request, '用户名或密码不正确。')
        else:
            messages.error(request, '请输入有效的用户名和密码。')
    else:
        form = UserLoginForm()

    return render(request, 'login.html', {'form': form})


@login_required
def user_logout(request):
    """用户登出视图"""
    logout(request)
    messages.success(request, '您已成功退出登录。')
    return redirect('users:login')


@login_required
def user_list(request):
    """用户列表视图"""
    # 检查用户是否为管理员
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('visual:dashboard')

    # 获取所有用户
    users_list = User.objects.all().order_by('-date_joined')

    # 分页处理
    paginator = Paginator(users_list, 20)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    context = {
        'users': users,
        'title': '用户管理'
    }
    return render(request, 'user_list.html', context)


@login_required
def user_register(request):
    """用户注册视图"""
    # 检查用户是否为管理员
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('visual:dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'用户 {user.username} 创建成功！')
            return redirect('users:user_list')
        else:
            messages.error(request, '请检查输入的信息。')
    else:
        form = UserRegisterForm()

    context = {
        'form': form,
        'title': '注册新用户'
    }
    return render(request, 'user_register.html', context)


@login_required
def user_detail(request, user_id):
    """用户详情视图"""
    # 检查用户是否为管理员
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('visual:dashboard')

    user = get_object_or_404(User, id=user_id)

    context = {
        'view_user': user,
        'title': f'用户详情 - {user.username}'
    }
    return render(request, 'user_detail.html', context)


@login_required
def user_profile(request):
    """用户个人资料视图"""
    context = {
        'title': '个人资料'
    }
    return render(request, 'profile.html', context)
