from django.db import models

from apps.category.models import MaterialCategory


class Specification(models.Model):
    """
    规格表，与物资类别关联
    """
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(MaterialCategory, on_delete=models.CASCADE, verbose_name='物资类别')
    specification_name = models.CharField('规格名称', max_length=200)

    class Meta:
        db_table = 'SPECIFICATION'
        verbose_name = '规格'
        verbose_name_plural = '规格'
        unique_together = ('category', 'specification_name')  # 同一类别下规格名称唯一

    def __str__(self):
        return f"{self.category.category_name} - {self.specification_name}"
