from django import template
from datetime import date

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@register.filter
def days_remaining(due_date):
    if not due_date:
        return ""
    return (due_date - date.today()).days