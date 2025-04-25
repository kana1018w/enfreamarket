from django.shortcuts import render

# ご利用規約
def terms(request):
    return render(request, 'core/terms.html')
