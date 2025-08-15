from django import template

register = template.Library()

@register.filter
def getattribute(value, arg):
    """获取对象的属性值"""
    return getattr(value, arg, '')

@register.filter
def join(value, separator=','):
    """将列表连接成字符串"""
    if not value:
        return ''
    return separator.join(value)