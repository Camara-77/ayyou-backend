from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RecommendationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recommendations'
    verbose_name = _('Moteur de Recommandation Comportemental Déterministe')
