from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.contrib.auth.password_validation import (
    UserAttributeSimilarityValidator,
    MinimumLengthValidator,
    CommonPasswordValidator,
    NumericPasswordValidator,
)

# 1. Similarity Validator (Checks if password is like the username)
class TheUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("The password can’t be too similar to the other personal information."),
                code='password_too_similar',
            )
    def get_help_text(self):
        return _("The password can’t be too similar to the other personal information.")

# 2. Minimum Length Validator (Checks character count)
class TheMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("The password must contain at least %(min_length)d characters."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )
    def get_help_text(self):
        return _("The password must contain at least %(min_length)d characters.") % {'min_length': self.min_length}

# 3. Common Password Validator (Checks lists like '123456')
class TheCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("The password can’t be a commonly used password."),
                code='password_too_common',
            )
    def get_help_text(self):
        return _("The password can’t be a commonly used password.")

# 4. Numeric Validator (Checks if it is just numbers)
class TheNumericPasswordValidator(NumericPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("The password can’t be entirely numeric."),
                code='password_entirely_numeric',
            )
    def get_help_text(self):
        return _("The password can’t be entirely numeric.")