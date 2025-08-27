# apps/visual/views.py
import calendar

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Min, Max, Q, Avg
from apps.projects.models import Project, ProjectMapping
from apps.projects.views import admin_required
from apps.region.models import Region
from apps.price.models import ConcretePrice
from datetime import date
import logging


@admin_required
def chart_hnt(request):
    """
    可视化图表首页
    """
    # 获取所有地区（去重的市级数据）- 只获取城市记录（district为空的记录）
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

@admin_required
def chart_hnt_bar(request):
    """
    可视化图表首页 - 柱状图页面
    """
    # 获取所有地区（去重的市级数据）- 只获取城市记录（district为空的记录）
    regions = Region.objects.filter(district='').order_by('city')

    context = {
        'regions': regions,
        'title': '商品混凝土C30项目价格柱状图'
    }

    return render(request, 'hnt-visual-bar.html', context)


@login_required
def chart_hnt_bar_data(request):
    """
    获取柱状图数据：按地区分组的项目价格和信息价
    修复：按月份匹配信息价（忽略具体日期），确保单月项目能关联当月信息价
    """
    logger = logging.getLogger(__name__)

    month_str = request.GET.get('month')
    year_str = request.GET.get('year')

    # 日期范围处理
    start_date = None
    end_date = None
    if year_str:
        try:
            year = int(year_str)
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            logger.debug(f"全年查询：{year}年，日期范围：{start_date} 至 {end_date}")
        except Exception as e:
            logger.error(f"年份解析失败：{year_str}，错误：{str(e)}")
    elif month_str:
        try:
            year, month = map(int, month_str.split('-'))
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
            logger.debug(f"单月查询：{year}-{month}，日期范围：{start_date} 至 {end_date}")
        except Exception as e:
            logger.error(f"月份解析失败：{month_str}，错误：{str(e)}")
    else:
        today = date.today()
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        logger.debug(f"默认查询：当前月 {today.year}-{today.month}")

    # 查询项目数据
    project_query = Project.objects.filter(
        specification__category__category_name='商品混凝土',
        specification__specification_name='C30'
    ).annotate(
        project_start=Min('arrival_date'),
        project_end=Max('arrival_date')
    )

    if start_date and end_date:
        project_query = project_query.filter(
            arrival_date__gte=start_date,
            arrival_date__lte=end_date
        )
    logger.debug(f"符合条件的项目数量：{project_query.count()}")

    # 按项目分组计算平均价格
    project_query = project_query.extra(
        select={'month': "DATE_FORMAT(arrival_date, '%%Y-%%m')" if not year_str else "DATE_FORMAT(arrival_date, '%%Y')"}
    ).values(
        'project_mapping__project_name',
        'project_mapping__region__city',
        'project_mapping__region__citypy',
        'project_start',
        'project_end'
    ).annotate(
        avg_price=Avg('unit_price')
    ).order_by('project_mapping__region__citypy', 'project_mapping__project_name')

    # 获取信息价数据（按日期排序）
    price_records = []
    if start_date and end_date:
        price_records = ConcretePrice.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
    else:
        price_records = ConcretePrice.objects.all().order_by('date')
    logger.debug(
        f"查询到的信息价记录数量：{len(price_records)}，日期列表：{[r.date.strftime('%Y-%m-%d') for r in price_records]}")

    # 组织项目数据
    project_data = []
    regions = {r.citypy: r for r in Region.objects.filter(district='')}

    for item in project_query:
        if item['avg_price'] is None or not item['project_start'] or not item['project_end']:
            continue

        # 项目基础信息
        project_name = item['project_mapping__project_name']
        citypy = item['project_mapping__region__citypy']
        region = regions.get(citypy)
        project_start = item['project_start']
        project_end = item['project_end']
        project_info_price = None

        # 计算项目持续月数（用于判断是否单月项目）
        months_duration = (project_end.year - project_start.year) * 12 + (project_end.month - project_start.month) + 1
        logger.debug(f"\n项目：{project_name}，地区拼音：{citypy}，持续月数：{months_duration}")
        logger.debug(f"项目时间段：{project_start.strftime('%Y-%m-%d')} 至 {project_end.strftime('%Y-%m-%d')}")

        if region and citypy:
            info_prices = []
            for record in price_records:
                # 核心修复：按月份匹配（忽略具体日期）
                # 1. 提取项目和信息价的年月
                project_year = project_start.year
                project_month = project_start.month
                record_year = record.date.year
                record_month = record.date.month

                # 2. 判断是否为同一月份（关键逻辑）
                is_same_month = (project_year == record_year) and (project_month == record_month)

                # 3. 对于多月项目：需信息价月份在项目起止月份范围内
                if months_duration > 1:
                    # 计算信息价月份是否在项目月份范围内
                    project_end_year = project_end.year
                    project_end_month = project_end.month
                    is_in_range = (
                                          (record_year > project_year) or
                                          (record_year == project_year and record_month >= project_month)
                                  ) and (
                                          (record_year < project_end_year) or
                                          (record_year == project_end_year and record_month <= project_end_month)
                                  )
                    is_date_match = is_in_range
                else:
                    # 单月项目：只需匹配月份
                    is_date_match = is_same_month

                if not is_date_match:
                    logger.debug(f"  信息价 {record.date.strftime('%Y-%m')} 与项目月份不匹配，跳过")
                    continue

                # 检查地区字段是否存在且值有效
                if not hasattr(record, citypy):
                    logger.warning(f"  信息价记录无 {citypy} 字段，跳过")
                    continue

                price_value = getattr(record, citypy)
                if price_value is None:
                    logger.debug(f"  {citypy} 字段值为NULL，跳过")
                    continue
                if isinstance(price_value, (int, float)) and price_value < 0:
                    logger.debug(f"  {citypy} 字段值为负数（{price_value}），跳过")
                    continue

                # 转换为数值并加入列表
                try:
                    price_value = float(price_value)
                    info_prices.append(price_value)
                    logger.debug(f"  有效信息价：{price_value}（{record.date.strftime('%Y-%m')}）")
                except ValueError:
                    logger.warning(f"  {citypy} 字段值格式无效（{price_value}），跳过")
                    continue

            # 计算信息价（单月取当月值，多月取平均）
            if info_prices:
                if months_duration == 1:
                    project_info_price = round(info_prices[-1], 2)  # 单月取当月值（通常只有1条）
                    logger.debug(f"  单月项目信息价：{project_info_price}")
                else:
                    project_info_price = round(sum(info_prices) / len(info_prices), 2)
                    logger.debug(f"  多月项目平均信息价：{project_info_price}（共{len(info_prices)}条）")
            else:
                logger.warning(f"  未找到匹配的有效信息价")

        # 加入项目数据列表
        project_data.append({
            'name': project_name,
            'date': month_str or (year_str if year_str else start_date.strftime('%Y-%m')),
            'price': float(item['avg_price']),
            'region': item['project_mapping__region__city'],
            'region_py': citypy,
            'info_price': project_info_price,
            'project_period': f"{project_start.strftime('%Y-%m')}至{project_end.strftime('%Y-%m')}",
            'duration_months': months_duration
        })

    # 组织整体参考价数据
    reference_price_data = []
    if start_date and end_date:
        if year_str:
            # 全年参考价：按地区计算每月平均
            region_yearly_prices = {r.citypy: [] for r in regions.values()}
            for record in price_records:
                for citypy, region in regions.items():
                    if hasattr(record, citypy):
                        price_value = getattr(record, citypy)
                        if price_value and isinstance(price_value, (int, float)) and price_value >= 0:
                            region_yearly_prices[citypy].append(float(price_value))
            entry = {'date': year_str}
            for citypy, prices in region_yearly_prices.items():
                if prices:
                    entry[regions[citypy].city] = round(sum(prices) / len(prices), 2)
            reference_price_data.append(entry)
        else:
            # 单月参考价：取当月平均值
            region_monthly_prices = {r.citypy: [] for r in regions.values()}
            for record in price_records:
                for citypy, region in regions.items():
                    if hasattr(record, citypy):
                        price_value = getattr(record, citypy)
                        if price_value and isinstance(price_value, (int, float)) and price_value >= 0:
                            region_monthly_prices[citypy].append(float(price_value))
            entry = {'date': start_date.strftime('%Y-%m')}
            for citypy, prices in region_monthly_prices.items():
                if prices:
                    entry[regions[citypy].city] = round(sum(prices) / len(prices), 2)
            reference_price_data.append(entry)

    return JsonResponse({
        'project_data': project_data,
        'reference_price_data': reference_price_data
    }, safe=False, json_dumps_params={'ensure_ascii': False})


