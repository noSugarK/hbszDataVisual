# apps/visual/models.py
from django.db import models
from ..common.models import Region, Supplier, Brand
from ..users.models import User

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

class ProjectMapping(models.Model):
    """
    项目映射表
    """
    id = models.AutoField(primary_key=True)
    project_name = models.CharField('项目名称', max_length=200)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='地区')

    class Meta:
        db_table = 'PROJECT_MAPPING'
        verbose_name = '项目映射'
        verbose_name_plural = '项目映射'

    def __str__(self):
        return f"{self.project_name} ({self.region})"

class Project(models.Model):
    """
    项目表
    """
    id = models.AutoField(primary_key=True)
    project_mapping = models.ForeignKey(ProjectMapping, on_delete=models.CASCADE, verbose_name='项目映射')
    arrival_date = models.DateField('到货日期')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='供应商')  # 确保有这行
    category = models.ForeignKey(MaterialCategory, on_delete=models.CASCADE, verbose_name='物资类别')
    specification = models.ForeignKey(Specification, on_delete=models.CASCADE, verbose_name='规格')
    quantity = models.DecimalField('数量', max_digits=15, decimal_places=2)
    unit_price = models.DecimalField('单价', max_digits=15, decimal_places=2)
    discount_rate = models.DecimalField('下浮率', max_digits=15, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField('合计', max_digits=15, decimal_places=2, blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, verbose_name='品牌')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='填报用户')

    class Meta:
        db_table = 'PROJECT'
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-arrival_date']

    def __str__(self):
        if self.project_mapping:
            return f"{self.project_mapping.project_name} - {self.arrival_date}"
        return f"项目 - {self.arrival_date}"

    @property
    def region(self):
        """通过项目映射获取地区信息"""
        if self.project_mapping and self.project_mapping.region:
            return self.project_mapping.region
        return None

    def save(self, *args, **kwargs):
        # 自动计算合计金额
        if self.quantity and self.unit_price:
            self.total_amount = self.quantity * self.unit_price
            # 如果有下浮率，需要调整合计金额
            if self.discount_rate:
                self.total_amount = self.total_amount * (1 - self.discount_rate / 100)
        super().save(*args, **kwargs)

class DataUpload(models.Model):
    """
    数据上传记录表
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    file_path = models.CharField('文件路径', max_length=500)
    upload_time = models.DateTimeField('上传时间', auto_now_add=True)
    status = models.CharField('状态', max_length=20, default='pending')

    class Meta:
        db_table = 'DATA_UPLOAD'
        verbose_name = '数据上传记录'
        verbose_name_plural = '数据上传记录'
        ordering = ['-upload_time']

    def __str__(self):
        return f"{self.user.username} - {self.upload_time}"
