from django.conf.urls.defaults import *

urlpatterns = patterns(
    'project.billboard.views',
    url(r'^$', 'index', name='billboard-index'),
    url(r'^category/(?P<category_id>\d+)/$', 'category', name='billboard-category'),
    # url(r'^ad/(?P<ad_id>\d+)/$', 'ad', name='billboard-add'),
)