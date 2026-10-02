from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur
from apps.catalog.models import PublicationFeed


class VideoEventLog(models.Model):
    """
    Modèle de journalisation de la télémétrie des interactions vidéo.
    Permet de suivre les événements d'impression, de visionnage, de complétion,
    de skips et d'interactions sociales/commerciales pour alimenter le dataset ML.
    """

    EVENT_IMPRESSION = 'IMPRESSION'
    EVENT_PLAY = 'PLAY'
    EVENT_PAUSE = 'PAUSE'
    EVENT_WATCH = 'WATCH'
    EVENT_COMPLETED = 'COMPLETED'
    EVENT_SKIP = 'SKIP'
    EVENT_LIKE = 'LIKE'
    EVENT_UNLIKE = 'UNLIKE'
    EVENT_SHARE = 'SHARE'
    EVENT_CART_ADD = 'CART_ADD'
    EVENT_DISH_CLICK = 'DISH_CLICK'

    CHOIX_EVENT_TYPES = [
        (EVENT_IMPRESSION, _('Impression (Affichée à l\'écran)')),
        (EVENT_PLAY, _('Début de lecture')),
        (EVENT_PAUSE, _('Mise en pause')),
        (EVENT_WATCH, _('Visionnage en cours (Heartbeat)')),
        (EVENT_COMPLETED, _('Visionnage complet (100%)')),
        (EVENT_SKIP, _('Zappe rapide (< 3s)')),
        (EVENT_LIKE, _('Like activé')),
        (EVENT_UNLIKE, _('Like retiré')),
        (EVENT_SHARE, _('Partage vidéo')),
        (EVENT_CART_ADD, _('Ajout au panier depuis vidéo')),
        (EVENT_DISH_CLICK, _('Clic fiche plat')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='video_events',
        verbose_name=_('utilisateur')
    )
    publication = models.ForeignKey(
        PublicationFeed,
        on_delete=models.CASCADE,
        related_name='video_events',
        verbose_name=_('publication feed')
    )
    session_id = models.CharField(_('ID de session feed'), max_length=100, db_index=True)
    event_type = models.CharField(
        _('type d\'événement'),
        max_length=50,
        choices=CHOIX_EVENT_TYPES,
        db_index=True
    )
    watch_time_seconds = models.FloatField(_('temps de visionnage (secondes)'), default=0.0)
    video_duration_seconds = models.FloatField(_('durée totale vidéo (secondes)'), default=0.0)
    progress_percent = models.FloatField(_('pourcentage de progression (0-100)'), default=0.0)
    feed_position = models.IntegerField(_('position dans le feed'), default=0)
    metadata = models.JSONField(_('métadonnées complémentaires'), default=dict, blank=True)
    created_at = models.DateTimeField(_('horodatage'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Journal Télémétrie Vidéo')
        verbose_name_plural = _('Journaux Télémétrie Vidéo')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['publication', 'event_type']),
            models.Index(fields=['utilisateur', 'created_at']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        user_str = self.utilisateur.email if self.utilisateur else 'Anonyme'
        return f"[{self.event_type}] Video #{self.publication_id} - {user_str} ({self.watch_time_seconds:.1f}s)"


class RecommendationShadowLog(models.Model):
    """
    Modèle de journalisation des prédictions effectuées en arrière-plan (Shadow Mode)
    par le modèle de recommandation LightGBM V3 sans modifier l'affichage réel.
    """

    id = models.BigAutoField(primary_key=True)
    session_id = models.CharField(_('ID de session'), max_length=100, db_index=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shadow_recommendations',
        verbose_name=_('utilisateur')
    )
    publication = models.ForeignKey(
        PublicationFeed,
        on_delete=models.CASCADE,
        related_name='shadow_recommendations',
        verbose_name=_('publication feed')
    )
    model_version = models.CharField(_('version du modèle'), max_length=50, default='v3', db_index=True)
    predicted_score = models.FloatField(_('score prédit par le modèle'), default=0.0)
    predicted_rank = models.IntegerField(_('rang prédit par le modèle'), default=0)
    feed_position = models.IntegerField(_('position réelle dans le feed'), default=0)
    request_id = models.CharField(_('ID unique de requête'), max_length=100, null=True, blank=True)
    candidate_count = models.IntegerField(_('nombre de candidats dans le batch'), default=0)
    execution_time_ms = models.FloatField(_('temps d\'exécution scoring (ms)'), default=0.0)
    created_at = models.DateTimeField(_('horodatage du scoring'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Journal Shadow Recommandation')
        verbose_name_plural = _('Journaux Shadow Recommandation')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['model_version', 'created_at']),
            models.Index(fields=['publication', 'model_version']),
        ]

    def __str__(self):
        user_str = self.utilisateur.email if self.utilisateur else 'Anonyme'
        return f"[Shadow {self.model_version}] Pub #{self.publication_id} -> Rank #{self.predicted_rank} (Score: {self.predicted_score:.4f}) - {user_str}"


class RecommendationExperimentLog(models.Model):
    """
    Modèle de journalisation de l'expérimentation contrôlée (A/B testing).
    Permet de suivre séparément les prédictions et la qualité du Feed pour le Groupe CONTROL
    (Feed chronologique) et le Groupe EXPERIMENT (Feed classé par LightGBM V3).
    """

    GROUP_CONTROL = 'control'
    GROUP_EXPERIMENT = 'experiment'

    CHOIX_GROUPS = [
        (GROUP_CONTROL, _('Groupe Contrôle (Chronologique)')),
        (GROUP_EXPERIMENT, _('Groupe Expérimental (Scoré V3)')),
    ]

    id = models.BigAutoField(primary_key=True)
    session_id = models.CharField(_('ID de session'), max_length=100, db_index=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='experiment_recommendations',
        verbose_name=_('utilisateur')
    )
    publication = models.ForeignKey(
        PublicationFeed,
        on_delete=models.CASCADE,
        related_name='experiment_recommendations',
        verbose_name=_('publication feed')
    )
    experiment_group = models.CharField(
        _('groupe d\'expérimentation'),
        max_length=20,
        choices=CHOIX_GROUPS,
        db_index=True
    )
    recommendation_mode = models.CharField(_('mode de recommandation active'), max_length=50, db_index=True)
    model_version = models.CharField(_('version du modèle'), max_length=50, null=True, blank=True)
    predicted_score = models.FloatField(_('score prédit par le modèle'), null=True, blank=True)
    predicted_rank = models.IntegerField(_('rang prédit par le modèle'), null=True, blank=True)
    feed_position = models.IntegerField(_('position finale affichée dans le feed'), default=0)
    fallback_used = models.BooleanField(_('fallback chronologique appliqué'), default=False, db_index=True)
    scoring_time_ms = models.FloatField(_('temps d\'exécution du scoring (ms)'), default=0.0)
    request_id = models.CharField(_('ID unique de requête'), max_length=100, null=True, blank=True)
    candidate_count = models.IntegerField(_('nombre de candidats dans le batch'), default=0)
    created_at = models.DateTimeField(_('horodatage de l\'événement'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Journal Expérimentation Recommandation')
        verbose_name_plural = _('Journaux Expérimentation Recommandation')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['experiment_group', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['fallback_used', 'created_at']),
        ]

    def __str__(self):
        user_str = self.utilisateur.email if self.utilisateur else 'Anonyme'
        return f"[{self.experiment_group.upper()}] Pub #{self.publication_id} at Pos #{self.feed_position} - {user_str} (Fallback: {self.fallback_used})"
