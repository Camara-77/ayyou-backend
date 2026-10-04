import math
from datetime import datetime
from typing import Optional
from django.utils import timezone
from apps.recommendations.configuration import EngineConfig


class FreshnessService:
    """
    Calcule le bonus déterministe de fraîcheur d'une publication vidéo
    en fonction de sa récence.
    """

    @classmethod
    def calculate_freshness_score(
        cls,
        pub_date: datetime,
        ref_now: Optional[datetime] = None
    ) -> float:
        """
        Calcul du bonus de fraîcheur :
        bonus = MAX_FRESHNESS_BONUS * (0.5 ** (delta_days / FRESHNESS_HALF_LIFE_DAYS))
        """
        if not pub_date:
            return 0.0

        now = ref_now or timezone.now()
        delta_days = (now - pub_date).total_seconds() / 86400.0

        if delta_days < 0:
            delta_days = 0.0

        decay_factor = math.pow(0.5, delta_days / EngineConfig.FRESHNESS_HALF_LIFE_DAYS)
        return EngineConfig.MAX_FRESHNESS_BONUS * decay_factor
