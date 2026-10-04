class EngineConfig:
    """
    Configuration centralisée des poids, des seuils et des règles déterministes
    du Moteur de Recommandation Comportemental AYYOU.
    AUCUN NOMBRE MAGIQUE N'EST DISPERSÉ DANS LE CODE.
    """

    # --- POIDS DES SIGNAUX COMPORTEMENTAUX BRUTS ---
    WEIGHT_IMPRESSION = 0.5       # Vue passive dans le viewport
    WEIGHT_PLAY = 1.0             # Lancement de la vidéo
    WEIGHT_PAUSE = 0.5            # Pause / Attention temporaire
    WEIGHT_WATCH_MEDIUM = 3.0     # Watch ratio entre 30% et 70%
    WEIGHT_WATCH_HIGH = 6.0       # Watch ratio > 70%
    WEIGHT_COMPLETED = 10.0       # Visionnage complet (100%)
    WEIGHT_SKIP = -4.0            # Zappe rapide (< 3s ou ratio < 15%) - Pénalité déterministe
    WEIGHT_LIKE = 12.0            # Signal social positif fort
    WEIGHT_UNLIKE = -8.0          # Signal d'aversion
    WEIGHT_SHARE = 15.0           # Signal très fort de recommandation utilisateur
    WEIGHT_DISH_CLICK = 12.0      # Clic sur la fiche plat
    WEIGHT_CART_ADD = 20.0        # Signal d'intention d'achat extrême
    WEIGHT_ORDER = 35.0           # Conversion d'achat réelle (Signal ultime)

    # --- DÉCROISSANCE TEMPORELLE (TIME DECAY) ---
    # Réduit progressivement le poids des anciennes interactions
    DECAY_HALF_LIFE_DAYS = 7.0    # Demi-vie de 7 jours (50% de poids après 7j)

    # --- FACTEURS D'ÉCHELLE POUR LE SCORING FINAL ---
    WEIGHT_CATEGORY_AFFINITY = 1.5      # Poids de l'affinité catégorie
    WEIGHT_PRODUCT_AFFINITY = 2.0       # Poids de l'affinité produit spécifique
    WEIGHT_ESTABLISHMENT_AFFINITY = 1.2 # Poids de l'affinité établissement
    WEIGHT_BEHAVIOR_HISTORICAL = 1.0    # Poids des interactions spécifiques sur cette vidéo

    # --- BONUS DE FRAÎCHEUR (RÉCENCE PUBLICATION) ---
    FRESHNESS_HALF_LIFE_DAYS = 3.0      # Les vidéos < 3 jours obtiennent un bonus significatif
    MAX_FRESHNESS_BONUS = 15.0          # Bonus maximal pour une vidéo publiée à l'instant

    # --- POPULARITÉ ---
    POPULARITY_LIKE_WEIGHT = 1.0
    POPULARITY_SHARE_WEIGHT = 2.0
    MAX_POPULARITY_SCORE = 10.0         # Plafond du score de popularité globale

    # --- DIVERSIFICATION ET EXPLORATION DÉTERMINISTE ---
    MAX_CONSECUTIVE_ESTABLISHMENT = 2   # Max 2 vidéos d'un même établissement d'affilée
    MAX_CONSECUTIVE_CATEGORY = 3        # Max 3 vidéos d'une même catégorie d'affilée
    PENALTY_REPEAT_ESTABLISHMENT = 0.50 # Pénalité de 50% sur le score si répétition d'établissement
    PENALTY_REPEAT_CATEGORY = 0.30      # Pénalité de 30% sur le score si répétition de catégorie
    EXPLORATION_INTERVAL = 4            # Insère 1 vidéo d'exploration toutes les 4 vidéos

    # --- SÉCURITÉ ET LIMITES ---
    MAX_CANDIDATES_TO_SCORE = 150
