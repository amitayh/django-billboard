from django import forms
from django.db import models, connection
from math import ceil
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
    
    def get_ads(self, filter=[], ads_per_page=15, page=1):
        ads_per_page = int(ads_per_page)
        page = int(page)
        if page < 1:
            page = 1
        ad_db_table = Ad._meta.db_table
        adpropertyvalue_db_table = AdPropertyValue._meta.db_table
        join_sql = []
        where_sql = []
        if filter:
            
            filter_properties_ids = [property for property, value in filter]
            filter_properties = [(property.id, property.type) for property in Property.objects.filter(id__in=filter_properties_ids)]
            properties = {}
            for property_id, property_type in filter_properties:
                model = 'PropertyValue' + dict(Property.VALUE_TYPES)[property_type]
                properties[property_id] = globals()[model]
            
            for property, value in filter:
                join_sql.append(
                    'JOIN `%(adpropertyvalue)s` `p%(property)d` ON `p%(property)d`.`ad_id` = `%(ad)s`.`id`' %
                    {'adpropertyvalue': adpropertyvalue_db_table, 'property': property, 'ad': ad_db_table}
                )
                where_sql.append(properties[property].get_filter_sql(property, value))
        
        sql = """
            SELECT SQL_CALC_FOUND_ROWS `%(ad)s`.*
            FROM `%(ad)s`
            %(join_sql)s
            WHERE `%(ad)s`.`category_id` IN (
                SELECT `id`
                FROM `%(category)s`
                WHERE `lft` >= %(category_left)d
                AND `rght` <= %(category_right)d
            )
            %(where_sql)s
            GROUP BY `%(ad)s`.`id`
            LIMIT %(offset)d, %(rowcount)d
        """
        
        params = {
            'ad': ad_db_table,
            'category': self._meta.db_table,
            'category_left': self.lft,
            'category_right': self.rght,
            'join_sql': "\n".join(join_sql),
            'where_sql': "\n".join(where_sql),
            'offset': (page - 1) * ads_per_page,
            'rowcount': ads_per_page
        }
        
        cursor = connection.cursor()
        cursor.execute(sql % params)
        ads = [Ad(*row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT FOUND_ROWS()")
        found_rows = int(cursor.fetchone()[0])
        num_pages = int(ceil(found_rows / float(ads_per_page)))
        
        return {
            'object_list': ads,
            'count': found_rows,
            'num_pages': num_pages,
            'current_page': page,
            'page_range': range(1, num_pages + 1)
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
    
    @staticmethod
    def get_filter_sql(property, value):
        pattern = """
            AND `p%(property)d`.`property_id` = %(property)d
            AND `p%(property)d`.`property_value` = %(property_value)d
        """
        return pattern % {'property': property, 'property_value': value}

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
    
    @staticmethod
    def get_filter_sql(property, value):
        pattern = """
            AND `p%(property)d`.`property_id` = %(property)d
            AND `p%(property)d`.`property_value` IN (
                SELECT `p%(property)d_a`.`id`
                FROM `%(propertyvaluetree)s` `p%(property)d_a`
                JOIN `%(propertyvaluetree)s` `p%(property)d_b` ON (
                    `p%(property)d_a`.`property_id` = `p%(property)d_b`.`property_id`
                    AND `p%(property)d_a`.`tree_id` = `p%(property)d_b`.`tree_id`
                    AND `p%(property)d_a`.`lft` >= `p%(property)d_b`.`lft`
                    AND `p%(property)d_a`.`rght` <= `p%(property)d_b`.`rght`
                )
                WHERE `p%(property)d_b`.`id` = %(property_value)d
            )
        """
        return pattern % {'propertyvaluetree': PropertyValueTree._meta.db_table, 'property': property, 'property_value': value}

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