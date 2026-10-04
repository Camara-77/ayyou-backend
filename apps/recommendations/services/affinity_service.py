from typing import Dict
from apps.recommendations.services.interaction_service import UserInteractionData


class AffinityService:
    """
    Calcule et normalise les affinités (catégorie, produit, établissement)
    à partir des signaux d'interaction bruts agrégés et pondérés.
    """

    @staticmethod
    def _normalize_dict(scores: Dict[int, float]) -> Dict[int, float]:
        """
        Normalise un dictionnaire de scores pour que la valeur maximale positive vale 1.0,
        tout en préservant le ratio d'intensité de chaque préférence ou aversion.
        """
        if not scores:
            return {}
        max_val = max(scores.values())
        min_val = min(scores.values())

        if max_val <= 0:
            if min_val == 0:
                return {k: 0.0 for k in scores}
            return {k: v / abs(min_val) for k, v in scores.items()}

        return {k: (v / max_val if v > 0 else max(v / max_val, -1.0)) for k, v in scores.items()}

    @classmethod
    def get_category_affinities(cls, data: UserInteractionData) -> Dict[int, float]:
        return cls._normalize_dict(data.category_scores)

    @classmethod
    def get_product_affinities(cls, data: UserInteractionData) -> Dict[int, float]:
        return cls._normalize_dict(data.product_scores)

    @classmethod
    def get_establishment_affinities(cls, data: UserInteractionData) -> Dict[int, float]:
        return cls._normalize_dict(data.etab_scores)
