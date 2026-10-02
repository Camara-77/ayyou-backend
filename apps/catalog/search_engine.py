import re
import unicodedata
from difflib import get_close_matches
from django.db.models import Q

def strip_accents(text: str) -> str:
    """
    Supprime tous les accents et caractères diacritiques d'un texte.
    Ex: "Thiéboudienne" -> "Thieboudienne", "Mafé" -> "Mafe"
    """
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def normalize_text(text: str) -> str:
    """
    Normalise une chaîne : minuscules, suppression des accents, suppression de la ponctuation inutile.
    """
    if not text:
        return ""
    text_clean = strip_accents(text.lower())
    text_clean = re.sub(r"[^\w\s]", " ", text_clean)
    return " ".join(text_clean.split())

# Dictionnaire de synonymes & équivalences culinaires AYYOU (Sénégal & International)
SYNONYM_MAP = {
    "hamburger": ["hamburger", "burger", "burgers", "cheeseburger", "cheeseburgers"],
    "hamburgers": ["hamburger", "burger", "burgers", "cheeseburger", "cheeseburgers"],
    "hambuger": ["hamburger", "burger", "cheeseburger"],
    "hamburgeur": ["hamburger", "burger", "cheeseburger"],
    "hamburguer": ["hamburger", "burger", "cheeseburger"],
    "burger": ["burger", "burgers", "hamburger", "hamburgers", "cheeseburger", "cheeseburgers"],
    "burgers": ["burger", "burgers", "hamburger", "cheeseburger"],
    "cheeseburger": ["cheeseburger", "cheeseburgers", "burger", "hamburger"],
    "mafe": ["mafe", "mafé", "tigadeguena", "tigadéguéna", "arachide"],
    "mafé": ["mafe", "mafé", "tigadeguena", "tigadéguéna", "arachide"],
    "tigadeguena": ["tigadeguena", "mafe", "mafé"],
    "thieboudienne": ["thieboudienne", "thiéboudienne", "ceebu jen", "ceebu jën", "thiebou", "thiébou", "tieb"],
    "thiéboudienne": ["thieboudienne", "thiéboudienne", "ceebu jen", "ceebu jën", "thiebou", "thiébou", "tieb"],
    "thiebou": ["thiebou", "thiébou", "thieboudienne", "thiéboudienne", "ceebu jen"],
    "thiébou": ["thiebou", "thiébou", "thieboudienne", "thiéboudienne"],
    "thie": ["thieboudienne", "thiéboudienne", "thiebou", "thiébou"],
    "thié": ["thieboudienne", "thiéboudienne", "thiebou", "thiébou"],
    "ceebu": ["ceebu jen", "ceebu jën", "thieboudienne", "thiéboudienne"],
    "yassa": ["yassa", "yassa poulet", "yassa poisson", "ceebu yassa"],
    "dibi": ["dibi", "dibiterie", "grillade", "grillades", "agneau", "haoussa"],
    "dibiterie": ["dibiterie", "dibi", "grillade", "grillades"],
    "grillade": ["grillade", "grillades", "dibi", "dibiterie"],
    "grillades": ["grillade", "grillades", "dibi", "dibiterie"],
    "tangana": ["tangana", "sandwich", "sandwichs", "foie", "oeuf"],
    "bissap": ["bissap", "jus de bissap", "hibiscus"],
    "bouye": ["bouye", "jus de bouye", "pain de singe", "baobab"],
    "attieke": ["attieke", "attiéké", "garba", "aloco", "alloco"],
    "attiéké": ["attieke", "attiéké", "garba", "aloco"],
    "poisson": ["poisson", "poissons", "poisson braise", "poisson braisé", "thiof", "tilapia", "capitaine", "merou"],
    "poulet": ["poulet", "poulets", "dibi poulet", "yassa poulet"],
    "pizza": ["pizza", "pizzas"],
    "pizzas": ["pizza", "pizzas"],
    "salade": ["salade", "salades", "healthy"],
    "fruit": ["fruit", "fruits", "smoothie"],
    "fruits": ["fruit", "fruits", "smoothie"],
    "chawarma": ["chawarma", "tacos", "shawarma"],
    "tacos": ["tacos", "chawarma", "fast food"]
}

