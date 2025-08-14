# apps/users/migrations/XXXX_create_default_admin.py (XXXX是自动生成的编号)
from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')

    # 检查是否已存在admin用户
    if not User.objects.filter(username='admin').exists():
        User.objects.create(
            username='admin',
            password=make_password('admin'),  # 使用Django的密码哈希函数
            email='admin@example.com',
            phone='13800000000',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )


def remove_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(username='admin').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),  # 确保这是最新的迁移文件
    ]

    operations = [
        migrations.RunPython(create_default_admin, remove_default_admin),
    ]
