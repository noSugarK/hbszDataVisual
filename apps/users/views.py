# apps/users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserLoginForm, UserRegisterForm

def user_login(request):
    """用户登录"""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, f'欢迎回来，{username}！')
                # 重定向到用户试图访问的页面，或者首页
                next_page = request.GET.get('next', 'common:home')
                return redirect(next_page)
            else:
                messages.error(request, '用户名或密码错误')
    else:
        form = UserLoginForm()
    return render(request, 'login.html', {'form': form})

def user_register(request):
    """用户注册"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, '注册成功，请登录')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def user_logout(request):
    """用户登出"""
    logout(request)
    messages.success(request, '您已成功退出登录。')
    return redirect('home')

@login_required
def profile(request):
    """用户个人资料"""
    return render(request, 'profile.html')
