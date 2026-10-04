import logging
from typing import List, Optional, Any
from datetime import datetime
from django.db.models import QuerySet
from django.utils import timezone

from apps.catalog.models import PublicationFeed, Etablissement
from apps.recommendations.configuration import EngineConfig
from apps.recommendations.services.interaction_service import InteractionService
from apps.recommendations.services.affinity_service import AffinityService
from apps.recommendations.services.scoring_service import ScoringService
from apps.recommendations.services.diversification_service import DiversificationService

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Orchestrateur principal du Moteur de Recommandation Comportemental Déterministe AYYOU.
    Assure le tri des publications avec gestion de la surcouche déterministe et repli (fallback)
    stricte en cas d'erreur.
    """

    @classmethod
    def rank_publications(
        cls,
        queryset: QuerySet,
        user: Optional[Any] = None,
        session_id: Optional[str] = None,
        ref_now: Optional[datetime] = None
    ) -> List[PublicationFeed]:
        """
        Ordonne une liste ou un QuerySet de PublicationFeed de manière déterministe.
        En cas d'erreur, bascule automatiquement sur le tri chronologique pur.
        """
        try:
            now = ref_now or timezone.now()

            # Charger les relations nécessaires si ce n'est pas déjà fait
            candidates = list(
                queryset.select_related(
                    'etablissement', 'produit', 'produit__categorie'
                )
            )

            if not candidates:
                return []

            # Limite le nombre de candidats à évaluer pour préserver les performances SQL
            to_score = candidates[:EngineConfig.MAX_CANDIDATES_TO_SCORE]
            overflow = candidates[EngineConfig.MAX_CANDIDATES_TO_SCORE:]

            # 1. Extraction des interactions et signaux utilisateur
            user_data = InteractionService.extract_user_interaction_data(user=user, session_id=session_id)

            # 2. Calcul des affinités (normalisées)
            cat_affinities = AffinityService.get_category_affinities(user_data)
            prod_affinities = AffinityService.get_product_affinities(user_data)
            etab_affinities = AffinityService.get_establishment_affinities(user_data)

            # 3. Évaluation (Scoring) de chaque candidat
            scored_candidates = []
            for pub in to_score:
                score, breakdown = ScoringService.calculate_publication_score(
                    pub=pub,
                    user_data=user_data,
                    cat_affinities=cat_affinities,
                    prod_affinities=prod_affinities,
                    etab_affinities=etab_affinities,
                    ref_now=now
                )
                scored_candidates.append((pub, score, breakdown))

            # 4. Tri par score décroissant (avec second critère déterministe : date de publication)
            scored_candidates.sort(
                key=lambda x: (x[1], x[0].date_publication or timezone.now()),
                reverse=True
            )

            # 5. Diversification déterministe & créneaux d'exploration
            diversified = DiversificationService.apply_diversification_and_exploration(scored_candidates)

            # 6. Extraction des publications réordonnées
            ranked_pubs = [item[0] for item in diversified]

            # Si le nombre initial de candidats dépassait le plafond de scoring, on rajoute le reliquat à la fin
            if overflow:
                ranked_pubs.extend(overflow)

            return ranked_pubs

        except Exception as e:
            logger.error(f"[RecommendationService] Exception durant le classement déterministe : {str(e)}. Repli sur feed chronologique.", exc_info=True)
            # Repli de sécurité garanti (Fallback)
            return list(queryset)

    @classmethod
    def get_recommended_feed(
        cls,
        user: Optional[Any] = None,
        session_id: Optional[str] = None,
        etablissement_id: Optional[int] = None,
        ref_now: Optional[datetime] = None
    ) -> List[PublicationFeed]:
        """
        Génère directement la liste des recommandations pour le Feed vidéo public.
        """
        now = ref_now or timezone.now()

        queryset = PublicationFeed.objects.select_related(
            'etablissement', 'produit', 'produit__categorie'
        ).filter(
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO
        )

        if user and not getattr(user, 'is_superuser', False):
            queryset = queryset.filter(
                etablissement__statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                etablissement__date_expiration_abonnement__gt=now
            )
        elif not user:
            queryset = queryset.filter(
                etablissement__statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                etablissement__date_expiration_abonnement__gt=now
            )

        if etablissement_id:
            queryset = queryset.filter(etablissement_id=etablissement_id)

        queryset = queryset.order_by('-date_publication')

        return cls.rank_publications(
            queryset=queryset,
            user=user,
            session_id=session_id,
            ref_now=now
        )
