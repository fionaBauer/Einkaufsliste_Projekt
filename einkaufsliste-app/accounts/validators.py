import re

from django.core.exceptions import ValidationError


class HasDigitValidator:
    def validate(self, password, user=None):
        if not re.search(r"\d", password):
            raise ValidationError(
                "Das Passwort muss mindestens eine Zahl enthalten.",
                code="password_no_digit",
            )

    def get_help_text(self):
        return "Das Passwort muss mindestens eine Zahl enthalten."


class HasSpecialCharValidator:
    SPECIAL = r'[!@#$%^&*()\-_=+\[\]{}|;:\'",.<>?/\\`~]'

    def validate(self, password, user=None):
        if not re.search(self.SPECIAL, password):
            raise ValidationError(
                "Das Passwort muss mindestens ein Sonderzeichen enthalten (z. B. !, @, #).",
                code="password_no_special",
            )

    def get_help_text(self):
        return "Das Passwort muss mindestens ein Sonderzeichen enthalten (z. B. !, @, #)."
