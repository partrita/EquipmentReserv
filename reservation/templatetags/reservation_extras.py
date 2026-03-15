from django import template

register = template.Library()

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def replace(value, arg):
    if "," in arg:
        old, new = arg.split(",")
        return value.replace(old, new)
    return value

@register.filter
def zfill(value, arg):
    return str(value).zfill(int(arg))
