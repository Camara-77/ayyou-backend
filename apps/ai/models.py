from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Utilisateur


class AIChatQuota(models.Model):
    """
    Modèle de suivi des quotas de recherche intelligente de plats effectuées par le Chatbot IA.
    Impose une limite stricte de 7 recherches par fenêtre glissante de 5 heures.
    Associé à l'utilisateur connecté s'il est authentifié, ou à la session/IP s'il est invité.
    """
    MAX_QUOTA = 7
    WINDOW_HOURS = 5

    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_quotas'
    )
    ip_address = models.CharField(max_length=45, null=True, blank=True, db_index=True)
    session_key = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    search_count = models.IntegerField(default=0)
    window_start = models.DateTimeField(default=timezone.now)
    reset_at = models.DateTimeField(null=True, blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quota Recherche Chatbot IA"
        verbose_name_plural = "Quotas Recherches Chatbot IA"

    def save(self, *args, **kwargs):
        if not self.reset_at and self.window_start:
            self.reset_at = self.window_start + timedelta(hours=self.WINDOW_HOURS)
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_quota(cls, request) -> 'AIChatQuota':
        """
        Récupère ou crée l'enregistrement de quota pour la requête courante.
        Gère la réinitialisation automatique si la fenêtre de 5 heures a expiré.
        """
        now = timezone.now()
        user = request.user if (request and hasattr(request, 'user') and request.user.is_authenticated) else None
        
        ip_addr = None
        if request and hasattr(request, 'META'):
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded:
                ip_addr = x_forwarded.split(',')[0].strip()
            else:
                ip_addr = request.META.get('REMOTE_ADDR')

        session_key = None
        if request and hasattr(request, 'session') and hasattr(request.session, 'session_key'):
            session_key = request.session.session_key

        quota = None
        if user:
            quota = cls.objects.filter(utilisateur=user).first()
        elif ip_addr:
            quota = cls.objects.filter(ip_address=ip_addr).first()
        elif session_key:
            quota = cls.objects.filter(session_key=session_key).first()

        if not quota:
            reset_at = now + timedelta(hours=cls.WINDOW_HOURS)
            quota = cls.objects.create(
                utilisateur=user,
                ip_address=ip_addr,
                session_key=session_key,
                search_count=0,
                window_start=now,
                reset_at=reset_at
            )

        # Si l'utilisateur vient de se connecter avec une entrée initialement sans utilisateur
        if user and not quota.utilisateur:
            quota.utilisateur = user
            quota.save(update_fields=['utilisateur'])

        # Réinitialisation automatique si la fenêtre de 5h a expiré
        if quota.reset_at and now >= quota.reset_at:
            quota.search_count = 0
            quota.window_start = now
            quota.reset_at = now + timedelta(hours=cls.WINDOW_HOURS)
            quota.save(update_fields=['search_count', 'window_start', 'reset_at'])

        return quota

    def is_exceeded(self) -> bool:
        now = timezone.now()
        if self.reset_at and now >= self.reset_at:
            return False
        return self.search_count >= self.MAX_QUOTA

    def get_seconds_remaining(self) -> int:
        now = timezone.now()
        if not self.reset_at or now >= self.reset_at:
            return 0
        diff = (self.reset_at - now).total_seconds()
        return max(0, int(diff))

    def get_formatted_time_remaining(self) -> str:
        seconds = self.get_seconds_remaining()
        if seconds <= 0:
            return "maintenant"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
        return f"{minutes}min" if minutes > 0 else "moins d'une minute"


class AIConversation(models.Model):
    """
    Fil de conversation persistant avec l'assistant IA Alimentaire AYYOU.
    """
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_conversations'
    )
    session_key = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    titre = models.CharField(max_length=255, default="Nouvelle conversation")
    context_data = models.JSONField(default=dict, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conversation IA"
        verbose_name_plural = "Conversations IA"
        ordering = ['-date_modification']

    def __str__(self):
        user_label = self.utilisateur.get_full_name() if self.utilisateur else (self.session_key or "Anonyme")
        return f"Conversation #{self.id} ({user_label}) - {self.titre}"


class AIMessage(models.Model):
    """
    Message individuel au sein d'une conversation avec l'assistant IA AYYOU.
    """
    ROLE_USER = 'USER'
    ROLE_ASSISTANT = 'ASSISTANT'
    ROLE_SYSTEM = 'SYSTEM'

    CHOIX_ROLES = [
        (ROLE_USER, 'Utilisateur'),
        (ROLE_ASSISTANT, 'Assistant'),
        (ROLE_SYSTEM, 'Système'),
    ]

    TYPE_TEXT = 'TEXT'
    TYPE_IMAGE = 'IMAGE'
    TYPE_ACTION = 'ACTION'
    TYPE_PLANNING = 'PLANNING'

    CHOIX_TYPES = [
        (TYPE_TEXT, 'Texte'),
        (TYPE_IMAGE, 'Image'),
        (TYPE_ACTION, 'Action'),
        (TYPE_PLANNING, 'Planning'),
    ]

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=CHOIX_ROLES, default=ROLE_USER)
    type_message = models.CharField(max_length=20, choices=CHOIX_TYPES, default=TYPE_TEXT)
    content = models.TextField(blank=True, default='')
    user_text = models.TextField(blank=True, default='')
    image_url = models.CharField(max_length=500, null=True, blank=True)
    data_payload = models.JSONField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message IA"
        verbose_name_plural = "Messages IA"
        ordering = ['date_creation']

    def __str__(self):
        return f"Message #{self.id} [{self.role}] ({self.conversation_id})"

