from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from news.models import Article, SummaryFeedback

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})


def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)

    # Feedback count
    feedback_total = SummaryFeedback.objects.filter(article=article).count()
    feedback_useful = SummaryFeedback.objects.filter(article=article, useful=True).count()

    context = {
        'article': article,
        'feedback_total': feedback_total,
        'feedback_useful': feedback_useful,
    }
    return render(request, 'news/article_detail.html', context)
