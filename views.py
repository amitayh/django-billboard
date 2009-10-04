from django.shortcuts import get_object_or_404
from project.shortcuts import render_response
from project.billboard.models import *

def index(request):
    categories = Category.objects.all()
    return render_response(request, 'billboard/index.html', {
        'categories': categories,
    })

def category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    subcategories = category.get_children()
    properties = category.get_properties()
    ads = Ad.objects.filter(category__in=category.get_descendants(include_self=True))
    return render_response(request, 'billboard/category.html', {
        'category': category,
        'subcategories': subcategories,
        'properties': properties,
        'ads': ads,
    })

def ad(request, ad_id):
    ad = get_object_or_404(Ad, id=ad_id)
    return render_response(request, 'billboard/ad.html', {
        'ad': ad,
    })