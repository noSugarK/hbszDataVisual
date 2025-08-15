from django.db import models

class Brand(models.Model):
    """
    品牌表
    """
    id = models.AutoField(primary_key=True)
    brand_name = models.CharField('品牌名称', max_length=100, unique=True)
    description = models.TextField('品牌描述', blank=True, null=True)

    class Meta:
        db_table = 'BRAND'
        verbose_name = '品牌'
        verbose_name_plural = '品牌'

    def __str__(self):
        return self.brand_name

