from django.contrib import admin
from django.db.models import Count, Sum, Max, Avg, F, Q # Import Avg and Q
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import RelatedOnlyFieldListFilter 
from .models import FAQ, Article, Category, UserPreference, ReadingHistory, SummaryFeedback, ArticleLike, Bookmark, Comment, UserArticleMetrics

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'published_at', 'author', 'approved_status', 'total_likes', 'total_comments')
    list_filter = (
    'source',
    ('category', RelatedOnlyFieldListFilter),
    'approved',
    'is_spotlighted',
    'published_at',
)
    search_fields = ('title', 'content', 'author')
    readonly_fields = ('published_at',)
    date_hierarchy = 'published_at'
    change_list_template = "admin/news/article/change_list.html"


    # Bulk Actions
    actions = ['make_approved', 'make_pending', 'set_as_spotlight']

    def set_as_spotlight(self, request, queryset):
        # Un-spotlight all other articles first
        Article.objects.update(is_spotlighted=False)
        # Spotlight the selected one (if only one is selected)
        if queryset.count() == 1:
            article = queryset.first()
            article.is_spotlighted = True
            article.save()
            self.message_user(request, f"'{article.title}' is now the Article of the Week.", level='success')
        else:
            self.message_user(request, "Please select only one article to set as the spotlight.", level='warning')
    set_as_spotlight.short_description = "Set as Article of the Week"

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

    # Helper function to format seconds into minutes and seconds
    def _format_seconds_to_minutes_seconds(self, seconds):
        if seconds is None:
            return "N/A"
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        if minutes > 0:
            return f"{minutes} min {remaining_seconds} sec"
        return f"{remaining_seconds} sec"

    # Comprehensive Dashboard Stats (added to changelist_view context)
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        if hasattr(response, "context_data"):
            # Existing Article Stats
            try:
                qs = response.context_data['cl'].queryset
            except (AttributeError, KeyError):
                qs = Article.objects.all() # Fallback for edge cases

            approved_count = qs.filter(approved=True).count()
            pending_count = qs.filter(approved=False).count()
            total_count = qs.count()

            response.context_data['article_stats'] = {
                'total': total_count,
                'approved': approved_count,
                'pending': pending_count,
            }

            # NEW: Global Dashboard Metrics
            # Top Liked Articles
            top_liked_articles = Article.objects.annotate(like_count=Count('likes')).order_by('-like_count')[:5]
            response.context_data['top_liked_articles'] = top_liked_articles

            # Top Commented Articles
            top_commented_articles = Article.objects.annotate(comment_count=Count('comments')).order_by('-comment_count')[:5]
            response.context_data['top_commented_articles'] = top_commented_articles

            # Top Useful Summaries (based on feedback)
            top_useful_summaries = Article.objects.annotate(useful_count=Count('summaryfeedback', filter=Q(summaryfeedback__useful=True))).order_by('-useful_count')[:5]
            response.context_data['top_useful_summaries'] = top_useful_summaries

            # Top Readers (by Time on Page) - MODIFIED to format time in Python
            top_readers_time_raw = UserArticleMetrics.objects.values('user__username').annotate(total_time=Sum('time_on_page')).order_by('-total_time')[:5]
            top_readers_time_formatted = []
            for reader in top_readers_time_raw:
                formatted_time = self._format_seconds_to_minutes_seconds(reader['total_time'])
                top_readers_time_formatted.append({'username': reader['user__username'], 'formatted_time': formatted_time})
            response.context_data['top_readers_time'] = top_readers_time_formatted


            # Top Readers (by Scroll Depth) - MODIFIED to calculate percentage in Python
            top_readers_scroll_raw = UserArticleMetrics.objects.values('user__username').annotate(avg_scroll=Avg('scroll_depth')).order_by('-avg_scroll')[:5]
            top_readers_scroll_formatted = []
            for reader in top_readers_scroll_raw:
                percentage = reader['avg_scroll'] * 100 if reader['avg_scroll'] is not None else 0.0
                top_readers_scroll_formatted.append({'username': reader['user__username'], 'avg_scroll_percentage': f"{percentage:.0f}%"}) # Format as integer percentage
            response.context_data['top_readers_scroll'] = top_readers_scroll_formatted


            # Recent unapproved comments (for quick moderation)
            recent_unapproved_comments = Comment.objects.filter(approved=False).order_by('-created_at')[:5]
            response.context_data['recent_unapproved_comments'] = recent_unapproved_comments

        return response

class SummaryFeedbackAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'useful', 'submitted_at')
    list_filter = ('useful', 'submitted_at')
    search_fields = ('article__title', 'user__username')
    readonly_fields = ('submitted_at',)

class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at')
    list_filter = ('created_at', 'article__title')
    search_fields = ('article__title', 'user__username')
    readonly_fields = ('created_at',)

class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at')
    list_filter = ('created_at', 'article__title')
    search_fields = ('article__title', 'user__username')
    readonly_fields = ('created_at',)

class CommentAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'content', 'created_at', 'approved')
    list_filter = ('approved', 'created_at', 'article__title')
    search_fields = ('article__title', 'user__username', 'content')
    actions = ['approve_comments', 'disapprove_comments']

    def approve_comments(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} comments approved.", level='success')
    approve_comments.short_description = "Approve selected comments"

    def disapprove_comments(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} comments disapproved.", level='warning')
    disapprove_comments.short_description = "Disapprove selected comments"

class UserArticleMetricsAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'time_on_page', 'scroll_depth', 'last_tracked_at')
    list_filter = ('last_tracked_at',)
    search_fields = ('user__username', 'article__title')
    readonly_fields = ('last_tracked_at',)

# NEW: Register the FAQ model with the admin site
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('keywords', 'answer', 'created_at')
    search_fields = ('keywords', 'answer')

admin.site.register(Article, ArticleAdmin)
admin.site.register(Category)
admin.site.register(UserPreference)
admin.site.register(ReadingHistory)
admin.site.register(SummaryFeedback, SummaryFeedbackAdmin)
admin.site.register(ArticleLike, ArticleLikeAdmin)
admin.site.register(Bookmark, BookmarkAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(UserArticleMetrics, UserArticleMetricsAdmin)