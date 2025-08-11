from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
# THIS LINE IS FIXED: I have removed the broken 'Profile' import.
from .models import FAQ, Article, Category, UserPreference, ReadingHistory, SummaryFeedback, ArticleLike, Bookmark, Comment, UserArticleMetrics
from .forms import UserPreferenceForm, SummaryFeedbackForm, CommentForm
from news.utils.scraper import fetch_articles, get_full_article_text, get_summary_from_gemini, generate_audio_summary
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
import os
import logging
import json
from datetime import datetime
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from .serializers import ArticleSerializer, UserPreferenceSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.cache import cache_page
from django.db.models import Case, When # Add these new imports
from django.http import HttpResponse
from wordcloud import WordCloud
import io
import base64

logger = logging.getLogger(__name__)

# This is the single, corrected view for your article list.
@cache_page(60 * 15)
def article_list(request):
    category_filter = request.GET.get("category", "All")
    query = request.GET.get("q", "")
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    min_likes_str = request.GET.get("min_likes")
    min_comments_str = request.GET.get("min_comments")
    sort_by = request.GET.get("sort_by", "-published_at")

    # THIS IS THE CORRECTED LINE
    articles = Article.objects.filter(approved=True)

    if category_filter and category_filter != "All":
        articles = articles.filter(category__name__iexact=category_filter)

    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(content__icontains=query))

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            articles = articles.filter(published_at__date__gte=start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            articles = articles.filter(published_at__date__lte=end_date)
        except ValueError:
            pass

    # Annotate once if any of the dependent filters are used
    if min_likes_str or min_comments_str or sort_by in ["most_popular_likes", "most_popular_comments"]:
        articles = articles.annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        )

    if min_likes_str:
        try:
            min_likes = int(min_likes_str)
            articles = articles.filter(like_count__gte=min_likes)
        except (ValueError, TypeError):
            pass
    if min_comments_str:
        try:
            min_comments = int(min_comments_str)
            articles = articles.filter(comment_count__gte=min_comments)
        except (ValueError, TypeError):
            pass

    # Apply Sorting
    if sort_by == "most_popular_likes":
        articles = articles.order_by('-like_count', '-published_at')
    elif sort_by == "most_popular_comments":
        articles = articles.order_by('-comment_count', '-published_at')
    else:
        articles = articles.order_by(sort_by)

    paginator = Paginator(articles, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.user.is_authenticated:
        page_article_ids = [article.id for article in page_obj]
        liked_articles_ids = set(ArticleLike.objects.filter(user=request.user, article__id__in=page_article_ids).values_list('article__id', flat=True))
        bookmarked_articles_ids = set(Bookmark.objects.filter(user=request.user, article__id__in=page_article_ids).values_list('article__id', flat=True))
        for article in page_obj:
            article.is_liked_by_user = article.id in liked_articles_ids
            article.is_bookmarked_by_user = article.id in bookmarked_articles_ids
    else:
        for article in page_obj:
            article.is_liked_by_user = False
            article.is_bookmarked_by_user = False

    categories = Category.objects.all()
    context = {
        "articles": page_obj,
        "categories": categories,
        "current_category": category_filter,
        "search_query": query,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "min_likes": min_likes_str,
        "min_comments": min_comments_str,
        "sort_by": sort_by,
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
    }
    return render(request, "news/article_list.html", context)


# --- YOUR UNTOUCHED API CODE ---
class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.filter(approved=True).order_by('-published_at')
    serializer_class = ArticleSerializer

class UserPreferenceViewSet(viewsets.ModelViewSet):
    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GenerateAudioAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        article = get_object_or_404(Article, pk=pk)
        if not article.summary:
            summary_text = get_summary_from_gemini(article.content)
            if summary_text:
                article.summary = summary_text
                article.save()
            else:
                return Response(
                    {'detail': 'Could not generate summary for article.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        if article.audio_file:
            return Response({'audio_url': article.audio_file.url}, status=status.HTTP_200_OK)
        audio_url = generate_audio_summary(article.summary, article.id)
        if audio_url:
            article.audio_file.name = audio_url.replace(settings.MEDIA_URL, '', 1)
            article.save()
            return Response({'audio_url': audio_url}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'detail': 'Failed to generate audio summary.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# --- END OF YOUR API CODE ---


def homepage(request):
    return render(request, "news/homepage.html")


@login_required
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if not article.approved and not request.user.is_staff:
        raise Http404("This article is pending approval.")

    feedback_useful = SummaryFeedback.objects.filter(article=article, useful=True).count()
    feedback_not_useful = SummaryFeedback.objects.filter(article=article, useful=False).count()
    feedback_total = feedback_useful + feedback_not_useful

    feedback_submitted = False
    comment_form = CommentForm()
    comments = Comment.objects.filter(article=article, approved=True)

    if request.method == "POST":
        if 'feedback_submit' in request.POST:
            form = SummaryFeedbackForm(request.POST)
            if form.is_valid():
                existing_feedback = SummaryFeedback.objects.filter(user=request.user, article=article).first()
                if existing_feedback:
                    existing_feedback.useful = form.cleaned_data['useful']
                    existing_feedback.save()
                    messages.info(request, "Your feedback has been updated.")
                else:
                    feedback = form.save(commit=False)
                    feedback.article = article
                    feedback.user = request.user
                    feedback.save()
                    messages.success(request, "Thank you for your feedback.")
                feedback_submitted = True
            else:
                messages.error(request, "There was an error with your feedback submission.")
        elif 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                new_comment = comment_form.save(commit=False)
                new_comment.article = article
                new_comment.user = request.user
                new_comment.save()
                messages.success(request, "Your comment has been submitted for review.")
                return redirect('news:detail', pk=article.pk)
            else:
                messages.error(request, "There was an error submitting your comment.")
    else:
        form = SummaryFeedbackForm()

    if request.user.is_authenticated:
        ReadingHistory.objects.get_or_create(user=request.user, article=article)
        user_feedback_exists = SummaryFeedback.objects.filter(user=request.user, article=article).exists()
        is_liked_by_user = ArticleLike.objects.filter(user=request.user, article=article).exists()
        is_bookmarked_by_user = Bookmark.objects.filter(user=request.user, article=article).exists()
    else:
        user_feedback_exists = False
        is_liked_by_user = False
        is_bookmarked_by_user = False

    return render(request, "news/article_detail.html", {
        "article": article,
        "form": form,
        "comment_form": comment_form,
        "comments": comments,
        "feedback_submitted": feedback_submitted,
        "feedback_useful": feedback_useful,
        "feedback_not_useful": feedback_not_useful,
        "feedback_total": feedback_total,
        "user_feedback_exists": user_feedback_exists,
        "is_liked_by_user": is_liked_by_user,
        "is_bookmarked_by_user": is_bookmarked_by_user,
    })


@login_required
@require_POST
def generate_summary_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if article.summary:
        return JsonResponse({'status': 'success', 'summary': article.summary})

    try:
        full_content = article.content
        if not full_content:
            # This utility function is already imported at the top of your file
            full_content = get_full_article_text(article.url)

        if not full_content:
            return JsonResponse({'status': 'error', 'message': 'Could not retrieve full article content to generate summary.'}, status=400)

        # The function name has been corrected from 'generate_summary' to the imported 'get_summary_from_gemini'
        # We assume your Gemini utility can handle the sentence_limit parameter.
        # If not, you might need to remove it from the call.
        summary_text = get_summary_from_gemini(full_content)

        if summary_text:
            article.summary = summary_text
            article.save()
            return JsonResponse({'status': 'success', 'summary': summary_text})
        else:
            return JsonResponse({'status': 'error', 'message': 'Summary generation failed.'}, status=500)

    except Exception as e:
        logger.error(f"Error generating summary for article {pk}: {e}")
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@login_required
def generate_audio_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not article.summary:
        return JsonResponse({'status': 'error', 'message': 'Summary not available. Please generate summary first.'}, status=400)
    if article.audio_file:
        return JsonResponse({'status': 'success', 'audio_url': article.audio_file.url})
    try:
        audio_url = generate_audio_summary(article.summary, article.id)
        if audio_url:
            article.audio_file.name = audio_url.replace(settings.MEDIA_URL, '', 1)
            article.save()
            return JsonResponse({'status': 'success', 'audio_url': audio_url})
        else:
            return JsonResponse({'status': 'error', 'message': 'Audio generation failed.'}, status=500)
    except Exception as e:
        logger.error(f"Error generating audio for article {pk}: {e}")
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@login_required
@require_POST
def toggle_article_like(request, pk):
    article = get_object_or_404(Article, pk=pk)
    user = request.user
    try:
        like, created = ArticleLike.objects.get_or_create(user=user, article=article)
        if not created:
            like.delete()
            is_liked = False
            message = "Article unliked."
        else:
            is_liked = True
            message = "Article liked!"
        total_likes = article.likes.count()
        return JsonResponse({'status': 'success', 'is_liked': is_liked, 'total_likes': total_likes, 'message': message})
    except Exception as e:
        logger.error(f"Error toggling like for article {pk} by user {user.username}: {e}")
        return JsonResponse({'status': 'error', 'message': 'An error occurred while processing your like.'}, status=500)


@login_required
@require_POST
def toggle_article_bookmark(request, pk):
    article = get_object_or_404(Article, pk=pk)
    user = request.user
    try:
        bookmark, created = Bookmark.objects.get_or_create(user=user, article=article)
        if not created:
            bookmark.delete()
            is_bookmarked = False
            message = "Bookmark removed."
        else:
            is_bookmarked = True
            message = "Article bookmarked!"
        return JsonResponse({'status': 'success', 'is_bookmarked': is_bookmarked, 'message': message})
    except Exception as e:
        logger.error(f"Error toggling bookmark for article {pk} by user {user.username}: {e}")
        return JsonResponse({'status': 'error', 'message': 'An error occurred while processing your bookmark.'}, status=500)


@login_required
@require_POST
def track_article_metrics(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)
    try:
        data = json.loads(request.body)
        article_id = data.get('article_id')
        time_on_page = data.get('time_on_page', 0)
        scroll_depth = data.get('scroll_depth', 0.0)
        article = get_object_or_404(Article, pk=article_id)
        metrics, created = UserArticleMetrics.objects.get_or_create(
            user=request.user,
            article=article,
            defaults={'time_on_page': time_on_page, 'scroll_depth': scroll_depth}
        )
        if not created:
            metrics.time_on_page = time_on_page
            if scroll_depth > metrics.scroll_depth:
                metrics.scroll_depth = scroll_depth
            metrics.save()
        return JsonResponse({'status': 'success', 'message': 'Metrics updated.'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Article.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Article not found.'}, status=404)
    except Exception as e:
        logger.error(f"Error tracking article metrics: {e}")
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)


@login_required
def bookmark_list(request):
    bookmarks = Bookmark.objects.filter(user=request.user).order_by('-created_at')
    article_ids = [b.article.id for b in bookmarks]
    liked_articles_ids = ArticleLike.objects.filter(user=request.user, article__id__in=article_ids).values_list('article__id', flat=True)
    for bookmark in bookmarks:
        bookmark.article.is_liked_by_user = bookmark.article.id in liked_articles_ids
        bookmark.article.is_bookmarked_by_user = True
    return render(request, "news/bookmarks.html", {"bookmarks": bookmarks})


@login_required
def preference_view(request):
    user_pref, created = UserPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserPreferenceForm(request.POST, instance=user_pref)
        if form.is_valid():
            form.save()
            return redirect("news:recommendations")
    else:
        form = UserPreferenceForm(instance=user_pref)
    return render(request, "news/user_preference.html", {"form": form})


@login_required
def personalized_recommendations(request):
    user_pref = UserPreference.objects.filter(user=request.user).first()
    articles = Article.objects.none()
    if user_pref and user_pref.preferred_categories.exists():
        articles = Article.objects.filter(
            category__in=user_pref.preferred_categories.all(),
            approved=True
        ).distinct()
    if request.user.is_authenticated:
        liked_articles_ids = ArticleLike.objects.filter(user=request.user, article__in=articles).values_list('article__id', flat=True)
        bookmarked_articles_ids = Bookmark.objects.filter(user=request.user, article__in=articles).values_list('article__id', flat=True)
        for article in articles:
            article.is_liked_by_user = article.id in liked_articles_ids
            article.is_bookmarked_by_user = article.id in bookmarked_articles_ids
    return render(request, "news/personalized_recommendations.html", {"articles": articles})


@login_required
def reading_history(request):
    history = ReadingHistory.objects.filter(user=request.user).order_by('-read_at')
    if request.user.is_authenticated:
        article_ids = [h.article.id for h in history]
        liked_articles_ids = ArticleLike.objects.filter(user=request.user, article__id__in=article_ids).values_list('article__id', flat=True)
        bookmarked_articles_ids = Bookmark.objects.filter(user=request.user, article__id__in=article_ids).values_list('article__id', flat=True)
        for h in history:
            h.article.is_liked_by_user = h.article.id in liked_articles_ids
            h.article.is_bookmarked_by_user = h.article.id in bookmarked_articles_ids
    return render(request, "news/reading_history.html", {"history": history})


@staff_member_required
def run_scraper_view(request):
    new_articles = fetch_articles()
    return render(request, "news/scraper_status.html", {"new_articles": new_articles})

# NEW FEATURE: View to generate and serve the word cloud image
def generate_word_cloud_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    text = article.content

    # Basic stopwords to remove common, uninteresting words
    stopwords = set(['the', 'a', 'in', 'to', 'of', 'and', 'for', 'is', 'on', 'it', 'that', 'was', 'with', 'as', 'at', 'by', 'he', 'she', 'from'])

    try:
        # Generate the word cloud object
        # You can customize colors, fonts, size, etc. here
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color=None, # Transparent background
            mode="RGBA",
            stopwords=stopwords,
            colormap='viridis', # A nice color scheme
            collocations=False # Avoids grouping words like "New York"
        ).generate(text)

        # Save the image to an in-memory buffer
        buffer = io.BytesIO()
        wordcloud.to_image().save(buffer, format='PNG')
        
        # Return the image as an HTTP response
        return HttpResponse(buffer.getvalue(), content_type='image/png')

    except Exception as e:
        logger.error(f"Error generating word cloud for article {pk}: {e}")
        # Return a simple 1x1 pixel transparent image on error
        return HttpResponse(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='), content_type='image/png')
    

@require_POST
def chatbot_response(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').lower().strip()

        if not user_message:
            return JsonResponse({'answer': "I'm sorry, I didn't get that. Could you ask again?"})

        # Split the user message into individual words
        user_keywords = user_message.split()
        
        # Find all FAQs that have at least one keyword matching the user's message
        # This uses a Q object to create a complex OR query
        keyword_query = Q()
        for keyword in user_keywords:
            keyword_query |= Q(keywords__icontains=keyword)

        possible_faqs = FAQ.objects.filter(keyword_query)

        if not possible_faqs:
            return JsonResponse({'answer': "I'm sorry, I don't have an answer for that yet. Please try asking in a different way."})

        # Score the possible FAQs to find the best match
        best_faq = None
        highest_score = 0
        for faq in possible_faqs:
            faq_keywords = [kw.strip().lower() for kw in faq.keywords.split(',')]
            score = 0
            for user_word in user_keywords:
                if user_word in faq_keywords:
                    score += 1
            if score > highest_score:
                highest_score = score
                best_faq = faq
        
        if best_faq:
            return JsonResponse({'answer': best_faq.answer})
        else:
            # Fallback if no keyword matches were strong enough
            return JsonResponse({'answer': "I'm sorry, I'm not sure how to help with that. Could you be more specific?"})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)