class CatalogSearchEngine:
    """
    Moteur de recherche tolérant, intelligent et performant pour le catalogue AYYOU.
    """

    @classmethod
    def expand_query_tokens(cls, query: str) -> set:
        """
        Extrait et élargit les mots-clés de recherche avec accents et synonymes.
        """
        raw_norm = normalize_text(query)
        if not raw_norm:
            return set()

        tokens = set(raw_norm.split())

        expanded = set(tokens)
        expanded.add(raw_norm)

        for token in tokens:
            if token in SYNONYM_MAP:
                for syn in SYNONYM_MAP[token]:
                    expanded.add(normalize_text(syn))

        return expanded

    @classmethod
    def score_produit(cls, produit, query_norm: str, expanded_tokens: set) -> int:
        """
        Calcule un score de pertinence pour un produit donné.
        """
        score = 0

        nom_norm = normalize_text(produit.nom)
        desc_norm = normalize_text(produit.description)
        cat_norm = normalize_text(produit.categorie.nom if produit.categorie else "")
        etab_nom = normalize_text(produit.etablissement.nom if produit.etablissement else "")
        etab_spec = normalize_text(produit.etablissement.specialite if produit.etablissement else "")

        # 1. Correspondance exacte sur le nom
        if query_norm == nom_norm:
            score += 150
        elif query_norm in nom_norm:
            score += 100

        # 2. Correspondance partielle ou synonyme sur le nom
        for token in expanded_tokens:
            if not token:
                continue
            if token == nom_norm:
                score += 90
            elif token in nom_norm:
                score += 70
            elif len(token) >= 3 and token in nom_norm:
                score += 50
            elif len(token) >= 3 and nom_norm.startswith(token):
                score += 60

        # 3. Correspondance sur la Catégorie
        if query_norm in cat_norm or cat_norm in query_norm:
            score += 50
        for token in expanded_tokens:
            if token and token in cat_norm:
                score += 35

        # 4. Correspondance sur l'Établissement & Spécialité
        if query_norm in etab_nom or query_norm in etab_spec:
            score += 40
        for token in expanded_tokens:
            if token and (token in etab_nom or token in etab_spec):
                score += 25

        # 5. Correspondance sur la Description
        if query_norm in desc_norm:
            score += 30
        for token in expanded_tokens:
            if token and token in desc_norm:
                score += 15

        # 6. Fuzzy matching (Tolérance aux fautes de frappe sur le nom)
        if score == 0 and len(query_norm) >= 4:
            nom_words = nom_norm.split()
            close = get_close_matches(query_norm, nom_words, n=1, cutoff=0.7)
            if close:
                score += 45

        return score

    @classmethod
    def search_produits(cls, queryset, query: str):
        """
        Filtre et classe les produits par pertinence selon la requête.
        """
        if not query or not query.strip():
            return queryset

        query_norm = normalize_text(query)
        expanded_tokens = cls.expand_query_tokens(query)

        # Filtre initial SQL pour limiter le volume traité
        q_filter = Q()
        for token in expanded_tokens:
            if not token:
                continue
            q_filter |= (
                Q(nom__icontains=token) |
                Q(description__icontains=token) |
                Q(categorie__nom__icontains=token) |
                Q(etablissement__nom__icontains=token) |
                Q(etablissement__specialite__icontains=token)
            )

        # Si recherche partielle courte (ex: "hamb", "thié")
        if len(query_norm) >= 3:
            q_filter |= Q(nom__icontains=query_norm) | Q(categorie__nom__icontains=query_norm)

        candidates = list(queryset.filter(q_filter).distinct())

        # Si le filtre SQL strict ne trouve rien, tester sur l'ensemble pour le fuzzy matching
        if not candidates and len(query_norm) >= 4:
            all_prods = list(queryset[:300])
            candidates = all_prods

        scored_items = []
        for p in candidates:
            sc = cls.score_produit(p, query_norm, expanded_tokens)
            if sc > 0:
                scored_items.append((sc, p))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_items]

    @classmethod
    def score_etablissement(cls, etab, query_norm: str, expanded_tokens: set) -> int:
        """
        Calcule un score de pertinence pour un établissement.
        """
        score = 0
        nom_norm = normalize_text(etab.nom)
        spec_norm = normalize_text(etab.specialite)
        desc_norm = normalize_text(etab.description)
        adresse_norm = normalize_text(etab.adresse)

        if query_norm == nom_norm:
            score += 150
        elif query_norm in nom_norm:
            score += 100

        if query_norm in spec_norm:
            score += 80

        for token in expanded_tokens:
            if not token:
                continue
            if token in nom_norm:
                score += 70
            if token in spec_norm:
                score += 50
            if token in desc_norm or token in adresse_norm:
                score += 20

        if score == 0 and len(query_norm) >= 4:
            nom_words = nom_norm.split() + spec_norm.split()
            close = get_close_matches(query_norm, nom_words, n=1, cutoff=0.7)
            if close:
                score += 45

        return score

    @classmethod
    def search_etablissements(cls, queryset, query: str):
        """
        Filtre et classe les établissements par pertinence.
        """
        if not query or not query.strip():
            return queryset

        query_norm = normalize_text(query)
        expanded_tokens = cls.expand_query_tokens(query)

        q_filter = Q()
        for token in expanded_tokens:
            if not token:
                continue
            q_filter |= (
                Q(nom__icontains=token) |
                Q(specialite__icontains=token) |
                Q(description__icontains=token) |
                Q(adresse__icontains=token)
            )

        if len(query_norm) >= 3:
            q_filter |= Q(nom__icontains=query_norm) | Q(specialite__icontains=query_norm)

        candidates = list(queryset.filter(q_filter).distinct())
        if not candidates and len(query_norm) >= 4:
            candidates = list(queryset[:200])

        scored_items = []
        for e in candidates:
            sc = cls.score_etablissement(e, query_norm, expanded_tokens)
            if sc > 0:
                scored_items.append((sc, e))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_items]
