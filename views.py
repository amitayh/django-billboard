from django.shortcuts import get_object_or_404
from project.shortcuts import render_response
from project.billboard.models import *

def index(request):
    categories = Category.objects.all()
    return render_response(request, 'billboard/index.html', {
        'categories': categories,
    })

def category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    topcategories = category.get_ancestors()
    subcategories = category.get_children()
    properties = category.get_properties()
    return render_response(request, 'billboard/category.html', {
        'category': category,
        'topcategories': topcategories,
        'subcategories': subcategories,
        'properties': properties,
    })