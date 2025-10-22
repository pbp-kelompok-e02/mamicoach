from django import forms
from .models import Course, Category


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "category",
            "title",
            "description",
            "location",
            "price",
            "duration",
            "thumbnail_url",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "placeholder": "Nama Kelas (contoh: Yoga Pemula)",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "rows": 4,
                    "placeholder": "Deskripsi lengkap tentang kelas ini...",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "placeholder": "Lokasi kelas (contoh: Jl. Kemang Raya No.7, Jakarta Selatan)",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "placeholder": "Harga per sesi (Rp)",
                }
            ),
            "duration": forms.NumberInput(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "placeholder": "Durasi dalam menit",
                }
            ),
            "thumbnail_url": forms.URLInput(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
                    "placeholder": "URL gambar kelas (opsional)",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "block w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["thumbnail_url"].required = False
        self.fields["category"].empty_label = "Pilih Kategori"
