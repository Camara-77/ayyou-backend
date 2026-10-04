from apps.recommendations.configuration import EngineConfig


class PopularityService:
    """
    Calcule le score de popularité globale d'une publication vidéo
    basé sur ses statistiques cumulatives (likes, partages).
    """

    @classmethod
    def calculate_popularity_score(
        cls,
        likes_count: int = 0,
        shares_count: int = 0
    ) -> float:
        """
        Score = min( (likes * POPULARITY_LIKE_WEIGHT) + (shares * POPULARITY_SHARE_WEIGHT), MAX_POPULARITY_SCORE )
        """
        raw_score = (likes_count * EngineConfig.POPULARITY_LIKE_WEIGHT) + (shares_count * EngineConfig.POPULARITY_SHARE_WEIGHT)
        return min(raw_score, EngineConfig.MAX_POPULARITY_SCORE)
