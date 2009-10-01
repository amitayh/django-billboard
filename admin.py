from django.contrib import admin
from project.billboard.models import *

class PropertyValueAdmin(admin.ModelAdmin):
    list_display = ('value',)
    list_filter = ('property',)

admin.site.register(Category)
admin.site.register(Property)
admin.site.register(Ad)
admin.site.register(AdPropertyValue)
admin.site.register(PropertyValueText, PropertyValueAdmin)
admin.site.register(PropertyValueChoice, PropertyValueAdmin)
admin.site.register(PropertyValueTree, PropertyValueAdmin)