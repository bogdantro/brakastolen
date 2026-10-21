from django.contrib import admin

from .models import Inquiry, InquiryNote, Plot, PlotCategory


class InquiryNoteInline(admin.TabularInline):
    model = InquiryNote
    extra = 0


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'interest', 'status', 'is_read', 'is_spam', 'created_at')
    list_filter = ('status', 'interest', 'is_spam', 'is_archived')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at',)
    inlines = [InquiryNoteInline]


@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = ('number', 'category', 'status', 'area_m2', 'price', 'altitude')
    list_filter = ('status', 'category')
    search_fields = ('number', 'note')


@admin.register(PlotCategory)
class PlotCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
