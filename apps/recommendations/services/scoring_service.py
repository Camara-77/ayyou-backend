from typing import Dict, Tuple, Any, Optional
from datetime import datetime
from apps.catalog.models import PublicationFeed
from apps.recommendations.configuration import EngineConfig
from apps.recommendations.services.interaction_service import UserInteractionData
from apps.recommendations.services.freshness_service import FreshnessService
from apps.recommendations.services.popularity_service import PopularityService


class ScoringService:
    """
    Service responsable de l'évaluation et de l'attribution de scores déterministes aux publications.
    Génère également un rapport d'explicabilité détaillé pour chaque décision.
    """

    @classmethod
    def calculate_publication_score(
        cls,
        pub: PublicationFeed,
        user_data: UserInteractionData,
        cat_affinities: Dict[int, float],
        prod_affinities: Dict[int, float],
        etab_affinities: Dict[int, float],
        ref_now: Optional[datetime] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score global = cat_score + prod_score + etab_score + behavior_score + freshness_score + popularity_score
        Retourne un tuple (total_score, breakdown_dict).
        """
        pub_id = pub.id
        etab_id = pub.etablissement_id
        prod = pub.produit
        prod_id = prod.id if prod else None
        cat_id = prod.categorie_id if (prod and prod.categorie_id) else None

        # 1. Affinité Catégorie
        cat_affinity = cat_affinities.get(cat_id, 0.0) if cat_id else 0.0
        cat_score = cat_affinity * EngineConfig.WEIGHT_CATEGORY_AFFINITY

        # 2. Affinité Produit
        prod_affinity = prod_affinities.get(prod_id, 0.0) if prod_id else 0.0
        prod_score = prod_affinity * EngineConfig.WEIGHT_PRODUCT_AFFINITY

        # 3. Affinité Établissement
        etab_affinity = etab_affinities.get(etab_id, 0.0) if etab_id else 0.0
        etab_score = etab_affinity * EngineConfig.WEIGHT_ESTABLISHMENT_AFFINITY

        # 4. Historique Direct sur cette vidéo
        behavior_hist_score = user_data.video_scores.get(pub_id, 0.0) * EngineConfig.WEIGHT_BEHAVIOR_HISTORICAL

        # 5. Bonus de Fraîcheur
        pub_date = getattr(pub, 'date_publication', None)
        freshness_score = FreshnessService.calculate_freshness_score(pub_date, ref_now=ref_now)

        # 6. Score de Popularité
        likes_count = getattr(pub, 'nombre_likes', 0) or 0
        shares_count = getattr(pub, 'nombre_partages', 0) or 0
        popularity_score = PopularityService.calculate_popularity_score(likes_count, shares_count)

        total_score = (
            cat_score
            + prod_score
            + etab_score
            + behavior_hist_score
            + freshness_score
            + popularity_score
        )

        breakdown = {
            'publication_id': pub_id,
            'total_score': round(total_score, 4),
            'details': {
                'cat_score': round(cat_score, 4),
                'prod_score': round(prod_score, 4),
                'etab_score': round(etab_score, 4),
                'behavior_hist_score': round(behavior_hist_score, 4),
                'freshness_score': round(freshness_score, 4),
                'popularity_score': round(popularity_score, 4),
            }
        }

        return total_score, breakdown
