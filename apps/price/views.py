# apps/price/views.py
from datetime import timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from .models import ConcretePrice
from apps.region.models import Region
from apps.users.models import User
from django.contrib.auth.decorators import login_required
from functools import wraps

from ..projects.views import admin_required


@admin_required
def price_list(request):
    """信息价列表"""
    # 获取所有信息价记录，按日期倒序排列
    prices_list = ConcretePrice.objects.all().order_by('-date')

    # 分页
    paginator = Paginator(prices_list, 20)
    page_number = request.GET.get('page')
    prices = paginator.get_page(page_number)

    context = {
        'prices': prices,
        'title': '混凝土信息价列表'
    }
    return render(request, 'price_list.html', context)


@admin_required
def price_add(request):
    """添加信息价"""
    if request.method == 'POST':
        date_str = request.POST.get('date')
        action = request.POST.get('action', 'add')  # add, confirm, update

        if date_str:
            # 将月份字符串转换为该月第一天的日期
            try:
                # 解析年月格式（例如：2023-05）
                year, month = map(int, date_str.split('-'))
                # 设置为该月第一天
                target_date = date(year, month, 1)
            except ValueError:
                messages.error(request, '月份格式不正确！')
                return redirect('price:price_add')

            # 获取表单中提交的所有城市价格数据
            city_fields = [
                'wuhan', 'huanggang', 'xiangyang', 'shiyan', 'jingzhou',
                'yichang', 'enshi', 'suizhou', 'jingmen', 'ezhou',
                'xiantao', 'qianjiang', 'tianmen', 'shennongjia',
                'xianning', 'huangshi', 'xiaogan'
            ]

            # 收集表单数据
            form_data = {}
            for field in city_fields:
                value = request.POST.get(field, '')
                if value and value != '':
                    form_data[field] = float(value)
                else:
                    form_data[field] = None

            # 检查该日期是否已存在记录
            existing_price = ConcretePrice.objects.filter(date=target_date).first()

            if existing_price and action == 'add':
                # 日期已存在，显示确认页面
                context = {
                    'date': target_date,  # 使用实际日期格式
                    'form_data': form_data,
                    'existing_price': existing_price,
                    'title': '确认更新信息价'
                }
                return render(request, 'price_confirm.html', context)

            elif action == 'confirm':
                # 用户确认覆盖，执行更新操作
                if existing_price:
                    # 更新现有记录
                    updated_fields = []

                    for field in city_fields:
                        new_value = form_data.get(field)
                        existing_value = getattr(existing_price, field, None)

                        # 更新字段（包括设置为None的情况）
                        if new_value != existing_value:
                            setattr(existing_price, field, new_value)
                            updated_fields.append(field)

                    if updated_fields:
                        existing_price.user = request.user
                        existing_price.save()
                        messages.success(request,
                                         f'{target_date} 的信息价已更新！更新了 {len(updated_fields)} 个城市的字段。')
                    else:
                        messages.info(request, f'{target_date} 的信息价无变化。')
                else:
                    # 创建新记录
                    has_data = any(value is not None for value in form_data.values())

                    if has_data:
                        price = ConcretePrice(date=target_date, user=request.user)
                        for field, value in form_data.items():
                            setattr(price, field, value)
                        price.save()
                        messages.success(request, '信息价添加成功！')
                    else:
                        messages.warning(request, '未输入任何城市的价格信息，记录未保存。')

                return redirect('price:price_list')

            else:
                # 直接创建新记录（日期不存在的情况）
                has_data = any(value is not None for value in form_data.values())

                if has_data:
                    price = ConcretePrice(date=target_date, user=request.user)
                    for field, value in form_data.items():
                        setattr(price, field, value)
                    price.save()
                    messages.success(request, '信息价添加成功！')
                else:
                    messages.warning(request, '未输入任何城市的价格信息，记录未保存。')

                return redirect('price:price_list')
        else:
            messages.error(request, '请选择月份！')

    # GET请求 - 显示添加表单
    # 检查是否有日期参数，如果有的话检查是否已存在记录
    date_param = request.GET.get('date', '')
    existing_data = None

    if date_param:
        try:
            # 解析年月格式（例如：2023-05）
            year, month = map(int, date_param.split('-'))
            # 设置为该月第一天
            target_date = date(year, month, 1)
            # 检查是否存在记录
            existing_data = ConcretePrice.objects.filter(date=target_date).first()
        except ValueError:
            pass  # 日期格式不正确，忽略

    cities = [
        {'name': '武汉', 'field': 'wuhan', 'verbose_name': '武汉市'},
        {'name': '黄冈', 'field': 'huanggang', 'verbose_name': '黄冈市'},
        {'name': '襄阳', 'field': 'xiangyang', 'verbose_name': '襄阳市'},
        {'name': '十堰', 'field': 'shiyan', 'verbose_name': '十堰市'},
        {'name': '荆州', 'field': 'jingzhou', 'verbose_name': '荆州市'},
        {'name': '宜昌', 'field': 'yichang', 'verbose_name': '宜昌市'},
        {'name': '恩施', 'field': 'enshi', 'verbose_name': '恩施市'},
        {'name': '随州', 'field': 'suizhou', 'verbose_name': '随州市'},
        {'name': '荆门', 'field': 'jingmen', 'verbose_name': '荆门市'},
        {'name': '鄂州', 'field': 'ezhou', 'verbose_name': '鄂州市'},
        {'name': '仙桃', 'field': 'xiantao', 'verbose_name': '仙桃市'},
        {'name': '潜江', 'field': 'qianjiang', 'verbose_name': '潜江市'},
        {'name': '天门', 'field': 'tianmen', 'verbose_name': '天门市'},
        {'name': '神农架', 'field': 'shennongjia', 'verbose_name': '神农架'},
        {'name': '咸宁', 'field': 'xianning', 'verbose_name': '咸宁市'},
        {'name': '黄石', 'field': 'huangshi', 'verbose_name': '黄石市'},
        {'name': '孝感', 'field': 'xiaogan', 'verbose_name': '孝感市'},
    ]

    context = {
        'cities': cities,
        'title': '添加混凝土信息价',
        'date': date_param,
        'existing_data': existing_data
    }
    return render(request, 'price_add.html', context)


