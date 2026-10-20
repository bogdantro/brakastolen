from django.contrib import admin

from .models import Inquiry, InquiryNote, Plot, Project, ProjectImage


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


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0


class PlotInline(admin.TabularInline):
    model = Plot
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'is_published', 'is_featured', 'order', 'deleted_at')
    list_filter = ('category', 'status', 'is_published', 'is_featured')
    search_fields = ('title', 'location', 'description')
    inlines = [ProjectImageInline, PlotInline]


@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = ('number', 'project', 'status', 'area_m2', 'price', 'altitude')
    list_filter = ('status', 'project')
    search_fields = ('number', 'note')
