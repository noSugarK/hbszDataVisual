# apps/users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserLoginForm(forms.Form):
    """用户登录表单"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入用户名'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )


class UserRegisterForm(forms.ModelForm):
    """用户注册表单"""
    password1 = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )
    password2 = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请再次输入密码'
        })
    )

    # 添加权限选择字段（仅超级管理员可见）
    permission = forms.ChoiceField(
        choices=[
            ('normal', '普通用户'),
            ('admin', '管理员')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name']  # 移除 last_name
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入用户名'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入邮箱地址'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入姓名'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # 根据当前用户权限调整表单
        if self.request_user and self.request_user.is_superuser:
            # 超级管理员可以看到权限选择
            self.fields['permission'].required = True
        else:
            # 管理员只能创建普通用户，隐藏权限字段
            del self.fields['permission']

    def clean_password2(self):
        """验证两次密码是否一致"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("两次输入的密码不一致")
        return password2

    def clean_username(self):
        """验证用户名是否已存在"""
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("该用户名已存在")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        # 根据权限设置用户角色
        if self.request_user and self.request_user.is_superuser:
            # 超级管理员可以设置权限
            permission = self.cleaned_data.get('permission', 'normal')
            user.permission = permission  # 使用 permission 字段
        else:
            # 管理员只能创建普通用户
            user.permission = 'normal'

        if commit:
            user.save()
        return user
