from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from apps.projects.models import Project
from apps.supplier.models import Supplier


# Create your views here.
@login_required
def supplier_list(request):
    """供应商列表"""
    # 检查权限：只有管理员可以查看供应商列表
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限访问此页面。')
        return redirect('supplier:home')

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
        return redirect('supplier:home')

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
                return redirect('supplier:supplier_list')
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
        return redirect('supplier:home')

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
                return redirect('supplier:supplier_list')
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
        return redirect('supplier:home')

    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        # 检查是否有项目关联到这个供应商
        if Project.objects.filter(supplier=supplier).exists():
            messages.error(request, '无法删除该供应商，因为还有项目使用它。')
            return redirect('supplier:supplier_list')

        supplier_name = supplier.supplier_name
        supplier.delete()
        messages.success(request, f'供应商 "{supplier_name}" 删除成功！')
        return redirect('supplier:supplier_list')

    context = {
        'supplier': supplier,
        'title': '删除供应商'
    }
    return render(request, 'supplier_delete.html', context)
