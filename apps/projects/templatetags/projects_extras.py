# apps/projects/templatetags/projects_extras.py
from django import template
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def sortable_header(context, display_name, sort_field):
    """
    生成可排序的表头
    """
    request = context['request']

    # 获取当前的排序参数
    current_sort = request.GET.get('sort', 'arrival_date')
    current_order = request.GET.get('order', 'desc')

    # 构建新的排序参数
    if sort_field == current_sort:
        # 如果点击的是当前排序字段，则切换排序方向
        new_order = 'asc' if current_order == 'desc' else 'desc'
    else:
        # 如果点击的是其他字段，默认降序排列
        new_order = 'desc'

    # 构建新的查询参数
    query_params = request.GET.copy()
    query_params['sort'] = sort_field
    query_params['order'] = new_order

    # 保持其他查询参数（如分页）
    url = f'?{urlencode(query_params)}'

    # 添加排序指示器
    if sort_field == current_sort:
        indicator = ' ↑' if current_order == 'asc' else ' ↓'
    else:
        indicator = ''

    # 生成HTML
    html = f'<a href="{url}" class="text-decoration-none">{display_name}{indicator}</a>'
    return mark_safe(html)
