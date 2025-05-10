from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    content = forms.CharField(
        label='コメント',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control', 'rows': '3',
                'placeholder': 'コメントを入力（任意）'
            }
        ),
        required=False
    )

    class Meta:
        model = Comment
        fields = ['content']

