from django import template

register = template.Library()


@register.filter
def get_result_week(obj, attr):
    return getattr(obj, f"result_{attr:02}")


@register.filter
def get_pick_week(obj, attr):
    return getattr(obj, f"pick_{attr:02}")
