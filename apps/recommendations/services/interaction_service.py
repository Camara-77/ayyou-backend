import math
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.db.models import Q

from apps.telemetry.models import VideoEventLog
from apps.catalog.models import LikeProduit
from apps.orders.models import LigneCommande
from apps.recommendations.configuration import EngineConfig


class UserInteractionData:
    """
    Structure déterministe stockant les signaux d'interaction agrégés et pondérés par time decay.
    """
    def __init__(self):
        self.video_scores: Dict[int, float] = {}        # pub_id -> weighted score
        self.category_scores: Dict[int, float] = {}     # cat_id -> weighted score
        self.product_scores: Dict[int, float] = {}      # prod_id -> weighted score
        self.etab_scores: Dict[int, float] = {}         # etab_id -> weighted score
        self.total_interactions_count: int = 0


class InteractionService:
    """
    Service responsable de l'analyse brute des signaux utilisateur (VideoEventLog, LikeProduit, Commande)
    et de l'application de la décroissance temporelle déterministe (Time Decay).
    """

    @staticmethod
    def calculate_time_decay(created_at: datetime, ref_now: Optional[datetime] = None) -> float:
        """
        Calcule la décroissance temporelle déterministe :
        decay_factor = 0.5 ** (delta_days / DECAY_HALF_LIFE_DAYS)
        """
        now = ref_now or timezone.now()
        if not created_at:
            return 1.0
        delta = (now - created_at).total_seconds() / 86400.0
        if delta <= 0:
            return 1.0
        return math.pow(0.5, delta / EngineConfig.DECAY_HALF_LIFE_DAYS)

    @classmethod
    def get_event_weight(cls, event_type: str, watch_time: float = 0.0, duration: float = 0.0, progress: float = 0.0) -> float:
        """
        Détermine le poids déterministe d'un événement de télémétrie.
        """
        if event_type == VideoEventLog.EVENT_SKIP:
            return EngineConfig.WEIGHT_SKIP

        if event_type == VideoEventLog.EVENT_COMPLETED:
            return EngineConfig.WEIGHT_COMPLETED

        if event_type == VideoEventLog.EVENT_LIKE:
            return EngineConfig.WEIGHT_LIKE

        if event_type == VideoEventLog.EVENT_UNLIKE:
            return EngineConfig.WEIGHT_UNLIKE

        if event_type == VideoEventLog.EVENT_SHARE:
            return EngineConfig.WEIGHT_SHARE

        if event_type == VideoEventLog.EVENT_CART_ADD:
            return EngineConfig.WEIGHT_CART_ADD

        if event_type == VideoEventLog.EVENT_DISH_CLICK:
            return EngineConfig.WEIGHT_DISH_CLICK

        if event_type == VideoEventLog.EVENT_PLAY:
            return EngineConfig.WEIGHT_PLAY

        if event_type == VideoEventLog.EVENT_PAUSE:
            return EngineConfig.WEIGHT_PAUSE

        if event_type in (VideoEventLog.EVENT_WATCH, VideoEventLog.EVENT_IMPRESSION):
            ratio = 0.0
            if duration > 0:
                ratio = watch_time / duration
            elif progress > 0:
                ratio = progress / 100.0

            if ratio >= 0.7:
                return EngineConfig.WEIGHT_WATCH_HIGH
            elif ratio >= 0.3:
                return EngineConfig.WEIGHT_WATCH_MEDIUM
            elif ratio < 0.15 and watch_time < 3.0 and event_type == VideoEventLog.EVENT_WATCH:
                return EngineConfig.WEIGHT_SKIP
            return EngineConfig.WEIGHT_IMPRESSION

        return 0.0

    @classmethod
    def extract_user_interaction_data(
        cls,
        user=None,
        session_id: Optional[str] = None
    ) -> UserInteractionData:
        """
        Extrait et agrège toutes les interactions de l'utilisateur (authentifié ou session anonyme)
        en appliquant la décroissance temporelle.
        """
        data = UserInteractionData()
        now = timezone.now()

        event_filter = Q()
        if user and getattr(user, 'is_authenticated', False):
            event_filter |= Q(utilisateur=user)
        if session_id:
            event_filter |= Q(session_id=session_id)

        if not event_filter:
            return data

        logs = VideoEventLog.objects.filter(event_filter).select_related(
            'publication', 'publication__produit', 'publication__produit__categorie', 'publication__etablissement'
        )

        for log in logs:
            data.total_interactions_count += 1
            decay = cls.calculate_time_decay(log.created_at, ref_now=now)
            base_weight = cls.get_event_weight(
                event_type=log.event_type,
                watch_time=log.watch_time_seconds,
                duration=log.video_duration_seconds,
                progress=log.progress_percent
            )
            weighted_score = base_weight * decay

            pub = log.publication
            if pub:
                pub_id = pub.id
                data.video_scores[pub_id] = data.video_scores.get(pub_id, 0.0) + weighted_score

                etab_id = pub.etablissement_id
                if etab_id:
                    data.etab_scores[etab_id] = data.etab_scores.get(etab_id, 0.0) + weighted_score

                if pub.produit:
                    prod_id = pub.produit.id
                    data.product_scores[prod_id] = data.product_scores.get(prod_id, 0.0) + weighted_score
                    if pub.produit.categorie_id:
                        cat_id = pub.produit.categorie_id
                        data.category_scores[cat_id] = data.category_scores.get(cat_id, 0.0) + weighted_score

        # 2. Intègre les Likes directes de LikeProduit
        if user and getattr(user, 'is_authenticated', False):
            likes = LikeProduit.objects.filter(utilisateur=user).select_related(
                'produit', 'produit__categorie', 'publication', 'publication__etablissement'
            )
            for like in likes:
                data.total_interactions_count += 1
                decay = cls.calculate_time_decay(like.date_creation, ref_now=now)
                like_weight = EngineConfig.WEIGHT_LIKE * decay

                if like.publication:
                    p_id = like.publication.id
                    data.video_scores[p_id] = data.video_scores.get(p_id, 0.0) + like_weight
                    e_id = like.publication.etablissement_id
                    if e_id:
                        data.etab_scores[e_id] = data.etab_scores.get(e_id, 0.0) + like_weight

                if like.produit:
                    pr_id = like.produit.id
                    data.product_scores[pr_id] = data.product_scores.get(pr_id, 0.0) + like_weight
                    if like.produit.categorie_id:
                        c_id = like.produit.categorie_id
                        data.category_scores[c_id] = data.category_scores.get(c_id, 0.0) + like_weight

            # 3. Intègre les commandes réelles
            lignes = LigneCommande.objects.filter(sous_commande__commande__utilisateur=user).select_related(
                'produit', 'produit__categorie', 'sous_commande__etablissement'
            )
            for ligne in lignes:
                data.total_interactions_count += 1
                cmd_date = getattr(ligne.sous_commande.commande, 'date_creation', now)
                decay = cls.calculate_time_decay(cmd_date, ref_now=now)
                order_weight = EngineConfig.WEIGHT_ORDER * decay

                if ligne.produit:
                    pr_id = ligne.produit.id
                    data.product_scores[pr_id] = data.product_scores.get(pr_id, 0.0) + order_weight
                    if ligne.produit.categorie_id:
                        c_id = ligne.produit.categorie_id
                        data.category_scores[c_id] = data.category_scores.get(c_id, 0.0) + order_weight

                if ligne.sous_commande and ligne.sous_commande.etablissement_id:
                    e_id = ligne.sous_commande.etablissement_id
                    data.etab_scores[e_id] = data.etab_scores.get(e_id, 0.0) + order_weight

        return data
