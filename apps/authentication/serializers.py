import re
import phonenumbers
from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur


class RegisterSerializer(serializers.Serializer):
    """
    Serializer d'inscription pour valider et normaliser les données du formulaire Client.
    """
    prenom = serializers.CharField(max_length=150, required=True, trim_whitespace=True)
    nom = serializers.CharField(max_length=150, required=True, trim_whitespace=True)
    email = serializers.EmailField(required=True)
    numero_telephone = serializers.CharField(max_length=30, required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirmation = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate_prenom(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError(_("Le prénom doit comporter au moins 2 caractères."))
        return value.strip()

    def validate_nom(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError(_("Le nom doit comporter au moins 2 caractères."))
        return value.strip()

    def validate_email(self, value):
        email_clean = value.strip().lower()
        if Utilisateur.objects.filter(email=email_clean).exists():
            raise serializers.ValidationError(_("Un compte existe déjà avec cette adresse email."))
        return email_clean

    def validate_numero_telephone(self, value):
        raw_phone = value.strip()
        default_region = getattr(settings, 'DEFAULT_COUNTRY_CODE', 'SN')
        try:
            parsed_phone = phonenumbers.parse(raw_phone, default_region)
            if not phonenumbers.is_valid_number(parsed_phone):
                raise serializers.ValidationError(_("Le numéro de téléphone est invalide."))

            formatted_phone = phonenumbers.format_number(
                parsed_phone,
                phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(_("Format de numéro de téléphone invalide."))

        if Utilisateur.objects.filter(numero_telephone=formatted_phone).exists():
            raise serializers.ValidationError(_("Un compte existe déjà avec ce numéro de téléphone."))

        return formatted_phone

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(_("Le mot de passe doit comporter au moins 8 caractères."))
        if not re.search(r'[a-zA-ZÀ-ÿ]', value):
            raise serializers.ValidationError(_("Le mot de passe doit contenir au moins une lettre."))
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError(_("Le mot de passe doit contenir au moins un chiffre."))
        if not re.search(r'[^a-zA-Z0-9]', value):
            raise serializers.ValidationError(_("Le mot de passe doit contenir au moins un symbole/caractère spécial."))
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirmation = attrs.get('password_confirmation')

        if password != password_confirmation:
            raise serializers.ValidationError({
                'password_confirmation': _("Les mots de passe ne correspondent pas.")
            })

        # Supprimer password_confirmation des données validées transmises au service
        attrs.pop('password_confirmation', None)
        return attrs


class VerifyOtpSerializer(serializers.Serializer):
    """
    Serializer de validation pour la soumission du code OTP SMS (/api/auth/verify-otp/).
    """
    numero_telephone = serializers.CharField(max_length=30, required=True)
    code = serializers.CharField(max_length=6, min_length=6, required=True, trim_whitespace=True)

    def validate_numero_telephone(self, value):
        raw_phone = value.strip()
        default_region = getattr(settings, 'DEFAULT_COUNTRY_CODE', 'SN')
        try:
            parsed_phone = phonenumbers.parse(raw_phone, default_region)
            if not phonenumbers.is_valid_number(parsed_phone):
                raise serializers.ValidationError(_("Le numéro de téléphone est invalide."))

            formatted_phone = phonenumbers.format_number(
                parsed_phone,
                phonenumbers.PhoneNumberFormat.E164
            )
            return formatted_phone
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(_("Format de numéro de téléphone invalide."))

    def validate_code(self, value):
        code_clean = value.strip()
        if len(code_clean) != 6 or not code_clean.isdigit():
            raise serializers.ValidationError(_("Le code OTP doit être composé d'exactement 6 chiffres."))
        return code_clean


class LoginSerializer(serializers.Serializer):
    """
    Serializer pour la connexion Client via Email ou Numéro de Téléphone (/api/auth/login/).
    """
    identifier = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate_identifier(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError(_("L'identifiant est obligatoire."))
        return val

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError(_("Le mot de passe est obligatoire."))
        return value

