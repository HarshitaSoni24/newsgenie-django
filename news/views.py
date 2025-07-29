from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q 
from .models import Article, Category, UserPreference, ReadingHistory
from .forms import UserPreferenceForm, SummaryFeedbackForm
from news.utils.scraper import fetch_articles, generate_audio_summary  # ✅ make sure this import exists
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
import os


def article_list(request):
    category = request.GET.get("category", "All")
    query = request.GET.get("q", "")

    articles = Article.objects.filter(approved=True).order_by('-published_at')

    if category and category != "All":
        articles = articles.filter(category__name__iexact=category)
    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(content__icontains=query))

    paginator = Paginator(articles, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    context = {
        "articles": page_obj,
        "categories": categories,
        "current_category": category,
        "search_query": query,
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
    }
    return render(request, "news/article_list.html", context)


@login_required
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if not article.approved and not request.user.is_staff:
        raise Http404("This article is pending approval.")

    # ✅ Fallback: Generate audio if not already present
    if not article.audio_file and article.summary:
        audio_url = generate_audio_summary(article.summary, article.id)
        if audio_url:
            article.audio_file.name = audio_url.replace('/media/', '')
            article.save()

    feedback_submitted = False
    if request.method == "POST":
        form = SummaryFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.article = article
            feedback.user = request.user
            feedback.save()
            feedback_submitted = True
    else:
        form = SummaryFeedbackForm()

    if request.user.is_authenticated:
        ReadingHistory.objects.filter(user=request.user, article=article).first() or ReadingHistory.objects.create(user=request.user, article=article)

    return render(request, "news/article_detail.html", {
        "article": article,
        "form": form,
        "feedback_submitted": feedback_submitted,
    })


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
    return render(request, "news/personalized_recommendations.html", {"articles": articles})


@login_required
def reading_history(request):
    history = ReadingHistory.objects.filter(user=request.user).order_by('-read_at')
    return render(request, "news/reading_history.html", {"history": history})


@staff_member_required
def run_scraper_view(request):
    new_articles = fetch_articles()
    return render(request, "news/scraper_status.html", {"new_articles": new_articles})