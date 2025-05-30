from django.contrib.auth.password_validation import MinimumLengthValidator
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

class CustomMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("このパスワードは短すぎます。最低%(min_length)d文字以上必要です。"),
                code='password_too_short',
                params={'min_length': self.min_length},
            ) 