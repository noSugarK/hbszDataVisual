from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from apps.brand.models import Brand
from apps.projects.models import Project


# Create your views here.
@login_required
def brand_list(request):
    """品牌列表"""
    # 检查权限：只有管理员可以查看品牌列表
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('brand:home')

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
        return redirect('brand:home')

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
                return redirect('brand:brand_list')
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
        return redirect('brand:home')

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
                return redirect('brand:brand_list')
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
        return redirect('brand:home')

    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        # 检查是否有项目关联到这个品牌
        if Project.objects.filter(brand=brand).exists():
            messages.error(request, '无法删除该品牌，因为还有项目使用它。')
            return redirect('brand:brand_list')

        brand_name = brand.brand_name
        brand.delete()
        messages.success(request, f'品牌 "{brand_name}" 删除成功！')
        return redirect('brand:brand_list')

    context = {
        'brand': brand,
        'title': '删除品牌'
    }
    return render(request, 'brand_delete.html', context)