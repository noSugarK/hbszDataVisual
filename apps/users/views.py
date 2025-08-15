# apps/users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.hashers import check_password
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
                next_page = request.GET.get('next', 'projects:dashboard')  # 默认重定向到仪表板
                try:
                    return redirect(next_page)
                except:
                    # 如果next_page无效，则重定向到仪表板
                    return redirect('projects:dashboard')
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
    # 检查用户是否为管理员或超级管理员
    if not request.user.is_admin and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('projects:dashboard')

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
    # 检查用户是否为管理员或超级管理员
    if not request.user.is_admin and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('projects:dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request_user=request.user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'用户 {user.username} 创建成功！')
            return redirect('users:user_list')
        else:
            messages.error(request, '请检查输入的信息。')
    else:
        form = UserRegisterForm(request_user=request.user)

    context = {
        'form': form,
        'title': '注册新用户'
    }
    return render(request, 'user_register.html', context)


@login_required
def user_detail(request, user_id):
    """用户详情视图"""
    # 检查用户是否为管理员或超级管理员
    if not request.user.is_admin and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('projects:dashboard')

    user = get_object_or_404(User, id=user_id)

    context = {
        'view_user': user,
        'title': f'用户详情 - {user.username}'
    }
    return render(request, 'user_detail.html', context)


@login_required
def user_profile(request):
    """用户个人资料视图"""
    if request.method == 'POST':
        # 获取表单数据
        email = request.POST.get('email', request.user.email)
        phone = request.POST.get('phone', request.user.phone or '')

        # 更新基本信息
        request.user.email = email
        request.user.phone = phone

        # 处理密码修改
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if current_password or new_password or confirm_password:
            # 需要修改密码
            if not current_password:
                messages.error(request, '请输入当前密码。')
                return render(request, 'profile.html', {'title': '个人资料'})

            # 验证当前密码
            if not check_password(current_password, request.user.password):
                messages.error(request, '当前密码不正确。')
                return render(request, 'profile.html', {'title': '个人资料'})

            # 验证新密码
            if not new_password:
                messages.error(request, '请输入新密码。')
                return render(request, 'profile.html', {'title': '个人资料'})

            if new_password != confirm_password:
                messages.error(request, '两次输入的新密码不一致。')
                return render(request, 'profile.html', {'title': '个人资料'})

            if len(new_password) < 6:
                messages.error(request, '密码长度至少为6位。')
                return render(request, 'profile.html', {'title': '个人资料'})

            # 设置新密码
            request.user.set_password(new_password)
            request.user.save()

            # 密码修改后需要重新登录
            messages.success(request, '个人信息更新成功！由于您修改了密码，请重新登录。')
            logout(request)
            return redirect('users:login')

        request.user.save()
        messages.success(request, '个人信息更新成功！')
        return redirect('users:profile')

    context = {
        'title': '个人资料'
    }
    return render(request, 'profile.html', context)


@login_required
def user_edit(request, user_id):
    """编辑用户信息视图"""
    # 检查权限：超级管理员可以编辑所有用户，用户可以编辑自己的信息
    user = get_object_or_404(User, id=user_id)

    # 普通用户只能编辑自己的信息
    if not request.user.is_superuser:
        if request.user != user:
            messages.error(request, '您没有权限访问此页面。')
            return redirect('projects:dashboard')

    if request.method == 'POST':
        # 获取表单数据
        email = request.POST.get('email', user.email)
        phone = request.POST.get('phone', user.phone or '')

        # 权限更新（仅超级管理员可以修改其他用户的权限）
        if request.user.is_superuser and not user.is_superuser:
            permission = request.POST.get('permission', user.permission)
            user.permission = permission

        # 更新基本信息
        user.email = email
        user.phone = phone

        # 处理密码修改
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if current_password or new_password or confirm_password:
            # 需要修改密码
            if not current_password:
                messages.error(request, '请输入当前密码。')
                return render(request, 'user_edit.html', {
                    'edit_user': user,
                    'current_permission': user.permission if not user.is_superuser else 'superuser',
                    'title': f'编辑用户信息 - {user.username}'
                })

            # 验证当前密码
            if not check_password(current_password, user.password):
                messages.error(request, '当前密码不正确。')
                return render(request, 'user_edit.html', {
                    'edit_user': user,
                    'current_permission': user.permission if not user.is_superuser else 'superuser',
                    'title': f'编辑用户信息 - {user.username}'
                })

            # 验证新密码
            if not new_password:
                messages.error(request, '请输入新密码。')
                return render(request, 'user_edit.html', {
                    'edit_user': user,
                    'current_permission': user.permission if not user.is_superuser else 'superuser',
                    'title': f'编辑用户信息 - {user.username}'
                })

            if new_password != confirm_password:
                messages.error(request, '两次输入的新密码不一致。')
                return render(request, 'user_edit.html', {
                    'edit_user': user,
                    'current_permission': user.permission if not user.is_superuser else 'superuser',
                    'title': f'编辑用户信息 - {user.username}'
                })

            if len(new_password) < 6:
                messages.error(request, '密码长度至少为6位。')
                return render(request, 'user_edit.html', {
                    'edit_user': user,
                    'current_permission': user.permission if not user.is_superuser else 'superuser',
                    'title': f'编辑用户信息 - {user.username}'
                })

            # 设置新密码
            user.set_password(new_password)
            # 如果用户修改了自己的密码，需要重新登录
            if request.user == user:
                messages.success(request, '用户信息更新成功！由于您修改了密码，请重新登录。')
                user.save()
                logout(request)
                return redirect('users:login')

        user.save()
        messages.success(request, f'用户 {user.username} 的信息更新成功！')

        # 如果是超级管理员编辑其他用户，返回用户列表
        if request.user.is_superuser and request.user != user:
            return redirect('users:user_list')
        else:
            # 如果是用户编辑自己的信息，返回个人资料页
            return redirect('users:profile')

    # GET请求 - 显示编辑表单
    current_permission = user.permission if not user.is_superuser else 'superuser'

    context = {
        'edit_user': user,
        'current_permission': current_permission,
        'title': f'编辑用户信息 - {user.username}'
    }
    return render(request, 'user_edit.html', context)
