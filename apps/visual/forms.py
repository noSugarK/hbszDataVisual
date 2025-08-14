# apps/visual/forms.py
from django import forms
from .models import Project, ProjectMapping, MaterialCategory, Specification, Brand
from ..common.models import Region, Supplier
from ..users.models import User


# apps/visual/forms.py
from django import forms
from .models import Project, ProjectMapping, MaterialCategory, Specification, Brand
from ..common.models import Region, Supplier
from ..users.models import User


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'project_mapping',
            'arrival_date',
            'supplier',
            'category',
            'specification',
            'quantity',
            'unit_price',
            'discount_rate',
            'brand'
        ]
        widgets = {
            'arrival_date': forms.DateInput(attrs={'type': 'date'}),
            'project_mapping': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'specification': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化供应商选项
        self.fields['supplier'].queryset = Supplier.objects.all()
        # 初始化规格选项为空，通过前端联动加载
        self.fields['specification'].queryset = Specification.objects.none()

        # 如果是编辑状态且已有关联的类别，则加载对应的规格
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['specification'].queryset = Specification.objects.filter(
                    category_id=category_id
                )
            except (ValueError, TypeError):
                pass  # 无效的类别ID
        elif self.instance.pk:
            # 编辑现有项目时，加载已选择类别的规格
            self.fields['specification'].queryset = Specification.objects.filter(
                category_id=self.instance.category_id
            )




class ProjectMappingForm(forms.ModelForm):
    """
    项目映射表单
    """
    class Meta:
        model = ProjectMapping
        fields = ['project_name', 'region']
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
        }


class ProjectSearchForm(forms.Form):
    """
    项目搜索表单
    """
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        label='地区'
    )

    project_mapping = forms.ModelChoiceField(
        queryset=ProjectMapping.objects.all(),
        required=False,
        label='项目名称'
    )

    category = forms.ModelChoiceField(
        queryset=MaterialCategory.objects.all(),
        required=False,
        label='物资类别'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 根据地区过滤项目映射
        if 'region' in self.data and self.data['region']:
            try:
                region_id = int(self.data['region'])
                self.fields['project_mapping'].queryset = ProjectMapping.objects.filter(
                    region_id=region_id
                )
            except (ValueError, TypeError):
                self.fields['project_mapping'].queryset = ProjectMapping.objects.none()

        # 根据类别过滤规格
        if 'category' in self.data and self.data['category']:
            try:
                category_id = int(self.data['category'])
                self.fields['specification'].queryset = Specification.objects.filter(
                    category_id=category_id
                )
            except (ValueError, TypeError):
                self.fields['specification'].queryset = Specification.objects.none()
