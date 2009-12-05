from django import forms
from django.db import models, connection
from math import ceil
import mptt

"""
SELECT billboard_ad.*
FROM billboard_ad
JOIN billboard_adpropertyvalue a ON a.ad_id = billboard_ad.id
JOIN billboard_adpropertyvalue b ON b.ad_id = billboard_ad.id
WHERE billboard_ad.category_id IN (1, 2, 6)
AND a.property_id = 1 AND a.property_value = 1
AND b.property_id = 5 AND b.property_value = 11
GROUP BY billboard_ad.id


from django.db.models import Q
AdPropertyValue.objects.select_related('ad').filter(Q(property=1, property_value=1) | Q(property=2, property_value=4))

"""

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
    
    def get_ads(self, search=[], ads_per_page=15, page=1):
        ads_per_page = int(ads_per_page)
        page = int(page)
        ad_db_table = Ad._meta.db_table
        adpropertyvalue_db_table = AdPropertyValue._meta.db_table
        join_sql = []
        where_sql = []
        if search:
            for property, value in search:
                join_sql.append(
                    'JOIN `%(adpropertyvalue)s` `p%(property)d` ON `p%(property)d`.`ad_id` = `%(ad)s`.`id`' %
                    {'adpropertyvalue': adpropertyvalue_db_table, 'property': property, 'ad': ad_db_table}
                )
                where_sql.append(
                    'AND `p%(property)d`.`property_id` = %(property)d AND `p%(property)d`.`property_value` = %(property_value)d' %
                    {'property': property, 'property_value': value}
                )
        
        sql = """
            SELECT SQL_CALC_FOUND_ROWS `%(ad)s`.*
            FROM `%(ad)s`
            %(join_sql)s
            WHERE `%(ad)s`.`category_id` IN (%(categories)s)
            %(where_sql)s
            GROUP BY `%(ad)s`.`id`
            LIMIT %(offset)d, %(rowcount)d
        """
        
        params = {
            'ad': ad_db_table,
            'join_sql': "\n".join(join_sql),
            'categories': ', '.join([str(category.id) for category in self.get_descendants(include_self=True)]),
            'where_sql': "\n".join(where_sql),
            'offset': (page - 1) * ads_per_page,
            'rowcount': ads_per_page
        }
        
        cursor = connection.cursor()
        cursor.execute(sql % params)
        ads = [Ad(*row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT FOUND_ROWS()")
        found_rows = int(cursor.fetchone()[0])
        
        return {
            'object_list': ads,
            'count': found_rows,
            'num_pages': int(ceil(found_rows / float(ads_per_page)))
        }
    
    def get_properties(self, types=('Choice', 'Tree')):
        type_ids = [k for k, v in Property.VALUE_TYPES if v in types]
        categories = [category.id for category in self.get_ancestors()]
        categories.append(self.id)
        return Property.objects.filter(type__in=type_ids, categories__in=categories)

mptt.register(Category)

class PropertySet(models.Model):
    name            = models.CharField(max_length=255, unique=True)
    
    def __unicode__(self):
        return u'%s' % self.name

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
    set             = models.ForeignKey(PropertySet)
    
    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['name']
    
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
        ordering = ['value']
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
    
    # def save(self):
    #     super(Ad, self).save()
    
    def get_properties(self):
        case_sql = []
        join_sql = []
        property_db_table = Property._meta.db_table
        propertyset_db_table = PropertySet._meta.db_table
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
                `%(propertyset)s`.`name` `set`,
                `%(property)s`.`id`,
                `%(property)s`.`name`,
                CASE `%(property)s`.`type`
                    %(case_sql)s
                END `value`
            FROM `%(property)s`
            JOIN `%(adpropertyvalue)s` ON `%(property)s`.`id` = `%(adpropertyvalue)s`.`property_id`
            LEFT JOIN `%(propertyset)s` ON `%(property)s`.`set_id` = `%(propertyset)s`.`id`
            %(join_sql)s
            WHERE `%(adpropertyvalue)s`.`ad_id` = %(ad_id)d
            ORDER BY `set`, `name`
        """
        
        params = {
            'case_sql': "\n".join(case_sql),
            'join_sql': "\n".join(join_sql),
            'property': property_db_table,
            'propertyset': propertyset_db_table,
            'adpropertyvalue': adpropertyvalue_db_table,
            'ad_id': self.id
        }
        
        # return sql % params
        
        cursor = connection.cursor()
        cursor.execute(sql % params)
        properties = {}
        for row in cursor.fetchall():
            if not row[0] in properties:
                properties[row[0]] = []
            properties[row[0]].append(row[1:])
        
        return properties.items()

class AdPropertyValue(models.Model):
    ad              = models.ForeignKey(Ad)
    property        = models.ForeignKey(Property)
    property_value  = models.IntegerField()