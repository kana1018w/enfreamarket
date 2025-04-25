from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'products/index.html')

# 出品
def sell(request):
    return render(request, 'products/sell.html')

# 気になるリスト
def favorite_list(request): 
    return render(request, 'products/favorite_list.html')

# ご利用規約
def terms(request):
    return render(request, 'products/terms.html')