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
from .forms import ProjectForm, ExcelUploadForm, ProjectMappingExcelUploadForm


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


@login_required
def project_excel(request):
    """
    上传Excel文件并导入项目数据
    """
    # 预览模式 - 显示工作表选项
    if request.method == 'POST' and 'preview' in request.POST:
        excel_file = request.FILES.get('excel_file')
        if excel_file:
            try:
                # 创建临时文件来存储上传的Excel文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    for chunk in excel_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                try:
                    # 获取工作表列表
                    if excel_file.name.endswith('.xlsx'):
                        engine = 'openpyxl'
                    elif excel_file.name.endswith('.xls'):
                        engine = 'xlrd'
                    else:
                        engine = None

                    # 读取Excel文件中的所有工作表名称
                    excel_file_obj = pd.ExcelFile(tmp_path, engine=engine)
                    sheet_names = excel_file_obj.sheet_names

                    # 创建表单并传递工作表选项，默认选择第一个工作表
                    sheet_choices = [('', '使用第一个工作表（默认）')] + [(name, name) for name in sheet_names]
                    form = ExcelUploadForm(sheet_choices=sheet_choices)
                    form.fields['excel_file'].initial = excel_file

                    # 保存临时文件路径到会话中
                    request.session['excel_tmp_path'] = tmp_path
                    request.session['excel_filename'] = excel_file.name

                    return render(request, 'project_excel.html', {
                        'form': form,
                        'sheet_names': sheet_names,
                        'preview_mode': True
                    })

                finally:
                    # 保持临时文件以供后续使用
                    pass

            except Exception as e:
                messages.error(request, f'读取Excel文件时发生错误: {str(e)}')
                # 清理临时文件
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
                form = ExcelUploadForm()
        else:
            form = ExcelUploadForm()

    # 导入模式 - 实际导入数据
    elif request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        sheet_name = request.POST.get('sheet_name', '')

        # 检查是否从会话中获取临时文件
        tmp_path = request.session.get('excel_tmp_path')
        excel_filename = request.session.get('excel_filename')

        if tmp_path and os.path.exists(tmp_path):
            try:
                # 保存上传记录
                data_upload = DataUpload.objects.create(
                    user=request.user,
                    file_path=excel_filename or 'unknown.xlsx',
                    status='processing'
                )

                try:
                    # 使用 pandas 读取临时文件，支持指定工作表
                    excel_file_name = excel_filename or 'unknown.xlsx'
                    if excel_file_name.endswith('.xlsx'):
                        engine = 'openpyxl'
                    elif excel_file_name.endswith('.xls'):
                        engine = 'xlrd'
                    else:
                        engine = None  # 让pandas自动选择

                    # 如果指定了工作表名称，则使用指定的工作表
                    if sheet_name:
                        df = pd.read_excel(tmp_path, sheet_name=sheet_name, engine=engine)
                    else:
                        # 否则使用第一个工作表
                        df = pd.read_excel(tmp_path, engine=engine)

                    # 验证必要的列是否存在
                    required_columns = ['项目名称', '到货日期', '供应商', '物资类别', '规格', '数量', '单价（不含税）']
                    missing_columns = [col for col in required_columns if col not in df.columns]

                    if missing_columns:
                        messages.error(request, f'Excel文件缺少必要的列: {", ".join(missing_columns)}')
                        data_upload.status = 'failed'
                        data_upload.save()
                        # 清理会话数据
                        if 'excel_tmp_path' in request.session:
                            del request.session['excel_tmp_path']
                        if 'excel_filename' in request.session:
                            del request.session['excel_filename']
                        return redirect('projects:project_excel')

                    # 获取ID为1的默认地区
                    try:
                        default_region = Region.objects.get(id=1)
                    except Region.DoesNotExist:
                        messages.error(request, '系统中不存在ID为1的地区，请先创建默认地区')
                        data_upload.status = 'failed'
                        data_upload.save()
                        # 清理会话数据
                        if 'excel_tmp_path' in request.session:
                            del request.session['excel_tmp_path']
                        if 'excel_filename' in request.session:
                            del request.session['excel_filename']
                        return redirect('projects:project_excel')

                    # 获取ID为1的默认品牌
                    try:
                        default_brand = Brand.objects.get(id=1)
                    except Brand.DoesNotExist:
                        messages.error(request, '系统中不存在ID为1的品牌，请先创建默认品牌')
                        data_upload.status = 'failed'
                        data_upload.save()
                        # 清理会话数据
                        if 'excel_tmp_path' in request.session:
                            del request.session['excel_tmp_path']
                        if 'excel_filename' in request.session:
                            del request.session['excel_filename']
                        return redirect('projects:project_excel')

                    # 处理数据并保存到数据库
                    success_count = 0
                    error_messages = []

                    with transaction.atomic():
                        for index, row in df.iterrows():
                            try:
                                # 验证必要字段不为空
                                if pd.isna(row['项目名称']) or pd.isna(row['到货日期']) or \
                                        pd.isna(row['供应商']) or pd.isna(row['物资类别']) or \
                                        pd.isna(row['规格']) or pd.isna(row['数量']) or \
                                        pd.isna(row['单价（不含税）']):
                                    raise ValueError("必要字段不能为空")

                                # 处理项目映射
                                project_name = str(row['项目名称']).strip()

                                # 获取或创建项目映射，使用ID为1的地区作为默认地区
                                project_mapping, created = ProjectMapping.objects.get_or_create(
                                    project_name=project_name,
                                    defaults={'region': default_region}
                                )

                                # 获取供应商
                                supplier, created = Supplier.objects.get_or_create(
                                    supplier_name=str(row['供应商']).strip()
                                )

                                # 获取物资类别
                                category, created = MaterialCategory.objects.get_or_create(
                                    category_name=str(row['物资类别']).strip()
                                )

                                # 获取规格
                                specification, created = Specification.objects.get_or_create(
                                    specification_name=str(row['规格']).strip(),
                                    category=category
                                )

                                # 处理品牌 - 使用ID为1的品牌作为默认品牌
                                brand = default_brand
                                if '品牌' in row and pd.notna(row['品牌']) and str(row['品牌']).strip() not in ['/','']:
                                    brand_name = str(row['品牌']).strip()
                                    # 尝试查找现有品牌，如果不存在则创建新品牌
                                    brand, created = Brand.objects.get_or_create(
                                        brand_name=brand_name
                                    )

                                # 处理日期格式
                                arrival_date = pd.to_datetime(row['到货日期'])

                                # 处理数值字段
                                try:
                                    quantity = float(row['数量'])
                                    unit_price = float(row['单价（不含税）'])
                                    discount_rate = float(row.get('下浮率%', 0)) if pd.notna(
                                        row.get('下浮率%', 0)) else 0
                                except ValueError:
                                    raise ValueError("数量、单价或下浮率格式不正确")

                                # 创建项目
                                Project.objects.create(
                                    project_mapping=project_mapping,
                                    arrival_date=arrival_date,
                                    supplier=supplier,
                                    category=category,
                                    specification=specification,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    discount_rate=discount_rate,
                                    brand=brand,
                                    user=request.user
                                )
                                success_count += 1

                            except Exception as e:
                                error_messages.append(f"第{index + 2}行数据导入失败: {str(e)}")  # +2因为索引从0开始，且第一行是标题行

                    if error_messages:
                        for error in error_messages:
                            messages.warning(request, error)

                    messages.success(request, f'成功导入 {success_count} 条数据')
                    data_upload.status = 'completed'
                    data_upload.save()

                finally:
                    # 删除临时文件
                    os.unlink(tmp_path)
                    # 清理会话数据
                    if 'excel_tmp_path' in request.session:
                        del request.session['excel_tmp_path']
                    if 'excel_filename' in request.session:
                        del request.session['excel_filename']

            except Exception as e:
                messages.error(request, f'导入过程中发生错误: {str(e)}')
                data_upload.status = 'failed'
                data_upload.save()
                # 清理会话数据
                if 'excel_tmp_path' in request.session:
                    del request.session['excel_tmp_path']
                if 'excel_filename' in request.session:
                    del request.session['excel_filename']
                # 删除临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            return redirect('projects:project_list')
        else:
            messages.error(request, '文件信息丢失，请重新上传文件')
            form = ExcelUploadForm()
    else:
        form = ExcelUploadForm()

    return render(request, 'project_excel.html', {'form': form, 'preview_mode': False})



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
