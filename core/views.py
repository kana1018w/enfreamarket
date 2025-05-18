from django.shortcuts import render

# ポートフォリオ
def portfolio_view(request):
    return render(request, 'portfolio.html')

# アプリ概要
def about(request):
    return render(request, 'core/about.html')

# ご利用規約
def terms(request):
    return render(request, 'core/terms.html')
