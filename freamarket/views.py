from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'freamarket/index.html')

# ご利用規約
def terms(request):
    return render(request, 'freamarket/terms.html')