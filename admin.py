from django.contrib import admin
from project.billboard.models import *

class AdPropertyValueInline(admin.TabularInline):
    model = AdPropertyValue
    extra = 1

class AdAdmin(admin.ModelAdmin):
    fields = ['name', 'description', 'category']
    inlines = [AdPropertyValueInline]

class PropertyValueAdmin(admin.ModelAdmin):
    list_display = ('value',)
    list_filter = ('property',)

admin.site.register(Category)
admin.site.register(Property)
admin.site.register(Ad, AdAdmin)
admin.site.register(PropertySet)
admin.site.register(PropertyValueText, PropertyValueAdmin)
admin.site.register(PropertyValueChoice, PropertyValueAdmin)
admin.site.register(PropertyValueTree, PropertyValueAdmin)