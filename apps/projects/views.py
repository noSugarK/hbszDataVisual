# apps/projects/views.py
import os
import tempfile
from functools import wraps
import pandas as pd

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import Project, ProjectMapping, Specification, MaterialCategory, Brand, DataUpload
from ..price.models import ConcretePrice
from ..region.models import Region
from ..supplier.models import Supplier
from ..users.models import User
from .forms import ProjectMappingExcelUploadForm


def admin_required(view_func):
    """
    自定义装饰器，只允许管理员访问
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not (request.user.is_superuser or request.user.permission == 'admin'):
            messages.error(request, '您没有权限访问此页面。')
            return redirect('common:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def project_mapping_excel(request):
    """
    上传Excel文件并导入项目映射数据（支持地区（市）和地区（区/县））
    """
    # 预览模式 - 显示工作表选项
    if request.method == 'POST' and 'preview' in request.POST:
        excel_file = request.FILES.get('excel_file')
        if excel_file:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    for chunk in excel_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                try:
                    if excel_file.name.endswith('.xlsx'):
                        engine = 'openpyxl'
                    elif excel_file.name.endswith('.xls'):
                        engine = 'xlrd'
                    else:
                        engine = None

                    excel_file_obj = pd.ExcelFile(tmp_path, engine=engine)
                    sheet_names = excel_file_obj.sheet_names

                    sheet_choices = [('', '使用第一个工作表（默认）')] + [(name, name) for name in sheet_names]
                    form = ProjectMappingExcelUploadForm(sheet_choices=sheet_choices)
                    form.fields['excel_file'].initial = excel_file

                    request.session['mapping_excel_tmp_path'] = tmp_path
                    request.session['mapping_excel_filename'] = excel_file.name

                    return render(request, 'project_mapping_excel.html', {
                        'form': form,
                        'sheet_names': sheet_names,
                        'preview_mode': True
                    })

                finally:
                    pass

            except Exception as e:
                messages.error(request, f'读取Excel文件时发生错误: {str(e)}')
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
                form = ProjectMappingExcelUploadForm()
        else:
            form = ProjectMappingExcelUploadForm()

    # 导入模式 - 实际导入数据
    elif request.method == 'POST':
        form = ProjectMappingExcelUploadForm(request.POST, request.FILES)
        sheet_name = request.POST.get('sheet_name', '')

        tmp_path = request.session.get('mapping_excel_tmp_path')
        excel_filename = request.session.get('mapping_excel_filename')

        if tmp_path and os.path.exists(tmp_path):
            try:
                data_upload = DataUpload.objects.create(
                    user=request.user,
                    file_path=excel_filename or 'unknown.xlsx',
                    status='processing'
                )

                try:
                    excel_file_name = excel_filename or 'unknown.xlsx'
                    if excel_file_name.endswith('.xlsx'):
                        engine = 'openpyxl'
                    elif excel_file_name.endswith('.xls'):
                        engine = 'xlrd'
                    else:
                        engine = None

                    df = pd.read_excel(tmp_path, sheet_name=sheet_name, engine=engine)

                    # 验证必要列
                    required_columns = ['项目名称', '地区（区/县）', '地区（市）']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        messages.error(request, f'Excel文件缺少必要的列: {", ".join(missing_columns)}')
                        data_upload.status = 'failed'
                        data_upload.save()
                        del request.session['mapping_excel_tmp_path']
                        del request.session['mapping_excel_filename']
                        return redirect('projects:project_mapping_excel')

                    success_count = 0
                    error_messages = []

                    with transaction.atomic():
                        for index, row in df.iterrows():
                            try:
                                # 验证必要字段不为空
                                if pd.isna(row['项目名称']):
                                    raise ValueError("项目名称不能为空")

                                project_name = str(row['项目名称']).strip()

                                # 处理地区信息
                                district = row['地区（区/县）']
                                city = row['地区（市）']

                                # 处理非正常地区数据
                                if pd.isna(district) or district in ['/', '', None]:
                                    district = ''
                                else:
                                    district = str(district).strip()

                                if pd.isna(city) or city in ['/', '', None]:
                                    raise ValueError("地区（市）不能为空")
                                else:
                                    city = str(city).strip()

                                # 查找地区，不允许新增地区
                                try:
                                    if district:
                                        # 优先查找区县
                                        region = Region.objects.get(city=city, district=district)
                                    else:
                                        # 查找市级地区
                                        region = Region.objects.get(city=city, district='')
                                except Region.DoesNotExist:
                                    if district:
                                        # 如果区县找不到，尝试查找市级地区
                                        try:
                                            region = Region.objects.get(city=city, district='')
                                            # 区县找不到，但市级存在，可以继续但需要提示
                                            messages.warning(request,
                                                             f'第{index + 2}行：区县"{district}"未找到，使用市级地区"{city}"')
                                        except Region.DoesNotExist:
                                            raise ValueError(f'地区"{city}"不存在')
                                    else:
                                        raise ValueError(f'地区"{city}"不存在')

                                # 创建或更新项目映射
                                project_mapping, created = ProjectMapping.objects.get_or_create(
                                    project_name=project_name,
                                    defaults={'region': region}
                                )
                                if not created and project_mapping.region != region:
                                    project_mapping.region = region
                                    project_mapping.save()

                                success_count += 1

                            except Exception as e:
                                error_messages.append(f"第{index + 2}行数据导入失败: {str(e)}")

                    if error_messages:
                        for error in error_messages:
                            messages.warning(request, error)

                    messages.success(request, f'成功导入 {success_count} 条项目映射数据')
                    data_upload.status = 'completed'
                    data_upload.save()

                finally:
                    os.unlink(tmp_path)
                    del request.session['mapping_excel_tmp_path']
                    del request.session['mapping_excel_filename']

            except Exception as e:
                messages.error(request, f'导入过程中发生错误: {str(e)}')
                if 'data_upload' in locals():
                    data_upload.status = 'failed'
                    data_upload.save()
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
                del request.session['mapping_excel_tmp_path']
                del request.session['mapping_excel_filename']

            return redirect('projects:project_mapping_list')
        else:
            messages.error(request, '文件信息丢失，请重新上传文件')
            form = ProjectMappingExcelUploadForm()

    else:
        form = ProjectMappingExcelUploadForm()

    return render(request, 'project_mapping_excel.html', {'form': form, 'preview_mode': False})



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
    mappings_list = ProjectMapping.objects.select_related('region').order_by('id')
    paginator = Paginator(mappings_list, 20)
    page_number = request.GET.get('page')
    mappings = paginator.get_page(page_number)

    context = {
        'mappings': mappings,
        'title': '项目映射列表'
    }
    return render(request, 'project_mapping_list.html', context)

@admin_required
def dashboard(request):
    """可视化仪表板 - 仅管理员可见"""
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
    if not request.user.is_superuser and not request.user.permission == 'admin':
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
    if not request.user.is_superuser and not request.user.permission == 'admin':
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
    if not request.user.is_superuser and not request.user.permission == 'admin':
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
        specifications = Specification.objects.filter(category_id=category_id).values('id', 'specification_name')
        spec_list = [{'id': s['id'], 'name': s['specification_name']} for s in specifications]
        return JsonResponse({'specifications': spec_list})
    return JsonResponse({'specifications': []})
