from django.db import models
from pypinyin import lazy_pinyin

from apps.users.models import User


class Region(models.Model):
    """
    地区表
    """
    id = models.AutoField(primary_key=True)
    city = models.CharField('市', max_length=50)
    district = models.CharField('区/县', max_length=50, blank=True)
    citypy = models.CharField('市拼音', max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'REGION'
        verbose_name = '地区'
        verbose_name_plural = '地区'
        unique_together = ('city', 'district')

    def save(self, *args, **kwargs):
        # 自动生成城市拼音
        if not self.citypy and self.city:
            pinyin_list = lazy_pinyin(self.city)
            self.citypy = ''.join(pinyin_list).lower()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.district:
            return f"{self.city}-{self.district}"
        return self.city


class ConcretePrice(models.Model):
    """
    混凝土信息价表
    """
    id = models.AutoField(primary_key=True)
    date = models.DateField('日期')
    wuhan = models.DecimalField('武汉市', max_digits=10, decimal_places=2, null=True, blank=True)
    huanggang = models.DecimalField('黄冈市', max_digits=10, decimal_places=2, null=True, blank=True)
    xiangyang = models.DecimalField('襄阳市', max_digits=10, decimal_places=2, null=True, blank=True)
    shiyan = models.DecimalField('十堰市', max_digits=10, decimal_places=2, null=True, blank=True)
    jingzhou = models.DecimalField('荆州市', max_digits=10, decimal_places=2, null=True, blank=True)
    yichang = models.DecimalField('宜昌市', max_digits=10, decimal_places=2, null=True, blank=True)
    enshi = models.DecimalField('恩施市', max_digits=10, decimal_places=2, null=True, blank=True)
    suizhou = models.DecimalField('随州市', max_digits=10, decimal_places=2, null=True, blank=True)
    jingmen = models.DecimalField('荆门市', max_digits=10, decimal_places=2, null=True, blank=True)
    ezhou = models.DecimalField('鄂州市', max_digits=10, decimal_places=2, null=True, blank=True)
    xiantao = models.DecimalField('仙桃市', max_digits=10, decimal_places=2, null=True, blank=True)
    qianjiang = models.DecimalField('潜江市', max_digits=10, decimal_places=2, null=True, blank=True)
    tianmen = models.DecimalField('天门市', max_digits=10, decimal_places=2, null=True, blank=True)
    shennongjia = models.DecimalField('神农架', max_digits=10, decimal_places=2, null=True, blank=True)
    xianning = models.DecimalField('咸宁市', max_digits=10, decimal_places=2, null=True, blank=True)
    huangshi = models.DecimalField('黄石市', max_digits=10, decimal_places=2, null=True, blank=True)
    xiaogan = models.DecimalField('孝感市', max_digits=10, decimal_places=2, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='管理员')

    class Meta:
        db_table = 'CONCRETE_PRICE'
        verbose_name = '混凝土信息价'
        verbose_name_plural = '混凝土信息价'
        ordering = ['-date']

    def __str__(self):
        return f"混凝土信息价 - {self.date}"

# 在 models.py 中添加 Supplier 模型，在其他模型定义之后
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
