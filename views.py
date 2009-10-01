from django.shortcuts import get_object_or_404
from project.shortcuts import render_response
from project.billboard.models import *

def index(request):
    categories = Category.objects.all()
    return render_response(request, 'billboard/index.html', {
        'categories': categories,
    })

def category(request):
    pass