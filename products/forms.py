from django import forms

from .models import CategoryModel, PlatformModel, ProductGroupModel, ProductModel


class PlatformForm(forms.ModelForm):
    class Meta:
        model = PlatformModel
        fields = ["name", "show_only_from_not_verified_source", "description", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-textarea"}),
            "show_only_from_not_verified_source": forms.CheckboxInput(attrs={"class": "border border-gray-300 rounded"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-file-input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = CategoryModel
        fields = ["name", "platform", "stage", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "platform": forms.Select(attrs={"class": "form-select"}),
            "stage": forms.NumberInput(attrs={"class": "form-input"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-file-input"}),
        }

    def __init__(self, *args, **kwargs):
        plateform_id = kwargs.pop("plateform_id", None)
        super().__init__(*args, **kwargs)
        if plateform_id:
            qs = self.fields["platform"].queryset.filter(id=plateform_id)
            self.fields["platform"].queryset = qs
            self.initial["platform"] = qs.first()


class ProductForm(forms.ModelForm):
    class Meta:
        model = ProductModel
        fields = ["name", "price", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "price": forms.NumberInput(attrs={"class": "form-input"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-file-input"}),
        }

    def __init__(self, *args, **kwargs):
        category_id = kwargs.pop("category_id", None)
        super().__init__(*args, **kwargs)
        if category_id:
            qs = self.fields["category"].queryset.filter(id=category_id)
            self.fields["category"].queryset = qs
            self.initial["category"] = qs.first()


class ProductGroupForm(forms.ModelForm):
    class Meta:
        model = ProductGroupModel
        fields = ["name", "description", "stage", "target_total_price", "products_count", "profit"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "stage": forms.NumberInput(attrs={"class": "form-input", "min": "1", "step": "1"}),
            "target_total_price": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0.01"}),
            "products_count": forms.NumberInput(attrs={"class": "form-input", "min": "1", "step": "1"}),
            "profit": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
        }
