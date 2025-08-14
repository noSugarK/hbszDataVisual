# apps/common/views.py
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Region, ConcretePrice, Supplier, Brand
from ..projects.models import Project, ProjectMapping
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


@login_required
def supplier_list(request):
    """供应商列表"""
    # 检查权限：只有管理员可以查看供应商列表
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('common:home')

    suppliers_list = Supplier.objects.all()
    paginator = Paginator(suppliers_list, 20)
    page_number = request.GET.get('page')
    suppliers = paginator.get_page(page_number)

    context = {
        'suppliers': suppliers,
        'title': '供应商列表'
    }
    return render(request, 'supplier_list.html', context)


@login_required
def supplier_add(request):
    """添加供应商"""
    # 检查权限：只有管理员可以添加供应商
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name')

        if supplier_name:
            if Supplier.objects.filter(supplier_name=supplier_name).exists():
                messages.error(request, '供应商名称已存在！')
            else:
                Supplier.objects.create(
                    supplier_name=supplier_name
                )
                messages.success(request, '供应商添加成功！')
                return redirect('common:supplier_list')
        else:
            messages.error(request, '请填写供应商名称！')

    context = {
        'title': '添加供应商'
    }
    return render(request, 'supplier_add.html', context)


@login_required
def supplier_edit(request, supplier_id):
    """编辑供应商"""
    # 检查权限：只有管理员可以编辑供应商
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name')

        if supplier_name:
            # 检查供应商名称是否已存在（排除当前供应商）
            if Supplier.objects.filter(supplier_name=supplier_name).exclude(id=supplier_id).exists():
                messages.error(request, '供应商名称已存在！')
            else:
                supplier.supplier_name = supplier_name
                supplier.save()
                messages.success(request, '供应商更新成功！')
                return redirect('common:supplier_list')
        else:
            messages.error(request, '请填写供应商名称！')

    context = {
        'supplier': supplier,
        'title': '编辑供应商'
    }
    return render(request, 'supplier_edit.html', context)


@login_required
def supplier_delete(request, supplier_id):
    """删除供应商"""
    # 检查权限：只有管理员可以删除供应商
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        # 检查是否有项目关联到这个供应商
        if Project.objects.filter(supplier=supplier).exists():
            messages.error(request, '无法删除该供应商，因为还有项目使用它。')
            return redirect('common:supplier_list')

        supplier_name = supplier.supplier_name
        supplier.delete()
        messages.success(request, f'供应商 "{supplier_name}" 删除成功！')
        return redirect('common:supplier_list')

    context = {
        'supplier': supplier,
        'title': '删除供应商'
    }
    return render(request, 'supplier_delete.html', context)

@login_required
def brand_list(request):
    """品牌列表"""
    # 检查权限：只有管理员可以查看品牌列表
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('common:home')

    brands_list = Brand.objects.all()
    paginator = Paginator(brands_list, 20)
    page_number = request.GET.get('page')
    brands = paginator.get_page(page_number)

    context = {
        'brands': brands,
        'title': '品牌列表'
    }
    return render(request, 'brand_list.html', context)


@login_required
def brand_add(request):
    """添加品牌"""
    # 检查权限：只有管理员可以添加品牌
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    if request.method == 'POST':
        brand_name = request.POST.get('brand_name')
        description = request.POST.get('description', '')

        if brand_name:
            if Brand.objects.filter(brand_name=brand_name).exists():
                messages.error(request, '品牌名称已存在！')
            else:
                Brand.objects.create(
                    brand_name=brand_name,
                    description=description
                )
                messages.success(request, '品牌添加成功！')
                return redirect('common:brand_list')
        else:
            messages.error(request, '请填写品牌名称！')

    context = {
        'title': '添加品牌'
    }
    return render(request, 'brand_add.html', context)


@login_required
def brand_edit(request, brand_id):
    """编辑品牌"""
    # 检查权限：只有管理员可以编辑品牌
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        brand_name = request.POST.get('brand_name')
        description = request.POST.get('description', '')

        if brand_name:
            # 检查品牌名称是否已存在（排除当前品牌）
            if Brand.objects.filter(brand_name=brand_name).exclude(id=brand_id).exists():
                messages.error(request, '品牌名称已存在！')
            else:
                brand.brand_name = brand_name
                brand.description = description
                brand.save()
                messages.success(request, '品牌更新成功！')
                return redirect('common:brand_list')
        else:
            messages.error(request, '请填写品牌名称！')

    context = {
        'brand': brand,
        'title': '编辑品牌'
    }
    return render(request, 'brand_edit.html', context)


@login_required
def brand_delete(request, brand_id):
    """删除品牌"""
    # 检查权限：只有管理员可以删除品牌
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限执行此操作。')
        return redirect('common:home')

    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        # 检查是否有项目关联到这个品牌
        if Project.objects.filter(brand=brand).exists():
            messages.error(request, '无法删除该品牌，因为还有项目使用它。')
            return redirect('common:brand_list')

        brand_name = brand.brand_name
        brand.delete()
        messages.success(request, f'品牌 "{brand_name}" 删除成功！')
        return redirect('common:brand_list')

    context = {
        'brand': brand,
        'title': '删除品牌'
    }
    return render(request, 'brand_delete.html', context)