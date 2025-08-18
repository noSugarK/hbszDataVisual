# apps/visual/views.py
import calendar

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Max, Q, Avg
from apps.projects.models import Project, ProjectMapping
from apps.region.models import Region
from apps.price.models import ConcretePrice
from datetime import date


@login_required
def chart_hnt(request):
    """
    可视化图表首页
    """
    # 获取所有地区（去重的市级数据）
    regions = Region.objects.filter(district='').order_by('city')

    # 获取项目数据的时间范围
    date_range = Project.objects.aggregate(
        min_date=Min('arrival_date'),
        max_date=Max('arrival_date')
    )

    context = {
        'regions': regions,
        'date_range': date_range,
        'title': '项目价格与信息价可视化'
    }

    return render(request, 'hnt-visual.html', context)


@login_required
def chart_hntdata(request):
    # 获取前端参数
    region_fields = request.GET.getlist('regions[]')  # 地区拼音列表
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # 日期处理函数（保持不变）
    def parse_month_to_date(month_str, day='first'):
        if not month_str:
            return None
        try:
            year, month = map(int, month_str.split('-'))
            if day == 'first':
                return date(year, month, 1)
            else:
                last_day = calendar.monthrange(year, month)[1]
                return date(year, month, last_day)
        except:
            return None

    start_date = parse_month_to_date(start_date_str, 'first')
    end_date = parse_month_to_date(end_date_str, 'last')

    # 查询信息价数据
    price_query = ConcretePrice.objects.all()
    if start_date:
        price_query = price_query.filter(date__gte=start_date)
    if end_date:
        price_query = price_query.filter(date__lte=end_date)
    prices = price_query.order_by('date')

    # 查询项目数据（按项目分组，而非地区）
    project_data = []
    # 获取选中地区的所有项目映射
    region_instances = Region.objects.filter(citypy__in=region_fields)
    project_mappings = ProjectMapping.objects.filter(region__in=region_instances)

    # 获取这些映射下的所有项目
    project_query = Project.objects.filter(project_mapping__in=project_mappings)
    if start_date:
        project_query = project_query.filter(arrival_date__gte=start_date)
    if end_date:
        project_query = project_query.filter(arrival_date__lte=end_date)

    # 按项目和月份分组计算平均价格
    project_query = project_query.extra(
        select={'month': "DATE_FORMAT(arrival_date, '%%Y-%%m')"}
    ).values('project_mapping__project_name', 'month').annotate(
        avg_price=Avg('unit_price')
    ).order_by('project_mapping__project_name', 'month')

    # 组织项目数据
    for item in project_query:
        if item['avg_price'] is not None:
            project_data.append({
                'name': item['project_mapping__project_name'],  # 项目名称
                'date': item['month'],
                'price': float(item['avg_price']),
                # 获取项目所属地区
                'region': ProjectMapping.objects.get(
                    project_name=item['project_mapping__project_name']
                ).region.city
            })

    # 组织信息价数据
    reference_price_data = []
    for price in prices:
        month_key = price.date.strftime('%Y-%m')
        entry = {'date': month_key}
        for region in region_fields:
            if hasattr(price, region):
                region_obj = Region.objects.filter(citypy=region).first()
                if region_obj:
                    entry[region_obj.city] = float(getattr(price, region) or 0)
        reference_price_data.append(entry)

    return JsonResponse({
        'project_data': project_data,
        'reference_price_data': reference_price_data,
        'regions': [r.city for r in region_instances]
    }, safe=False, json_dumps_params={'ensure_ascii': False})