@admin_required
def price_edit(request, price_id):
    """编辑信息价"""
    price = get_object_or_404(ConcretePrice, id=price_id)

    if request.method == 'POST':
        date = request.POST.get('date')

        if date:
            # 获取表单中提交的所有城市价格数据
            city_fields = [
                'wuhan', 'huanggang', 'xiangyang', 'shiyan', 'jingzhou',
                'yichang', 'enshi', 'suizhou', 'jingmen', 'ezhou',
                'xiantao', 'qianjiang', 'tianmen', 'shennongjia',
                'xianning', 'huangshi', 'xiaogan'
            ]

            # 收集表单数据
            form_data = {}
            for field in city_fields:
                value = request.POST.get(field, '')
                if value and value != '':
                    form_data[field] = float(value)
                else:
                    form_data[field] = None

            # 检查该日期是否已存在其他记录
            existing_price = ConcretePrice.objects.filter(date=date).exclude(id=price_id).first()

            if existing_price:
                # 存在其他日期相同的记录，合并数据
                merged_fields = []
                for field in city_fields:
                    new_value = form_data.get(field)
                    existing_value = getattr(existing_price, field, None)

                    # 如果新值不为空而现有值为空，则更新现有记录
                    if new_value is not None and existing_value is None:
                        setattr(existing_price, field, new_value)
                        merged_fields.append(field)

                if merged_fields:
                    existing_price.user = request.user
                    existing_price.save()
                    messages.success(request,
                                     f'信息价已合并到 {date} 的记录中，更新了 {len(merged_fields)} 个城市的字段。')
                else:
                    messages.info(request, f'没有需要合并的数据。')

                # 删除当前记录
                price.delete()
                return redirect('price:price_list')
            else:
                # 更新当前记录
                price.date = date

                updated_fields = []
                for field in city_fields:
                    new_value = form_data.get(field)
                    existing_value = getattr(price, field, None)

                    if new_value != existing_value:
                        setattr(price, field, new_value)
                        updated_fields.append(field)

                price.user = request.user
                price.save()

                if updated_fields:
                    messages.success(request, f'信息价更新成功！更新了 {len(updated_fields)} 个城市的字段。')
                else:
                    messages.info(request, '信息价无变化。')

                return redirect('price:price_list')
        else:
            messages.error(request, '请选择日期！')

    # GET请求 - 显示编辑表单
    cities = [
        {'name': '武汉', 'field': 'wuhan', 'verbose_name': '武汉市'},
        {'name': '黄冈', 'field': 'huanggang', 'verbose_name': '黄冈市'},
        {'name': '襄阳', 'field': 'xiangyang', 'verbose_name': '襄阳市'},
        {'name': '十堰', 'field': 'shiyan', 'verbose_name': '十堰市'},
        {'name': '荆州', 'field': 'jingzhou', 'verbose_name': '荆州市'},
        {'name': '宜昌', 'field': 'yichang', 'verbose_name': '宜昌市'},
        {'name': '恩施', 'field': 'enshi', 'verbose_name': '恩施市'},
        {'name': '随州', 'field': 'suizhou', 'verbose_name': '随州市'},
        {'name': '荆门', 'field': 'jingmen', 'verbose_name': '荆门市'},
        {'name': '鄂州', 'field': 'ezhou', 'verbose_name': '鄂州市'},
        {'name': '仙桃', 'field': 'xiantao', 'verbose_name': '仙桃市'},
        {'name': '潜江', 'field': 'qianjiang', 'verbose_name': '潜江市'},
        {'name': '天门', 'field': 'tianmen', 'verbose_name': '天门市'},
        {'name': '神农架', 'field': 'shennongjia', 'verbose_name': '神农架'},
        {'name': '咸宁', 'field': 'xianning', 'verbose_name': '咸宁市'},
        {'name': '黄石', 'field': 'huangshi', 'verbose_name': '黄石市'},
        {'name': '孝感', 'field': 'xiaogan', 'verbose_name': '孝感市'},
    ]

    context = {
        'price': price,
        'cities': cities,
        'title': '编辑混凝土信息价'
    }
    return render(request, 'price_edit.html', context)


