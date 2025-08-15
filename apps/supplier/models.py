from django.db import models


class Supplier(models.Model):
    """
    供应商表
    """
    id = models.AutoField(primary_key=True)
    supplier_name = models.CharField('供应商名称', max_length=200, unique=True)

    class Meta:
        db_table = 'SUPPLIER'
        verbose_name = '供应商'
        verbose_name_plural = '供应商'

    def __str__(self):
        return self.supplier_name
