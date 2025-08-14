from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    扩展Django内置User模型
    """
    USER_PERMISSION_CHOICES = [
        ('normal', '普通用户'),
        ('admin', '管理员'),
    ]

    phone = models.CharField('手机号', max_length=15, blank=True)
    email = models.EmailField('邮箱')
    permission = models.CharField('权限', max_length=10, choices=USER_PERMISSION_CHOICES, default='normal')

    class Meta:
        db_table = 'USER'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username

    def is_admin(self):
        """判断是否为管理员"""
        return self.permission == 'admin'
