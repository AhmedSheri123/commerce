from django import forms
from django.contrib.auth.models import User
from accounts.models import UserProfile, SurveyQuestion, SurveyOption, Notification
from products.models import PlatformModel, CategoryModel, ProductModel
from management.models import SupportContact


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="كلمة المرور")
    password2 = forms.CharField(widget=forms.PasswordInput, label="تأكيد كلمة المرور")

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_active"]
        labels = {
            "username": "اسم المستخدم",
            "email": "البريد الإلكتروني",
            "first_name": "الاسم الأول",
            "last_name": "اسم العائلة",
            "is_active": "نشط",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()

    def _apply_styles(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "كلمتا المرور غير متطابقتين")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label="كلمة مرور جديدة (اختياري)",
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_active"]
        labels = {
            "username": "اسم المستخدم",
            "email": "البريد الإلكتروني",
            "first_name": "الاسم الأول",
            "last_name": "اسم العائلة",
            "is_active": "نشط",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()

    def _apply_styles(self):
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["balance", "total_earned", "is_verified", "from_verified_source", "is_enabled"]
        labels = {
            "balance": "الرصيد",
            "total_earned": "إجمالي الأرباح",
            "is_verified": "موثق",
            "from_verified_source": "من مصدر موثوق",
            "is_enabled": "الحساب مفعّل",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )


class SurveyQuestionForm(forms.ModelForm):
    class Meta:
        model = SurveyQuestion
        fields = ["text", "field_type", "is_required", "is_active", "order"]
        labels = {
            "text": "نص السؤال",
            "field_type": "نوع الإجابة",
            "is_required": "إجباري",
            "is_active": "مفعل",
            "order": "الترتيب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )


class SurveyOptionForm(forms.ModelForm):
    class Meta:
        model = SurveyOption
        fields = ["text", "value", "order"]
        labels = {
            "text": "النص",
            "value": "القيمة (اختياري)",
            "order": "الترتيب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "class",
                "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
            )


class UserProgressForm(forms.Form):
    platform = forms.ModelChoiceField(
        queryset=PlatformModel.objects.all(),
        required=True,
        label="المنصة",
    )
    category = forms.ModelChoiceField(
        queryset=CategoryModel.objects.select_related('platform').all(),
        required=True,
        label="الفئة",
    )
    product = forms.ModelChoiceField(
        queryset=ProductModel.objects.select_related('category', 'category__platform').all(),
        required=True,
        label="المنتج",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault(
                "class",
                "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
            )

    def clean(self):
        cleaned = super().clean()
        platform = cleaned.get("platform")
        category = cleaned.get("category")
        product = cleaned.get("product")

        if platform and category and category.platform_id != platform.id:
            self.add_error("category", "الفئة لا تنتمي إلى المنصة المختارة.")

        if category and product and product.category_id != category.id:
            self.add_error("product", "المنتج لا ينتمي إلى الفئة المختارة.")

        return cleaned

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["title", "message", "target_all", "target_user", "is_active"]
        labels = {
            "title": "Title",
            "message": "Message",
            "target_all": "Send to all users",
            "target_user": "Target user",
            "is_active": "Active",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_user"].required = False
        self.fields["target_user"].queryset = User.objects.filter(is_superuser=False).order_by("username")
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )

    def clean(self):
        cleaned = super().clean()
        target_all = cleaned.get("target_all")
        target_user = cleaned.get("target_user")
        if not target_all and not target_user:
            self.add_error("target_user", "Select a user when 'Send to all users' is disabled.")
        return cleaned


class SupportContactForm(forms.ModelForm):
    class Meta:
        model = SupportContact
        fields = ["platform", "title", "url", "icon", "is_active", "order"]
        labels = {
            "platform": "Platform",
            "title": "Title",
            "url": "URL / Handle",
            "icon": "Icon Image",
            "is_active": "Active",
            "order": "Order",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded",
                )
            else:
                field.widget.attrs.setdefault(
                    "class",
                    "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5",
                )
