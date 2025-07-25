from django.contrib import admin
from django.db.models import Count
from .models import Article, Category, UserPreference, ReadingHistory
from django.contrib.admin import RelatedOnlyFieldListFilter

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'author', 'approved_status')
    list_filter = (
    'source',
    ('category', RelatedOnlyFieldListFilter),  # ✅ Fixed this line
    'approved',
    'published_at',
) # categories is ManyToMany, so it's okay
    search_fields = ('title', 'content', 'author')
    readonly_fields = ('published_at',)  # removed 'link' since it's not in model
    date_hierarchy = 'published_at'
    change_list_template = "admin/news/article/change_list.html"


    # Bulk Actions
    actions = ['make_approved', 'make_pending']

    def make_approved(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(
            request, f"{updated} articles marked as approved.", level='success'
        )
    make_approved.short_description = "Mark selected articles as approved"

    def make_pending(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(
            request, f"{updated} articles marked as pending.", level='warning'
        )
    make_pending.short_description = "Mark selected articles as pending"

    # Article stats
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # Only add stats if the response has a context (i.e., not a redirect)
        if hasattr(response, "context_data"):
            try:
                qs = response.context_data['cl'].queryset
            except (AttributeError, KeyError):
                qs = Article.objects.all()

            approved_count = qs.filter(approved=True).count()
            pending_count = qs.filter(approved=False).count()
            total_count = qs.count()

            response.context_data['article_stats'] = {
                'total': total_count,
                'approved': approved_count,
                'pending': pending_count,
            }

        return response


admin.site.register(Article, ArticleAdmin)
admin.site.register(Category)
admin.site.register(UserPreference)
admin.site.register(ReadingHistory)
