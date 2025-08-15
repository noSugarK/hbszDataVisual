from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.category.models import MaterialCategory
from apps.projects.models import Project
from apps.projects.views import admin_required
from apps.specification.models import Specification


@login_required
@admin_required
def category_list(request):
    """物资类别列表"""
    categories = MaterialCategory.objects.all()

    context = {
        'categories': categories,
        'title': '物资类别管理'
    }
    return render(request, 'category_list.html', context)


@login_required
@admin_required
def category_add(request):
    """添加物资类别"""
    if request.method == 'POST':
        category_name = request.POST.get('category_name')

        if category_name:
            if MaterialCategory.objects.filter(category_name=category_name).exists():
                messages.error(request, '物资类别名称已存在！')
            else:
                MaterialCategory.objects.create(category_name=category_name)
                messages.success(request, '物资类别添加成功！')
                return redirect('category:category_list')
        else:
            messages.error(request, '请填写物资类别名称！')

    context = {
        'title': '添加物资类别'
    }
    return render(request, 'category_add.html', context)


@login_required
@admin_required
def category_edit(request, category_id):
    """编辑物资类别"""
    category = get_object_or_404(MaterialCategory, id=category_id)

    if request.method == 'POST':
        category_name = request.POST.get('category_name')

        if category_name:
            # 检查是否重复（排除当前类别）
            if MaterialCategory.objects.filter(category_name=category_name).exclude(id=category_id).exists():
                messages.error(request, '物资类别名称已存在！')
            else:
                category.category_name = category_name
                category.save()
                messages.success(request, '物资类别更新成功！')
                return redirect('category:category_list')
        else:
            messages.error(request, '请填写物资类别名称！')

    context = {
        'category': category,
        'title': '编辑物资类别'
    }
    return render(request, 'category_edit.html', context)


@login_required
@admin_required
def category_delete(request, category_id):
    """删除物资类别"""
    category = get_object_or_404(MaterialCategory, id=category_id)

    if request.method == 'POST':
        # 检查是否有规格或项目关联到这个类别
        if Specification.objects.filter(category=category).exists():
            messages.error(request, '无法删除该物资类别，因为还有规格使用它。')
            return redirect('category:category_list')

        if Project.objects.filter(category=category).exists():
            messages.error(request, '无法删除该物资类别，因为还有项目使用它。')
            return redirect('category:category_list')

        category_name = category.category_name
        category.delete()
        messages.success(request, f'物资类别 "{category_name}" 删除成功！')
        return redirect('category:category_list')

    context = {
        'category': category,
        'title': '删除物资类别'
    }
    return render(request, 'category_delete.html', context)
