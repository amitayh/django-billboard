from django import forms
from django.db import models, connection
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
    
    def get_properties(self, types=('Choice', 'Tree')):
        type_ids = [k for k, v in Property.VALUE_TYPES if v in types]
        categories = [category.id for category in self.get_ancestors()]
        categories.append(self.id)
        return Property.objects.filter(type__in=type_ids, categories__in=categories)

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
    
    def get_values(self):
        model = 'PropertyValue' + dict(self.VALUE_TYPES)[self.type]
        return globals()[model].objects.filter(property=self)

class PropertyValue(models.Model):
    property        = models.ForeignKey(Property)
    value           = models.CharField(max_length=255)
    field           = forms.CharField

    class Meta:
        abstract = True
    
    def __unicode__(self):
        return u'%s' % self.value
    
    def get_value(self):
        return u'%s' % self.value

class PropertyValueText(PropertyValue):
    pass

class PropertyValueChoice(PropertyValue):
    field           = forms.ChoiceField

class PropertyValueTree(PropertyValue):
    parent          = models.ForeignKey('self', null=True, blank=True, related_name='children')
    field           = forms.ChoiceField
    
    class Meta:
        ordering = ['tree_id', 'lft']
    
    def get_value(self):
        return u'%s %s' % ('--' * self.level, self.value)

mptt.register(PropertyValueTree)

class Ad(models.Model):
    name            = models.CharField(max_length=255)
    description     = models.TextField()
    category        = models.ForeignKey(Category)
    
    def __unicode__(self):
        return u'%s' % self.name
    
    def get_properties(self):
        case_sql = []
        join_sql = []
        property_db_table = Property._meta.db_table
        adpropertyvalue_db_table = AdPropertyValue._meta.db_table
        for type_id, type_name in Property.VALUE_TYPES:
            model = globals()['PropertyValue' + type_name]
            db_table = model._meta.db_table
            case_sql.append('WHEN %(type_id)d THEN `%(db_table)s`.`value`' % {'type_id': type_id, 'db_table': db_table})
            join_sql.append(
                'LEFT JOIN `%(db_table)s` ON (`%(property)s`.`type` = %(type_id)d AND `%(adpropertyvalue)s`.`property_value` = `%(db_table)s`.`id`)' %
                {'db_table': db_table, 'type_id': type_id, 'property': property_db_table, 'adpropertyvalue': adpropertyvalue_db_table}
            )
        
        sql = """
            SELECT
                `%(property)s`.`id`,
                `%(property)s`.`name`,
                CASE `%(property)s`.`type`
                    %(case_sql)s
                END `value`
            FROM `%(property)s`
            JOIN `%(adpropertyvalue)s` ON `%(property)s`.`id` = `%(adpropertyvalue)s`.`property_id`
            %(join_sql)s
            WHERE `%(adpropertyvalue)s`.`ad_id` = %(ad_id)d
        """
        
        params = {
            'case_sql': "\n".join(case_sql),
            'join_sql': "\n".join(join_sql),
            'property': property_db_table,
            'adpropertyvalue': adpropertyvalue_db_table,
            'ad_id': self.id
        }
        
        cursor = connection.cursor()
        cursor.execute(sql % params)
        return cursor.fetchall()

class AdPropertyValue(models.Model):
    ad              = models.ForeignKey(Ad)
    property        = models.ForeignKey(Property)
    property_value  = models.IntegerField()