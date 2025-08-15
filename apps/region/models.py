from django.db import models
from pypinyin import lazy_pinyin


# Create your models here.
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
            clean_city = self.city.replace('市', '')
            pinyin_list = lazy_pinyin(clean_city)
            self.citypy = ''.join(pinyin_list).lower()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.district:
            return f"{self.city}-{self.district}"
        return self.city
