from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from apps.category.models import MaterialCategory
from apps.projects.models import Project
from apps.projects.views import admin_required
from apps.specification.models import Specification


@login_required
@admin_required
def specification_list(request):
    """规格列表"""
    specifications = Specification.objects.select_related('category').all()

    context = {
        'specifications': specifications,
        'title': '规格管理'
    }
    return render(request, 'specification_list.html', context)


@login_required
@admin_required
def specification_add(request):
    """添加规格"""
    if request.method == 'POST':
        category_id = request.POST.get('category')
        specification_name = request.POST.get('specification_name')

        if category_id and specification_name:
            try:
                category = MaterialCategory.objects.get(id=category_id)
                # 检查同一类别下规格名称是否重复
                if Specification.objects.filter(category=category, specification_name=specification_name).exists():
                    messages.error(request, '该类别下已存在同名规格！')
                else:
                    Specification.objects.create(
                        category=category,
                        specification_name=specification_name
                    )
                    messages.success(request, '规格添加成功！')
                    return redirect('specification:specification_list')
            except MaterialCategory.DoesNotExist:
                messages.error(request, '选择的物资类别不存在！')
        else:
            messages.error(request, '请填写所有必填字段！')

    categories = MaterialCategory.objects.all()
    context = {
        'categories': categories,
        'title': '添加规格'
    }
    return render(request, 'specification_add.html', context)


@login_required
@admin_required
def specification_edit(request, spec_id):
    """编辑规格"""
    specification = get_object_or_404(Specification, id=spec_id)

    if request.method == 'POST':
        category_id = request.POST.get('category')
        specification_name = request.POST.get('specification_name')

        if category_id and specification_name:
            try:
                category = MaterialCategory.objects.get(id=category_id)
                # 检查同一类别下规格名称是否重复（排除当前规格）
                if Specification.objects.filter(
                        category=category,
                        specification_name=specification_name
                ).exclude(id=spec_id).exists():
                    messages.error(request, '该类别下已存在同名规格！')
                else:
                    specification.category = category
                    specification.specification_name = specification_name
                    specification.save()
                    messages.success(request, '规格更新成功！')
                    return redirect('specification:specification_list')
            except MaterialCategory.DoesNotExist:
                messages.error(request, '选择的物资类别不存在！')
        else:
            messages.error(request, '请填写所有必填字段！')

    categories = MaterialCategory.objects.all()
    context = {
        'specification': specification,
        'categories': categories,
        'title': '编辑规格'
    }
    return render(request, 'specification_edit.html', context)


@login_required
@admin_required
def specification_delete(request, spec_id):
    """删除规格"""
    specification = get_object_or_404(Specification, id=spec_id)

    if request.method == 'POST':
        # 检查是否有项目关联到这个规格
        if Project.objects.filter(specification=specification).exists():
            messages.error(request, '无法删除该规格，因为还有项目使用它。')
            return redirect('specification:specification_list')

        spec_name = str(specification)
        specification.delete()
        messages.success(request, f'规格 "{spec_name}" 删除成功！')
        return redirect('specification:specification_list')

    context = {
        'specification': specification,
        'title': '删除规格'
    }
    return render(request, 'specification_delete.html', context)
