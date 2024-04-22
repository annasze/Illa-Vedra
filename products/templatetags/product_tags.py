import re

from django import template

register = template.Library()


@register.filter
def paginate(value, arg):
    if re.search("(?<=page=)[\d]+", value):
        return re.sub("(?<=page=)[\d]+", str(arg), value)
    elif "?" not in value:
        return f"{value}?page={arg}"
    else:
        return f"{value}&page={arg}"


@register.simple_tag
def split(value, arg):
    return value.strip(arg).split(arg)


@register.filter
def multiply(value, arg):
    return value * arg


@register.simple_tag
def to_list(*args):
    return args

