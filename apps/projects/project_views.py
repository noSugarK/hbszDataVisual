import os
import tempfile
import pandas as pd

from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Project, ProjectMapping, Specification, MaterialCategory, Brand, DataUpload
from ..region.models import Region
from ..supplier.models import Supplier
from ..users.models import User
from .forms import ProjectForm, ExcelUploadForm

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
    查看所有项目信息，添加筛选、搜索和排序功能
    """
    # 获取基础查询集 - 根据用户权限决定展示范围
    projects_queryset = Project.objects.select_related(
        'project_mapping__region',  # 项目映射及其地区
        'supplier',  # 供应商
        'category',  # 物资类别
        'specification',  # 规格
        'brand',  # 品牌
        'user'  # 用户
    )

    # 权限控制：管理员可以看到所有项目，普通用户只能看到自己填报的项目
    if not (request.user.is_superuser or request.user.permission == 'admin'):
        projects_list = projects_queryset.filter(user=request.user)
    else:
        projects_list = projects_queryset

    # 获取搜索和筛选参数
    search_query = request.GET.get('search', '')
    project_name_filter = request.GET.get('project_name', '')
    supplier_filter = request.GET.get('supplier', '')
    category_filter = request.GET.get('category', '')
    specification_filter = request.GET.get('specification', '')
    brand_filter = request.GET.get('brand', '')
    city_filter = request.GET.get('city', '')  # 城市筛选
    district_filter = request.GET.get('district', '')  # 区县筛选
    user_filter = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    # 异常值筛选参数
    anomaly_filter = request.GET.get('anomaly_filter', '')
    # 排序参数
    sort_by = request.GET.get('sort', 'arrival_date')  # 默认按到货日期排序
    order = request.GET.get('order', 'desc')  # 默认降序

    # 应用搜索条件（全局搜索）
    if search_query:
        projects_list = projects_list.filter(
            Q(project_mapping__project_name__icontains=search_query) |
            Q(supplier__supplier_name__icontains=search_query) |
            Q(category__category_name__icontains=search_query) |
            Q(specification__specification_name__icontains=search_query) |
            Q(brand__brand_name__icontains=search_query) |
            Q(project_mapping__region__city__icontains=search_query) |
            Q(project_mapping__region__district__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # 应用筛选条件
    if project_name_filter:
        projects_list = projects_list.filter(
            project_mapping__project_name=project_name_filter
        )

    if supplier_filter:
        projects_list = projects_list.filter(
            supplier__supplier_name=supplier_filter
        )

    if category_filter:
        projects_list = projects_list.filter(
            category__category_name=category_filter
        )

    if specification_filter:
        projects_list = projects_list.filter(
            specification__id=specification_filter
        )

    if brand_filter:
        projects_list = projects_list.filter(
            brand__brand_name=brand_filter
        )

    # 地区筛选逻辑改进
    if city_filter:
        # 如果选择了城市，则筛选该城市的所有项目（包括所有区县）
        projects_list = projects_list.filter(
            project_mapping__region__city=city_filter
        )

        # 如果还选择了具体的区县，则进一步筛选
        if district_filter:
            projects_list = projects_list.filter(
                project_mapping__region__district=district_filter
            )

    if user_filter:
        # 管理员可以按用户筛选，普通用户只能看到自己的数据，不需要按用户筛选
        if request.user.is_superuser or request.user.permission == 'admin':
            projects_list = projects_list.filter(
                user__username=user_filter
            )

    if start_date:
        projects_list = projects_list.filter(
            arrival_date__gte=start_date
        )

    if end_date:
        projects_list = projects_list.filter(
            arrival_date__lte=end_date
        )

    # 新增异常值筛选逻辑
    if anomaly_filter == 'anomaly':
        projects_list = projects_list.filter(is_anomaly=True)
    elif anomaly_filter == 'normal':
        projects_list = projects_list.filter(is_anomaly=False)

    # 应用排序
    # 定义允许排序的字段，防止SQL注入
    allowed_sort_fields = {
        'project_mapping__project_name': 'project_mapping__project_name',
        'arrival_date': 'arrival_date',
        'supplier__supplier_name': 'supplier__supplier_name',
        'category__category_name': 'category__category_name',
        'specification__specification_name': 'specification__specification_name',
        'quantity': 'quantity',
        'unit_price': 'unit_price',
        'discount_rate': 'discount_rate',
        'total_amount': 'total_amount',
        'brand__brand_name': 'brand__brand_name',
        'project_mapping__region': 'project_mapping__region',
        'user__username': 'user__username'
    }

    # 验证排序字段是否允许
    if sort_by in allowed_sort_fields:
        sort_field = allowed_sort_fields[sort_by]
        # 如果是降序，在字段前加负号
        if order == 'desc':
            sort_field = '-' + sort_field
        projects_list = projects_list.order_by(sort_field)
    else:
        # 默认排序
        projects_list = projects_list.order_by('-arrival_date')

    # 获取筛选选项数据 - 根据用户权限决定
    if request.user.is_superuser or request.user.permission == 'admin':
        # 管理员可以看到所有选项
        project_names = ProjectMapping.objects.values_list('project_name', flat=True).distinct()
        suppliers = Supplier.objects.values_list('supplier_name', flat=True).distinct()
        categories = MaterialCategory.objects.values_list('category_name', flat=True).distinct()
        brands = Brand.objects.values_list('brand_name', flat=True).distinct()
        cities = Region.objects.values_list('city', flat=True).distinct()
        users = User.objects.values_list('username', flat=True).distinct()
    else:
        # 普通用户只能看到与自己相关的选项
        user_projects = projects_queryset.filter(user=request.user)
        project_names = user_projects.values_list('project_mapping__project_name', flat=True).distinct()
        suppliers = user_projects.values_list('supplier__supplier_name', flat=True).distinct()
        categories = user_projects.values_list('category__category_name', flat=True).distinct()
        brands = user_projects.values_list('brand__brand_name', flat=True).distinct()
        cities = Region.objects.filter(
            projectmapping__project__user=request.user
        ).values_list('city', flat=True).distinct()
        users = [request.user.username]  # 普通用户只能看到自己

    # 根据当前选择的城市获取区县选项
    if city_filter:
        districts = Region.objects.filter(city=city_filter).values_list('district', flat=True).distinct()
        # 过滤掉空值
        districts = [d for d in districts if d]
    else:
        districts = []

    specifications = Specification.objects.select_related('category')

    # 创建Paginator对象，每页显示20条数据
    paginator = Paginator(projects_list, 20)
    # 获取当前页码
    page_number = request.GET.get('page')
    # 获取当前页的项目数据
    projects = paginator.get_page(page_number)

    return render(request, 'project_list.html', {
        'projects': projects,
        'project_names': project_names,
        'suppliers': suppliers,
        'categories': categories,
        'brands': brands,
        'cities': cities,
        'districts': districts,
        'users': users,
        'specifications': specifications,
        'search_query': search_query,
        'project_name_filter': project_name_filter,
        'supplier_filter': supplier_filter,
        'category_filter': category_filter,
        'specification_filter': specification_filter,
        'brand_filter': brand_filter,
        'city_filter': city_filter,
        'district_filter': district_filter,
        'user_filter': user_filter,
        'start_date': start_date,
        'end_date': end_date,
        'anomaly_filter': anomaly_filter,
        'sort_by': sort_by,
        'order': order,
    })


@login_required
def project_detail(request, project_id):
    """查看项目详情"""
    project = get_object_or_404(Project, id=project_id)

    # 检查权限：管理员可以查看所有项目，普通用户只能查看自己的项目
    if not request.user.is_superuser and not request.user.permission == 'admin' and project.user != request.user:
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
    if not request.user.is_superuser and not request.user.permission == 'admin' and project.user != request.user:
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
    if not request.user.is_superuser and not request.user.permission == 'admin' and project.user != request.user:
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
def detect_anomalies(request):
    """
    检测项目数据中的异常值
    """
    if not (request.user.is_superuser or request.user.permission == 'admin'):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('projects:project_list')

    # 获取所有城市（按city字段分组）
    cities = Region.objects.values_list('city', flat=True).distinct().order_by('city')

    context = {
        'cities': cities,
        'title': '异常值检测'
    }

    return render(request, 'detect_anomalies.html', context)


def is_anomaly(project, stats):
    """
    判断单个项目是否为异常值的函数
    使用更严格的3.0标准差阈值

    Args:
        project: Project对象
        stats: 该分组的统计信息，包含mean和std

    Returns:
        bool: True表示是异常值，False表示不是异常值
    """
    # 确保统计数据有效
    if 'mean' not in stats or 'std' not in stats:
        return False

    mean = stats['mean']
    std = stats['std']

    # 如果标准差为0或无效，无法判断异常值
    if std is None or float(std) == 0:
        return False

    # 将所有值转换为float类型进行计算
    project_price = float(project.unit_price)
    mean_val = float(mean)
    std_val = float(std)

    # 使用Z-Score方法，如果超过3个标准差则为异常值（更严格的标准）
    z_score = abs(project_price - mean_val) / std_val
    return z_score > 3.0


@login_required
def process_anomalies(request, city_name):
    """
    处理特定城市的异常值检测（按物资类别、规格和月份分组）
    """
    if not (request.user.is_superuser or request.user.permission == 'admin'):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('projects:project_list')

    # 获取该城市的所有地区
    regions = Region.objects.filter(city=city_name)

    # 获取该城市的所有项目
    projects = Project.objects.filter(project_mapping__region__in=regions)

    # 按物资类别、规格和月份分组，计算每个分组的统计信息
    from django.db.models import Avg, StdDev
    category_stats = projects.values(
        'category__category_name',
        'specification__specification_name',
        'arrival_date__year',
        'arrival_date__month'
    ).annotate(
        mean=Avg('unit_price'),
        std=StdDev('unit_price'),
        count=models.Count('id')
    ).filter(count__gt=1)  # 只考虑有2个以上数据点的分组

    # 创建统计信息字典
    stats_dict = {}
    for stat in category_stats:
        category_name = stat['category__category_name']
        specification_name = stat['specification__specification_name']
        year = stat['arrival_date__year']
        month = stat['arrival_date__month']

        # 使用复合键作为字典的键
        key = (category_name, specification_name, year, month)

        # 确保统计数据有效
        mean_val = stat['mean'] if stat['mean'] is not None else 0
        std_val = stat['std'] if stat['std'] is not None else 0

        stats_dict[key] = {
            'mean': mean_val,
            'std': std_val
        }

    # 重置所有项目的异常标记
    projects.update(is_anomaly=False)

    # 检测异常值
    anomaly_count = 0
    for project in projects:
        category_name = project.category.category_name
        specification_name = project.specification.specification_name
        year = project.arrival_date.year
        month = project.arrival_date.month

        # 使用相同的复合键查找统计信息
        key = (category_name, specification_name, year, month)
        if key in stats_dict:
            stats = stats_dict[key]
            if is_anomaly(project, stats):
                project.is_anomaly = True
                project.save()
                anomaly_count += 1

    messages.success(request, f'在 {city_name} 城市检测到 {anomaly_count} 个异常值。')
    return redirect('projects:detect_anomalies')


@login_required
def process_selected_cities(request):
    """
    处理选中城市的异常值检测（按物资类别、规格和月份分组）
    """
    if not (request.user.is_superuser or request.user.permission == 'admin'):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('projects:project_list')

    if request.method == 'POST':
        # 获取选中的城市
        selected_cities = request.POST.getlist('selected_cities')

        if not selected_cities:
            messages.warning(request, '请至少选择一个城市进行处理。')
            return redirect('projects:detect_anomalies')

        # 统计信息
        total_anomaly_count = 0
        processed_cities = 0

        # 处理每个选中的城市
        for city_name in selected_cities:
            try:
                # 获取该城市的所有地区
                regions = Region.objects.filter(city=city_name)

                # 获取该城市的所有项目
                projects = Project.objects.filter(project_mapping__region__in=regions)

                # 按物资类别、规格和月份分组，计算每个分组的统计信息
                from django.db.models import Avg, StdDev
                import django.db.models as models
                category_stats = projects.values(
                    'category__category_name',
                    'specification__specification_name',
                    'arrival_date__year',
                    'arrival_date__month'
                ).annotate(
                    mean=Avg('unit_price'),
                    std=StdDev('unit_price'),
                    count=models.Count('id')
                ).filter(count__gt=1)  # 只考虑有2个以上数据点的分组

                # 创建统计信息字典
                stats_dict = {}
                for stat in category_stats:
                    category_name = stat['category__category_name']
                    specification_name = stat['specification__specification_name']
                    year = stat['arrival_date__year']
                    month = stat['arrival_date__month']

                    # 使用复合键作为字典的键
                    key = (category_name, specification_name, year, month)

                    # 确保统计数据有效
                    mean_val = stat['mean'] if stat['mean'] is not None else 0
                    std_val = stat['std'] if stat['std'] is not None else 0

                    stats_dict[key] = {
                        'mean': mean_val,
                        'std': std_val
                    }

                # 重置该城市所有项目的异常标记
                projects.update(is_anomaly=False)

                # 检测该城市的异常值
                anomaly_count = 0
                for project in projects:
                    category_name = project.category.category_name
                    specification_name = project.specification.specification_name
                    year = project.arrival_date.year
                    month = project.arrival_date.month

                    # 使用相同的复合键查找统计信息
                    key = (category_name, specification_name, year, month)
                    if key in stats_dict:
                        stats = stats_dict[key]
                        if is_anomaly(project, stats):
                            project.is_anomaly = True
                            project.save()
                            anomaly_count += 1

                total_anomaly_count += anomaly_count
                processed_cities += 1

            except Exception as e:
                messages.warning(request, f'处理城市 {city_name} 时发生错误: {str(e)}')
                continue

        messages.success(request,
                         f'已完成选中城市的异常值检测，共处理 {processed_cities} 个城市，检测到 {total_anomaly_count} 个异常值。')

    return redirect('projects:detect_anomalies')
