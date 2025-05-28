from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    content = forms.CharField(
        label='コメント',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control', 'rows': '3',
                'placeholder': 'コメントを入力してください'
            }
        ),
        required=True,
        error_messages={'required': '未入力の場合、コメントは送信できません。'}
    )

    class Meta:
        model = Comment
        fields = ['content']

