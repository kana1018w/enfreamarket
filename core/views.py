from django.shortcuts import render

# ポートフォリオ
def portfolio_view(request):
    return render(request, 'portfolio.html')

# ご利用規約
def terms(request):
    return render(request, 'core/terms.html')
