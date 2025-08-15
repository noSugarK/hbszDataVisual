from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.projects.models import ProjectMapping
from apps.projects.views import admin_required
from apps.region.models import Region


@login_required
@admin_required
def region_list(request):
    """地区列表"""
    # 获取所有唯一城市
    city_names = Region.objects.values_list('city', flat=True).distinct().order_by('city')

    city_districts = {}
    for city_name in city_names:
        # 获取该城市的所有区县
        districts = Region.objects.filter(city=city_name).exclude(
            district=''
        ).exclude(
            district__isnull=True
        ).order_by('district')

        # 获取城市记录（用于编辑/删除操作）
        # 优先尝试获取district为空的记录，如果没有则使用该城市的第一条记录
        try:
            city_obj = Region.objects.get(city=city_name, district='')
        except Region.DoesNotExist:
            try:
                city_obj = Region.objects.get(city=city_name, district__isnull=True)
            except Region.DoesNotExist:
                # 如果找不到纯粹的城市记录，则使用该城市的第一条记录作为城市记录
                city_obj = Region.objects.filter(city=city_name).first()

        city_districts[city_name] = {
            'city_obj': city_obj,
            'districts': districts
        }

    # print("City districts data:", city_districts)
    context = {
        'city_districts': city_districts,
        'title': '地区管理'
    }
    return render(request, 'region_list.html', context)


@admin_required
@login_required
def region_add(request):
    """添加地区"""
    if request.method == 'POST':
        city = request.POST.get('city').strip()  # 去除首尾空格
        district = request.POST.get('district', '').strip()  # 去除首尾空格

        if city:
            if district:
                # 添加区县
                if Region.objects.filter(city=city, district=district).exists():
                    messages.error(request, '该区县已存在！')
                else:
                    Region.objects.create(city=city, district=district)
                    messages.success(request, '区县添加成功！')
                    return redirect('region:region_list')
            else:
                # 添加城市
                if Region.objects.filter(city=city, district='').exists():
                    messages.error(request, '该城市已存在！')
                else:
                    Region.objects.create(city=city, district='')
                    messages.success(request, '城市添加成功！')
                    return redirect('region:region_list')
        else:
            messages.error(request, '请填写城市名称！')

    context = {
        'title': '添加地区'
    }
    return render(request, 'region_add.html', context)



@login_required
@admin_required
def region_edit(request, region_id):
    """编辑地区"""
    region = get_object_or_404(Region, id=region_id)

    if request.method == 'POST':
        city = request.POST.get('city')
        district = request.POST.get('district', '')

        if city:
            # 检查是否重复
            if district:
                if Region.objects.filter(city=city, district=district).exclude(id=region_id).exists():
                    messages.error(request, '该区县已存在！')
                else:
                    region.city = city
                    region.district = district
                    region.save()
                    messages.success(request, '区县更新成功！')
                    return redirect('region:region_list')
            else:
                if Region.objects.filter(city=city, district='').exclude(id=region_id).exists():
                    messages.error(request, '该城市已存在！')
                else:
                    region.city = city
                    region.district = district
                    region.save()
                    messages.success(request, '城市更新成功！')
                    return redirect('region:region_list')
        else:
            messages.error(request, '请填写城市名称！')

    context = {
        'region': region,
        'title': '编辑地区'
    }
    return render(request, 'region_edit.html', context)


@login_required
@admin_required
def region_delete(request, region_id):
    """删除地区"""
    region = get_object_or_404(Region, id=region_id)

    if request.method == 'POST':
        # 检查是否有项目映射关联到这个地区
        if ProjectMapping.objects.filter(region=region).exists():
            messages.error(request, '无法删除该地区，因为还有项目映射使用它。')
            return redirect('region:region_list')

        region_name = str(region)
        region.delete()
        messages.success(request, f'地区 "{region_name}" 删除成功！')
        return redirect('region:region_list')

    context = {
        'region': region,
        'title': '删除地区'
    }
    return render(request, 'region_delete.html', context)

