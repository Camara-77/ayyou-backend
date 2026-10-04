from typing import List, Tuple, Dict, Any
from apps.catalog.models import PublicationFeed
from apps.recommendations.configuration import EngineConfig


class DiversificationService:
    """
    Service d'application déterministe des règles de diversification et d'exploration.
    Évite la répétition excessive des mêmes établissements ou catégories et garantit
    l'insertion de contenus de découverte.
    """

    @classmethod
    def apply_diversification_and_exploration(
        cls,
        scored_candidates: List[Tuple[PublicationFeed, float, Dict[str, Any]]]
    ) -> List[Tuple[PublicationFeed, float, Dict[str, Any]]]:
        """
        Reclasse les candidats en appliquant des pénalités déterministes sur les répétitions consécutives
        et en insérant des vidéos d'exploration à intervalles réguliers.
        """
        if not scored_candidates:
            return []

        remaining = list(scored_candidates)
        final_feed: List[Tuple[PublicationFeed, float, Dict[str, Any]]] = []
        recent_etabs: List[int] = []
        recent_cats: List[int] = []

        while remaining:
            is_exploration_slot = (
                len(final_feed) > 0 and
                (len(final_feed) + 1) % EngineConfig.EXPLORATION_INTERVAL == 0
            )

            chosen_idx = -1

            if is_exploration_slot and len(remaining) > 3:
                # Créneau d'exploration : privilégie une vidéo d'un établissement ou d'une catégorie non vue récemment
                seen_etabs = set(recent_etabs)
                seen_cats = set(recent_cats)

                for idx, (pub, score, bd) in enumerate(remaining):
                    e_id = pub.etablissement_id
                    c_id = pub.produit.categorie_id if (pub.produit and pub.produit.categorie_id) else None

                    if e_id not in seen_etabs and (c_id is None or c_id not in seen_cats):
                        chosen_idx = idx
                        bd['is_exploration'] = True
                        break

            if chosen_idx == -1:
                # Sélection normale avec pénalités de répétition
                best_adjusted_score = float('-inf')
                best_idx = 0

                # On inspecte les 15 meilleurs candidats restants pour éviter une complexité O(N^2) excessive
                inspect_window = min(len(remaining), 15)

                for idx in range(inspect_window):
                    pub, score, bd = remaining[idx]
                    adjusted_score = score
                    e_id = pub.etablissement_id
                    c_id = pub.produit.categorie_id if (pub.produit and pub.produit.categorie_id) else None

                    # Répétition d'établissement
                    if len(recent_etabs) >= EngineConfig.MAX_CONSECUTIVE_ESTABLISHMENT:
                        if all(e == e_id for e in recent_etabs[-EngineConfig.MAX_CONSECUTIVE_ESTABLISHMENT:]):
                            adjusted_score *= (1.0 - EngineConfig.PENALTY_REPEAT_ESTABLISHMENT)

                    # Répétition de catégorie
                    if c_id and len(recent_cats) >= EngineConfig.MAX_CONSECUTIVE_CATEGORY:
                        if all(c == c_id for c in recent_cats[-EngineConfig.MAX_CONSECUTIVE_CATEGORY:]):
                            adjusted_score *= (1.0 - EngineConfig.PENALTY_REPEAT_CATEGORY)

                    if adjusted_score > best_adjusted_score:
                        best_adjusted_score = adjusted_score
                        best_idx = idx

                chosen_idx = best_idx

            chosen_item = remaining.pop(chosen_idx)
            pub, orig_score, breakdown = chosen_item

            e_id = pub.etablissement_id
            c_id = pub.produit.categorie_id if (pub.produit and pub.produit.categorie_id) else None

            recent_etabs.append(e_id)
            if c_id:
                recent_cats.append(c_id)

            if len(recent_etabs) > 5:
                recent_etabs.pop(0)
            if len(recent_cats) > 5:
                recent_cats.pop(0)

            final_feed.append((pub, orig_score, breakdown))

        return final_feed
