from django.db import models

class MaterialCategory(models.Model):
    """
    物资类别表
    """
    id = models.AutoField(primary_key=True)
    category_name = models.CharField('类别名称', max_length=100, unique=True)

    class Meta:
        db_table = 'MATERIAL_CATEGORY'
        verbose_name = '物资类别'
        verbose_name_plural = '物资类别'

    def __str__(self):
        return self.category_name