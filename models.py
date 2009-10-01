from django.db import models
import mptt

class Category(models.Model):
    name            = models.CharField(max_length=255, unique=True)
    description     = models.TextField(null=True, blank=True)
    parent          = models.ForeignKey('self', null=True, blank=True, related_name='children')
    ads_count       = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['tree_id', 'lft']
    
    def __unicode__(self):
        return u'%s' % self.name
    
    def offset(self):
        return u'--' * self.level
    
    def get_properties(self):
        pass

mptt.register(Category)

class Property(models.Model):

    VALUE_TYPES = (
        (0, 'Text'),
        (1, 'Choice'),
        (2, 'Tree'),
    )
    
    name            = models.CharField(max_length=255, unique=True)
    description     = models.TextField(null=True, blank=True)
    type            = models.IntegerField(choices=VALUE_TYPES, default=0)
    categories      = models.ManyToManyField(Category)
    
    class Meta:
        verbose_name_plural = 'Properties'
    
    def __unicode__(self):
        return u'%s' % self.name

class PropertyValue(models.Model):
    property        = models.ForeignKey(Property)
    value           = models.CharField(max_length=255)

    class Meta:
        abstract = True
    
    def __unicode__(self):
        return u'%s' % self.value

class PropertyValueText(PropertyValue):
    pass

class PropertyValueChoice(PropertyValue):
    pass

class PropertyValueTree(PropertyValue):
    parent          = models.ForeignKey('self', null=True, blank=True, related_name='children')
    
    class Meta:
        ordering = ['tree_id', 'lft']

mptt.register(PropertyValueTree)

class Ad(models.Model):
    name            = models.CharField(max_length=255)
    description     = models.TextField()
    categories      = models.ManyToManyField(Category)
    
    def __unicode__(self):
        return u'%s' % self.name
    
    def get_properties(self):
        pass

class AdPropertyValue(models.Model):
    ad              = models.ForeignKey(Ad)
    property        = models.ForeignKey(Property)
    property_value  = models.IntegerField()