@login_required
def chart_hnt_line(request):
    """
    折线图页面
    """
    # 获取所有地区（去重的市级数据）- 只获取城市记录（district为空的记录）
    regions = Region.objects.filter(district='').order_by('city')

    context = {
        'regions': regions,
        'title': '商品混凝土C30价格趋势折线图'
    }

    return render(request, 'hnt-visual-line.html', context)


@login_required
def chart_hnt_line_data(request):
    """
    获取折线图数据
    """
    region_field = request.GET.get('region')  # 地区拼音
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    print(f"请求参数: region={region_field}, start_date={start_date_str}, end_date={end_date_str}")

    # 日期处理
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

    print(f"解析后的日期: start_date={start_date}, end_date={end_date}")

    # 获取地区对象 - 只匹配城市记录（district为空）
    region = Region.objects.filter(citypy=region_field, district='').first()
    if not region:
        print(f"未找到地区: {region_field}")
        return JsonResponse({'error': '无效的地区'}, status=400)

    print(f"找到地区: {region.city} ({region.citypy})")

    # 查询项目数据 - 匹配该城市的所有地区记录（包括区县）
    project_mappings = ProjectMapping.objects.filter(region__citypy=region_field)
    print(f"找到 {project_mappings.count()} 个项目映射")

    project_query = Project.objects.filter(
        project_mapping__in=project_mappings,
        specification__category__category_name='商品混凝土',
        specification__specification_name='C30'
    )

    if start_date:
        project_query = project_query.filter(arrival_date__gte=start_date)
    if end_date:
        project_query = project_query.filter(arrival_date__lte=end_date)

    print(f"项目查询条件后的数量: {project_query.count()}")

    # 如果没有找到数据，尝试扩大时间范围
    if project_query.count() == 0:
        print("未找到项目数据，尝试查找最近的数据...")
        # 查找该地区最近的项目数据
        recent_project = Project.objects.filter(
            project_mapping__in=project_mappings,
            specification__category__category_name='商品混凝土',
            specification__specification_name='C30'
        ).order_by('-arrival_date').first()

        if recent_project:
            # 使用最近数据的日期重新查询
            recent_date = recent_project.arrival_date
            start_date = date(recent_date.year, 1, 1)  # 年初
            end_date = date(recent_date.year, 12, 31)  # 年末

            project_query = Project.objects.filter(
                project_mapping__in=project_mappings,
                specification__category__category_name='商品混凝土',
                specification__specification_name='C30',
                arrival_date__gte=start_date,
                arrival_date__lte=end_date
            )
            print(f"使用最近数据年份 {recent_date.year}，重新查询后数量: {project_query.count()}")

    # 按项目和月份分组计算平均价格
    project_query = project_query.extra(
        select={'month': "DATE_FORMAT(arrival_date, '%%Y-%%m')"}
    ).values('project_mapping__project_name', 'month').annotate(
        avg_price=Avg('unit_price')
    ).order_by('project_mapping__project_name', 'month')

    # 组织项目数据
    project_data = []
    for item in project_query:
        if item['avg_price'] is not None:
            project_data.append({
                'name': item['project_mapping__project_name'],
                'date': item['month'],
                'price': float(item['avg_price'])
            })
    print('project_data', project_data)

    # 查询信息价数据
    price_query = ConcretePrice.objects.all()
    if start_date:
        price_query = price_query.filter(date__gte=start_date)
    if end_date:
        price_query = price_query.filter(date__lte=end_date)
    prices = price_query.order_by('date')
    print(f"信息价数据数量: {prices.count()}")

    # 组织信息价数据
    reference_price_data = []
    for price in prices:
        month_key = price.date.strftime('%Y-%m')
        if hasattr(price, region_field):
            reference_price_data.append({
                'date': month_key,
                'price': float(getattr(price, region_field) or 0)
            })

    # 查询该地区所有项目的平均价格（按月份分组）
    average_query = Project.objects.filter(
        project_mapping__in=project_mappings,
        specification__category__category_name='商品混凝土',
        specification__specification_name='C30'
    )

    if start_date:
        average_query = average_query.filter(arrival_date__gte=start_date)
    if end_date:
        average_query = average_query.filter(arrival_date__lte=end_date)

    print(f"平均价格查询条件后的数量: {average_query.count()}")

    # 如果没有找到平均价格数据，但有项目数据，则使用项目数据计算平均值
    if average_query.count() == 0 and len(project_data) > 0:
        print("未找到平均价格数据，从项目数据中计算...")
        # 从项目数据中按月份计算平均值
        from collections import defaultdict
        monthly_prices = defaultdict(list)

        for item in project_data:
            monthly_prices[item['date']].append(item['price'])

        average_price_data = []
        for month, prices in monthly_prices.items():
            avg_price = sum(prices) / len(prices)
            average_price_data.append({
                'date': month,
                'price': round(avg_price, 2)
            })
        print("从项目数据计算的平均价格:", average_price_data)
    else:
        # 按月份分组计算平均价格
        average_query = average_query.extra(
            select={'month': "DATE_FORMAT(arrival_date, '%%Y-%%m')"}
        ).values('month').annotate(
            avg_price=Avg('unit_price')
        ).order_by('month')

        # 组织平均价格数据
        average_price_data = []
        for item in average_query:
            if item['avg_price'] is not None:
                average_price_data.append({
                    'date': item['month'],
                    'price': float(item['avg_price'])
                })
        print("average_price_data:", average_price_data)

    return JsonResponse({
        'project_data': project_data,
        'reference_price_data': reference_price_data,
        'average_price_data': average_price_data
    }, safe=False, json_dumps_params={'ensure_ascii': False})


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
    # 获取选中地区的所有项目映射 - 匹配城市拼音即可（包括所有区县）
    region_instances = Region.objects.filter(citypy__in=region_fields)
    project_mappings = ProjectMapping.objects.filter(region__citypy__in=region_fields)

    # 获取这些映射下的所有项目
    project_query = Project.objects.filter(
        project_mapping__in=project_mappings,
        specification__category__category_name='商品混凝土',
        specification__specification_name='C30'
    )
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
                region_obj = Region.objects.filter(citypy=region, district='').first()
                if region_obj:
                    entry[region_obj.city] = float(getattr(price, region) or 0)
        reference_price_data.append(entry)

    return JsonResponse({
        'project_data': project_data,
        'reference_price_data': reference_price_data,
        'regions': [r.city for r in region_instances.filter(district='')]
    }, safe=False, json_dumps_params={'ensure_ascii': False})
