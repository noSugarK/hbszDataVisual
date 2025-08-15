# apps/projects/views.py
from functools import wraps

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import Project, ProjectMapping, Specification, MaterialCategory, Brand
from ..common.models import ConcretePrice
from ..region.models import Region
from ..supplier.models import Supplier
from ..users.models import User
from .forms import ProjectForm

def admin_required(view_func):
    """
    自定义装饰器，只允许管理员访问
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not (request.user.is_admin or request.user.is_staff):
            messages.error(request, '您没有权限访问此页面。')
            return redirect('common:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# 用于调试的视图
def debug_regions(request):
    """
    调试地区数据
    """
    from django.http import HttpResponse

    html = "<h2>地区数据调试</h2>"

    # 显示所有市级数据
    html += "<h3>市级数据:</h3><ul>"
    cities = Region.objects.filter(district='')
    for city in cities:
        html += f"<li>ID: {city.id}, 城市: {city.city}, 区县: '{city.district}'</li>"
    html += "</ul>"

    # 显示前10个区县数据
    html += "<h3>区县数据(前10条):</h3><ul>"
    districts = Region.objects.exclude(district='').order_by('city')[:10]
    for district in districts:
        html += f"<li>ID: {district.id}, 城市: {district.city}, 区县: '{district.district}'</li>"
    html += "</ul>"

    return HttpResponse(html)


# apps/projects/views.py
@login_required
def project_add(request):
    if request.method == 'POST':
        print("POST数据:", request.POST)  # 调试信息
        form = ProjectForm(request.POST)
        if form.is_valid():
            print("表单有效")  # 调试信息
            project = form.save(commit=False)
            project.user = request.user  # 自动设置当前用户为填表人
            print("准备保存项目:", project)  # 调试信息
            project.save()
            messages.success(request, '项目数据保存成功！')
            return redirect('projects:project_list')
        else:
            print("表单错误:", form.errors)  # 调试信息
            messages.error(request, '表单数据有误，请检查后重新提交。')
    else:
        form = ProjectForm()

    # 获取所有项目映射数据，包含地区信息
    project_mappings = ProjectMapping.objects.select_related('region').all()
    categories = MaterialCategory.objects.all()
    brands = Brand.objects.all()
    suppliers = Supplier.objects.all()  # 获取所有供应商

    context = {
        'form': form,
        'project_mappings': project_mappings,
        'categories': categories,
        'brands': brands,
        'suppliers': suppliers,
        'user': request.user,
    }

    return render(request, 'project_add.html', context)
@login_required
def project_list(request):
    """
    查看所有项目信息
    """
    # 获取所有项目数据，包含关联信息
    projects_list = Project.objects.select_related(
        'project_mapping__region',  # 项目映射及其地区
        'supplier',                 # 供应商
        'category',                 # 物资类别
        'specification',            # 规格
        'brand',                    # 品牌
        'user'                      # 用户
    ).all()

    # 创建Paginator对象，每页显示20条数据
    paginator = Paginator(projects_list, 20)
    # 获取当前页码
    page_number = request.GET.get('page')
    # 获取当前页的项目数据
    projects = paginator.get_page(page_number)

    return render(request, 'project_list.html', {'projects': projects})


@login_required
def project_detail(request, project_id):
    """查看项目详情"""
    project = get_object_or_404(Project, id=project_id)

    # 检查权限：管理员可以查看所有项目，普通用户只能查看自己的项目
    if not request.user.is_admin and not request.user.is_staff and project.user != request.user:
        messages.error(request, '您没有权限查看此项目。')
        return redirect('projects:project_list')

    context = {
        'project': project,
        'title': '项目详情'
    }
    return render(request, 'project_detail.html', context)


@login_required
def project_edit(request, project_id):
    """编辑项目"""
    project = get_object_or_404(Project, id=project_id)

    # 检查权限：管理员可以编辑所有项目，普通用户只能编辑自己的项目
    if not request.user.is_admin and not request.user.is_staff and project.user != request.user:
        messages.error(request, '您没有权限编辑此项目。')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)
            # 保持原有的用户信息
            project.user = project.user  # 保持原有用户
            project.save()
            messages.success(request, '项目信息更新成功！')
            return redirect('projects:project_detail', project_id=project.id)
        else:
            messages.error(request, '表单数据有误，请检查后重新提交。')
    else:
        form = ProjectForm(instance=project)

    # 获取所有项目映射数据，包含地区信息
    project_mappings = ProjectMapping.objects.select_related('region').all()
    categories = MaterialCategory.objects.all()
    brands = Brand.objects.all()
    suppliers = Supplier.objects.all()  # 获取所有供应商

    context = {
        'form': form,
        'project': project,
        'project_mappings': project_mappings,
        'categories': categories,
        'brands': brands,
        'suppliers': suppliers,
        'user': request.user,
        'title': '编辑项目'
    }
    return render(request, 'project_edit.html', context)


@login_required
def project_delete(request, project_id):
    """删除项目"""
    project = get_object_or_404(Project, id=project_id)

    # 检查权限：管理员可以删除所有项目，普通用户只能删除自己的项目
    if not request.user.is_admin and not request.user.is_staff and project.user != request.user:
        messages.error(request, '您没有权限删除此项目。')
        return redirect('projects:project_list')

    if request.method == 'POST':
        project_name = project.project_mapping.project_name if project.project_mapping else '未知项目'
        project.delete()
        messages.success(request, f'项目 "{project_name}" 删除成功！')
        return redirect('projects:project_list')

    context = {
        'project': project,
        'title': '删除项目'
    }
    return render(request, 'project_delete.html', context)


@login_required
def project_mapping_add(request):
    """
    添加项目映射信息
    """
    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        region_id = request.POST.get('region')

        if project_name and region_id:
            try:
                region = Region.objects.get(id=region_id)
                ProjectMapping.objects.create(
                    project_name=project_name,
                    region=region
                )
                messages.success(request, '项目映射添加成功！')
                return redirect('projects:project_mapping_list')
            except Region.DoesNotExist:
                messages.error(request, '选择的地区不存在！')
        else:
            messages.error(request, '请填写所有必填字段！')

    # 获取所有地区信息用于选择
    regions = Region.objects.all()

    context = {
        'regions': regions,
        'title': '添加项目映射'
    }
    return render(request, 'project_mapping_add.html', context)


@login_required
def project_mapping_list(request):
    """
    显示所有项目映射信息
    """
    mappings_list = ProjectMapping.objects.select_related('region').all()
    paginator = Paginator(mappings_list, 20)
    page_number = request.GET.get('page')
    mappings = paginator.get_page(page_number)

    context = {
        'mappings': mappings,
        'title': '项目映射列表'
    }
    return render(request, 'project_mapping_list.html', context)

@admin_required
@login_required
def dashboard(request):
    """可视化仪表板 - 仅管理员可见"""
    # 获取所有数据（仅管理员可见）
    projects = Project.objects.all()
    concrete_prices = ConcretePrice.objects.all()
    users = User.objects.all()
    project_mappings = ProjectMapping.objects.all()
    suppliers = Supplier.objects.all()  # 从common应用导入的Supplier

    context = {
        'projects_count': projects.count(),
        'users_count': users.count(),
        'regions_count': Region.objects.count(),
        'project_mappings_count': project_mappings.count(),
        'suppliers_count': suppliers.count(),
        'categories_count': MaterialCategory.objects.count(),
        'brands_count': Brand.objects.count(),
        'recent_projects': projects.select_related(
            'project_mapping__region',
            'supplier',
            'category',
            'specification',
            'brand',
            'user'
        ).order_by('-arrival_date')[:5],  # 最近5个项目
        'title': '数据可视化仪表板'
    }
    return render(request, 'dashboard.html', context)



@login_required
def project_mapping_detail(request, mapping_id):
    """查看项目映射详情"""
    mapping = get_object_or_404(ProjectMapping, id=mapping_id)

    # 检查权限：只有管理员可以查看项目映射详情
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限查看项目映射详情。')
        return redirect('projects:project_mapping_list')

    context = {
        'mapping': mapping,
        'title': '项目映射详情'
    }
    return render(request, 'project_mapping_detail.html', context)


@login_required
def project_mapping_edit(request, mapping_id):
    """编辑项目映射"""
    mapping = get_object_or_404(ProjectMapping, id=mapping_id)

    # 检查权限：只有管理员可以编辑项目映射
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限编辑项目映射。')
        return redirect('projects:project_mapping_list')

    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        region_id = request.POST.get('region')

        if project_name and region_id:
            try:
                region = Region.objects.get(id=region_id)
                mapping.project_name = project_name
                mapping.region = region
                mapping.save()
                messages.success(request, '项目映射更新成功！')
                return redirect('projects:project_mapping_detail', mapping_id=mapping.id)
            except Region.DoesNotExist:
                messages.error(request, '选择的地区不存在！')
        else:
            messages.error(request, '请填写所有必填字段！')
    else:
        regions = Region.objects.all()

        context = {
            'mapping': mapping,
            'regions': regions,
            'title': '编辑项目映射'
        }
        return render(request, 'project_mapping_edit.html', context)


@login_required
def project_mapping_delete(request, mapping_id):
    """删除项目映射"""
    mapping = get_object_or_404(ProjectMapping, id=mapping_id)

    # 检查权限：只有管理员可以删除项目映射
    if not request.user.is_admin and not request.user.is_staff:
        messages.error(request, '您没有权限删除项目映射。')
        return redirect('projects:project_mapping_list')

    if request.method == 'POST':
        # 检查是否有项目关联到这个映射
        if mapping.project_set.exists():
            messages.error(request, '无法删除该项目映射，因为还有项目关联到它。请先删除相关项目。')
            return redirect('projects:project_mapping_detail', mapping_id=mapping.id)

        mapping_name = mapping.project_name
        mapping.delete()
        messages.success(request, f'项目映射 "{mapping_name}" 删除成功！')
        return redirect('projects:project_mapping_list')

    context = {
        'mapping': mapping,
        'title': '删除项目映射'
    }
    return render(request, 'project_mapping_delete.html', context)

@login_required
def chart_data(request):
    """获取图表数据"""
    # 根据查询参数获取数据
    chart_type = request.GET.get('type', 'monthly')

    if request.user.is_admin():
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(user=request.user)

    # 根据图表类型返回不同数据
    if chart_type == 'monthly':
        # 单月数据：项目单价柱状图 + 信息价折线图
        data = get_monthly_chart_data(projects)
    else:
        # 多月数据：各项目单价和信息价线
        data = get_multi_month_chart_data(projects)

    return JsonResponse(data)


def get_monthly_chart_data(projects):
    """获取单月图表数据"""
    # 实现单月图表数据逻辑
    data = {
        'labels': [],  # 项目名称
        'datasets': [
            {
                'label': '项目单价',
                'data': [],
                'type': 'bar'
            },
            {
                'label': '信息价',
                'data': [],
                'type': 'line'
            }
        ]
    }
    return data


def get_multi_month_chart_data(projects):
    """获取多月图表数据"""
    # 实现多月图表数据逻辑
    data = {
        'labels': [],  # 月份
        'datasets': []
    }
    return data


@require_http_methods(["GET"])
def get_districts(request):
    """
    根据市获取区县列表
    """
    city = request.GET.get('city')
    print(f"查询区县，城市: {city}")  # 调试信息

    if city:
        # 精确匹配城市名称，获取该市的所有区县
        districts = Region.objects.filter(
            city=city
        ).exclude(
            district__isnull=True
        ).exclude(
            district=''
        ).order_by('district')

        print(f"找到 {districts.count()} 个区县")  # 调试信息

        district_list = []
        for d in districts:
            district_list.append({
                'id': d.id,
                'name': d.district
            })

        print(f"区县列表: {district_list}")  # 调试信息
        return JsonResponse({'districts': district_list})

    return JsonResponse({'districts': []})


@require_http_methods(["GET"])
def get_project_mapping_info(request):
    """
    获取项目映射的详细信息（包括地区信息）
    """
    mapping_id = request.GET.get('id')
    if mapping_id:
        try:
            mapping = ProjectMapping.objects.select_related('region').get(id=mapping_id)
            return JsonResponse({
                'project_name': mapping.project_name,
                'region': str(mapping.region) if mapping.region else '',
                'region_id': mapping.region.id if mapping.region else None
            })
        except ProjectMapping.DoesNotExist:
            pass
    return JsonResponse({})


@require_http_methods(["GET"])
def get_specifications(request):
    """
    根据物资类别获取规格列表
    """
    category_id = request.GET.get('category_id')
    if category_id:
        specifications = Specification.objects.filter

@require_http_methods(["GET"])
def get_specifications(request):
    """
    根据物资类别获取规格列表
    """
    category_id = request.GET.get('category_id')
    if category_id:
        specifications = Specification.objects.filter(category_id=category_id).values('id', 'specification_name')
        spec_list = [{'id': s['id'], 'name': s['specification_name']} for s in specifications]
        return JsonResponse({'specifications': spec_list})
    return JsonResponse({'specifications': []})