@admin_required
def price_delete(request, price_id):
    """删除信息价"""
    price = get_object_or_404(ConcretePrice, id=price_id)

    if request.method == 'POST':
        date = price.date
        price.delete()
        messages.success(request, f'{date} 的信息价删除成功！')
        return redirect('price:price_list')

    context = {
        'price': price,
        'title': '删除混凝土信息价'
    }
    return render(request, 'price_delete.html', context)


@login_required
def price_chart(request):
    """信息价图表展示"""
    # 获取所有城市拼音和名称
    regions = Region.objects.filter(district='').order_by('city')

    # 获取选中的城市（支持多选）
    cities_param = request.GET.get('cities', '')
    selected_cities = []
    if cities_param:
        selected_cities = cities_param.split(',')

    # 获取时间范围参数
    time_range = request.GET.get('time_range', '3m')  # 默认最近三个月

    context = {
        'regions': regions,
        'selected_cities': selected_cities,  # 这里传递列表
        'time_range': time_range,
        'title': '混凝土信息价图表'
    }
    return render(request, 'price_chart.html', context)

@login_required
def price_chart_data(request):
    """获取图表数据"""
    cities_param = request.GET.get('cities', '')
    time_range = request.GET.get('time_range', '3m')

    if not cities_param:
        return JsonResponse({'error': '请选择至少一个城市'})

    selected_cities = cities_param.split(',')

    # 根据城市拼音查找对应字段和中文名称
    city_info_map = {
        'wuhan': {'field': 'wuhan', 'name': '武汉市'},
        'huanggang': {'field': 'huanggang', 'name': '黄冈市'},
        'xiangyang': {'field': 'xiangyang', 'name': '襄阳市'},
        'shiyan': {'field': 'shiyan', 'name': '十堰市'},
        'jingzhou': {'field': 'jingzhou', 'name': '荆州市'},
        'yichang': {'field': 'yichang', 'name': '宜昌市'},
        'enshi': {'field': 'enshi', 'name': '恩施市'},
        'suizhou': {'field': 'suizhou', 'name': '随州市'},
        'jingmen': {'field': 'jingmen', 'name': '荆门市'},
        'ezhou': {'field': 'ezhou', 'name': '鄂州市'},
        'xiantao': {'field': 'xiantao', 'name': '仙桃市'},
        'qianjiang': {'field': 'qianjiang', 'name': '潜江市'},
        'tianmen': {'field': 'tianmen', 'name': '天门市'},
        'shennongjia': {'field': 'shennongjia', 'name': '神农架'},
        'xianning': {'field': 'xianning', 'name': '咸宁市'},
        'huangshi': {'field': 'huangshi', 'name': '黄石市'},
        'xiaogan': {'field': 'xiaogan', 'name': '孝感市'},
    }

    try:
        # 构建查询条件
        query = Q()
        valid_fields = []

        for city_py in selected_cities:
            city_info = city_info_map.get(city_py, {})
            field_name = city_info.get('field', '')
            if field_name:
                query |= Q(**{f'{field_name}__isnull': False})
                valid_fields.append((city_py, field_name, city_info.get('name', city_py)))

        if not valid_fields:
            return JsonResponse({'error': '无效的城市选择'})

        # 获取数据并根据时间范围过滤
        prices_queryset = ConcretePrice.objects.filter(query)

        # 根据时间范围过滤数据
        if time_range != 'all':
            end_date = timezone.now().date()
            if time_range == '3m':
                start_date = end_date - timedelta(days=90)
            elif time_range == '1y':
                start_date = end_date - timedelta(days=365)
            elif time_range == '2y':
                start_date = end_date - timedelta(days=730)

            prices_queryset = prices_queryset.filter(date__gte=start_date)

        prices = prices_queryset.order_by('date')

        # 检查是否有数据
        if not prices.exists():
            return JsonResponse({'error': '所选城市在指定时间范围内暂无信息价数据'})

        # 准备图表数据
        dates = list(prices.values_list('date', flat=True).distinct())
        dates = [date.strftime('%Y-%m-%d') for date in dates]

        datasets = []
        for city_py, field_name, city_name in valid_fields:
            # 获取该城市的所有价格数据
            city_prices = {}
            for price in prices:
                value = getattr(price, field_name, None)
                if value is not None:
                    city_prices[price.date.strftime('%Y-%m-%d')] = float(value)

            # 为每个日期创建数据点
            data_points = []
            for date in dates:
                data_points.append(city_prices.get(date, None))

            datasets.append({
                'label': f'{city_name}混凝土信息价',  # 使用中文名称
                'data': data_points,
            })

        data = {
            'labels': dates,
            'datasets': datasets
        }

        return JsonResponse(data)

    except Exception as e:
        # 记录错误日志
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取图表数据失败: {str(e)}")
        return JsonResponse({'error': f'获取数据失败: {str(e)}'})
