from django.db import models

from apps.users.models import User


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
