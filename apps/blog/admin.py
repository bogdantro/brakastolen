from django.contrib import admin

from .models import Blog


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'excerpt', 'text')
    readonly_fields = ('slug', 'created_at', 'updated_at')
