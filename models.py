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
    
    def offset(self):
        return '--' * self.level
    
    def get_properties(self, types=('Choice', 'Tree')):
        type_ids = [k for k, v in Property.VALUE_TYPES if v in types]
        categories = [category.pk for category in self.get_ancestors()]
        categories.append(self.pk)
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
        return eval(model).objects.filter(property=self)

class PropertyValue(models.Model):
    property        = models.ForeignKey(Property)
    value           = models.CharField(max_length=255)

    class Meta:
        abstract = True
    
    def __unicode__(self):
        return u'%s' % self.value
    
    def get_value(self):
        return u'%s' % self.value

class PropertyValueText(PropertyValue):
    pass

class PropertyValueChoice(PropertyValue):
    pass

class PropertyValueTree(PropertyValue):
    parent          = models.ForeignKey('self', null=True, blank=True, related_name='children')
    
    class Meta:
        ordering = ['tree_id', 'lft']
    
    def get_value(self):
        return u'%s %s' % ('--' * self.level, self.value)

mptt.register(PropertyValueTree)

class Ad(models.Model):
    name            = models.CharField(max_length=255)
    description     = models.TextField()
    categories      = models.ManyToManyField(Category)
    
    def __unicode__(self):
        return u'%s' % self.name
    
    def get_properties(self):
        case_sql = []
        join_sql = []
        for type_id, type_name in Property.VALUE_TYPES:
            model = eval('PropertyValue' + type_name)
            db_table = model._meta.db_table
            case_sql.append('WHEN %d THEN `%s`.`value`' % (type_id, db_table))
            join_sql.append('LEFT JOIN `%s` ON (`{property}`.`type` = %d AND `{adpropertyvalue}`.`property_value` = `%s`.`id`)' % (db_table, type_id, db_table))
        
        sql = """
            SELECT
                `{property}`.`id`,
                `{property}`.`name`,
                CASE `{property}`.`type`
                    {case_sql}
                END `value`
            FROM `{property}`
            JOIN `{adpropertyvalue}` ON `{property}`.`id` = `{adpropertyvalue}`.`property_id`
            {join_sql}
            WHERE `{adpropertyvalue}`.`ad_id` = %d
        """
        
        params = (
            ('case_sql', "\n".join(case_sql)),
            ('join_sql', "\n".join(join_sql)),
            ('property', Property._meta.db_table),
            ('adpropertyvalue', AdPropertyValue._meta.db_table),
        )
        
        for k, v in params: sql = sql.replace('{%s}' % k, v)
        
        cursor = connection.cursor()
        cursor.execute(sql % self.pk)
        return cursor.fetchall()

class AdPropertyValue(models.Model):
    ad              = models.ForeignKey(Ad)
    property        = models.ForeignKey(Property)
    property_value  = models.IntegerField()