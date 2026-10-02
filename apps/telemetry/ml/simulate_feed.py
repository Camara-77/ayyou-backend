import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from scipy.stats import spearmanr, kendalltau

from apps.catalog.models import PublicationFeed
from apps.telemetry.ml.scoring import RecommendationScoringService

logger = logging.getLogger(__name__)


def run_feed_simulation_for_profile(
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    scenario_name: str = "Simulation Général"
) -> Dict[str, Any]:
    """
    Simule le classement IA (LightGBM V2) pour un profil d'utilisateur/session donné
    et le compare avec l'ordre chronologique du Feed de production actuel.
    
    NE MODIFIE AUCUNE DONNEE EN BASE ET N'AFFECTE PAS LE FEED REEL.
    """
    # 1. Récupération des candidats du Feed actuel (8 vidéos réelles)
    pubs_qs = PublicationFeed.objects.select_related('etablissement', 'produit', 'produit__categorie').all().order_by('-date_publication')
    candidates_list = list(pubs_qs)
    
    if not candidates_list:
        return {
            'scenario_name': scenario_name,
            'user_id': user_id,
            'session_id': session_id,
            'candidates_count': 0,
            'error': 'Aucune publication vidéo candidate trouvée dans le Feed.'
        }

    candidate_ids = [str(pub.id) for pub in candidates_list]
    
    # Ordre actuel (Chronologique 1-indexed)
    current_order_map = {str(pub.id): i + 1 for i, pub in enumerate(candidates_list)}
    current_top_1 = str(candidates_list[0].id)
    current_top_3 = set(candidate_ids[:3])
    current_top_5 = set(candidate_ids[:5])

    # 2. Appel du service de scoring LightGBM V2
    scored_results = RecommendationScoringService.score_candidates(
        publication_ids=candidate_ids,
        user_id=user_id,
        session_id=session_id
    )

    # 3. Construction de la comparaison d'ordonnancement
    ai_order_map = {item['publication_id']: item['rank'] for item in scored_results}
    ai_top_1 = scored_results[0]['publication_id'] if scored_results else None
    ai_top_3 = set([item['publication_id'] for item in scored_results[:3]])
    ai_top_5 = set([item['publication_id'] for item in scored_results[:5]])

    comparison_table = []
    current_ranks = []
    ai_ranks = []

    for item in scored_results:
        pub_id = item['publication_id']
        current_pos = current_order_map.get(pub_id, 0)
        ai_pos = item['rank']
        
        # Variation de position : +X si monte dans le classement, -X si descend
        variation = current_pos - ai_pos
        
        pub_obj = next((p for p in candidates_list if str(p.id) == pub_id), None)
        category_name = pub_obj.produit.categorie.nom if (pub_obj and pub_obj.produit and pub_obj.produit.categorie) else 'N/A'

        comparison_table.append({
            'publication_id': pub_id,
            'current_position': current_pos,
            'ai_position': ai_pos,
            'variation': variation,
            'predicted_score': item['predicted_score'],
            'dish_name': item.get('dish_name', 'N/A'),
            'resto_name': item.get('resto_name', 'N/A'),
            'category_name': category_name,
            'dish_price': item.get('dish_price', 0.0)
        })

        current_ranks.append(current_pos)
        ai_ranks.append(ai_pos)

    # 4. Calcul des métriques statistiques de comparaison
    moved_count = sum(1 for item in comparison_table if item['variation'] != 0)
    unchanged_count = sum(1 for item in comparison_table if item['variation'] == 0)
    avg_delta = float(np.mean([abs(item['variation']) for item in comparison_table])) if comparison_table else 0.0

    overlap_3 = len(current_top_3.intersection(ai_top_3))
    overlap_5 = len(current_top_5.intersection(ai_top_5))

    # Correlation de rang
    spearman_corr, _ = spearmanr(current_ranks, ai_ranks)
    kendall_corr, _ = kendalltau(current_ranks, ai_ranks)

    return {
        'scenario_name': scenario_name,
        'user_id': user_id,
        'session_id': session_id,
        'candidates_count': len(candidates_list),
        'metrics': {
            'current_top_1': current_top_1,
            'ai_top_1': ai_top_1,
            'overlap_top_3': overlap_3,
            'overlap_top_5': overlap_5,
            'moved_videos_count': moved_count,
            'unchanged_videos_count': unchanged_count,
            'avg_position_shift': round(avg_delta, 2),
            'spearman_rank_correlation': round(float(spearman_corr), 4) if not np.isnan(spearman_corr) else 0.0,
            'kendall_tau_correlation': round(float(kendall_corr), 4) if not np.isnan(kendall_corr) else 0.0,
        },
        'comparison_table': comparison_table
    }


def run_all_phase_6_scenarios() -> Dict[str, Any]:
    """
    Exécute l'ensemble des scénarios de simulation définis pour la Phase 6.
    """
    scenarios = [
        {
            'name': 'SCÉNARIO A — Utilisateur authentifié avec historique (Modou Diop #185)',
            'user_id': 185,
            'session_id': None
        },
        {
            'name': 'SCÉNARIO B — Utilisateur authentifié avec peu d’historique (Marché des Fruits #184)',
            'user_id': 184,
            'session_id': None
        },
        {
            'name': 'SCÉNARIO C — Visiteur anonyme (Session sim_anon_secC_999)',
            'user_id': None,
            'session_id': 'sim_anon_secC_999'
        },
        {
            'name': 'SCÉNARIO D — Profil avec intérêt catégorie (Street Food Awa #181)',
            'user_id': 181,
            'session_id': None
        }
    ]

    results = {}
    for sc in scenarios:
        res = run_feed_simulation_for_profile(
            user_id=sc['user_id'],
            session_id=sc['session_id'],
            scenario_name=sc['name']
        )
        results[sc['name']] = res

    return results
