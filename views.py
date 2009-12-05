from django.shortcuts import get_object_or_404
from django.http import Http404
from project.shortcuts import render_response
from project.billboard.models import *
import re

def index(request):
    categories = Category.objects.all()
    return render_response(request, 'billboard/index.html', {
        'categories': categories,
    })

def category(request, category_id, page=1):
    ads_per_page = 15
    category = get_object_or_404(Category, id=category_id)
    subcategories = category.get_children()
    properties = category.get_properties()
    filter = []
    request_lists = dict(request.GET.lists())
    if 'p' in request_lists:
        filter = [map(lambda x: int(x), v.split('_')) for v in request_lists['p'] if v != '0']
    ads = category.get_ads(filter, ads_per_page=ads_per_page, page=page)
    return render_response(request, 'billboard/category.html', {
        'category': category,
        'subcategories': subcategories,
        'properties': properties,
        'ads': ads
    })

def ad(request, ad_id):
    ad = get_object_or_404(Ad, id=ad_id)
    return render_response(request, 'billboard/ad.html', {
        'ad': ad
    })