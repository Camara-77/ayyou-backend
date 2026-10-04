import re
import math
from typing import Optional, Dict, Any, List
from django.db.models import Q, Count
from apps.catalog.models import Produit, Etablissement, Categorie
from apps.catalog.search_engine import normalize_text, SYNONYM_MAP


def parse_budget(val: Any) -> Optional[float]:
    """
    Parse et sécurise les valeurs de budget saisies par l'utilisateur ou l'IA.
    Gère les formats : '5000 FCFA', '5 000 FCFA', '5.000 FCFA', '5,000 FCFA', '5000f', '5k', 5000.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else None

    s = str(val).strip().lower()
    if not s:
        return None

    # Support '5k', '10k'
    k_match = re.search(r'^(\d+(?:\.\d+)?)\s*k$', s)
    if k_match:
        return float(k_match.group(1)) * 1000.0

    # Nettoyage des chaînes type FCFA, CFA, F, francs, espaces
    cleaned = re.sub(r'[^\d.,]', '', s)
    if not cleaned:
        return None

    if '.' in cleaned and ',' in cleaned:
        if cleaned.find('.') < cleaned.find(','):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        parts = cleaned.split('.')
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            cleaned = cleaned.replace('.', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            cleaned = cleaned.replace(',', '')
        else:
            cleaned = cleaned.replace(',', '.')

    try:
        res = float(cleaned)
        return res if res > 0 else None
    except ValueError:
        return None


class CatalogSearchService:
    """
    Service centralisé pour la recherche et la consultation du catalogue AYYOU.
    Garantit que PostgreSQL est la SEULE SOURCE DE VÉRITÉ MÉTIER.

    Règles absolues P0 :
    - Catégories exposées : est_active=True ET au moins 1 produit disponible.
    - Établissements exposés : statut_verification=VALIDE ET au moins 1 produit disponible.
    - Recherche restaurant par plat : passe STRICTEMENT par la relation Produit -> Etablissement.
      (Jamais de correspondance basée uniquement sur le nom de l'établissement).
    - Disponibilité & Prix : extraits en temps réel de PostgreSQL.
    """

    @classmethod
    def get_base_product_queryset(cls, is_available: bool = True):
        """
        QuerySet de base pour les produits exploitables par le client / Copilote.
        """
        qs = Produit.objects.select_related('etablissement', 'categorie').filter(
            etablissement__isnull=False,
            etablissement__statut_verification=Etablissement.STATUT_VALIDE
        )
        if is_available:
            qs = qs.filter(est_disponible=True)
        return qs

    @classmethod
    def get_base_establishment_queryset(cls):
        """
        QuerySet de base pour les établissements exploitables (ayant au moins 1 produit dispo).
        """
        return Etablissement.objects.filter(
            statut_verification=Etablissement.STATUT_VALIDE,
            produits__isnull=False,
            produits__est_disponible=True
        ).distinct()

    @classmethod
    def get_base_category_queryset(cls):
        """
        QuerySet de base pour les catégories actives ET contenant au moins 1 produit dispo.
        Exclut systématiquement les catégories vides destineées à l'administration.
        """
        return Categorie.objects.filter(
            est_active=True,
            produits__isnull=False,
            produits__est_disponible=True,
            produits__etablissement__statut_verification=Etablissement.STATUT_VALIDE
        ).annotate(
            nombre_plats_dispo=Count(
                'produits',
                filter=Q(
                    produits__est_disponible=True,
                    produits__etablissement__statut_verification=Etablissement.STATUT_VALIDE
                )
            )
        ).filter(nombre_plats_dispo__gt=0).order_by('ordre', 'nom').distinct()

    @classmethod
    def expand_search_terms(cls, query: str) -> set:
        """
        Élargit la recherche avec synonymes et équivalences de mots-clés.
        """
        if not query:
            return set()
        q_raw = str(query).strip()
        q_str = q_raw.lower()
        q_clean = normalize_text(q_raw)
        search_terms = {q_raw, q_str, q_clean}

        if 'thieb' in q_clean:
            search_terms.add(q_clean.replace('thieb', 'thiéb'))
            search_terms.add('thiéboudienne')
            search_terms.add('thieboudienne')

        for term in list(search_terms):
            if term in SYNONYM_MAP:
                for syn in SYNONYM_MAP[term]:
                    search_terms.add(normalize_text(syn))

        return {t for t in search_terms if t}

    @classmethod
    def search_products(
        cls,
        query: Optional[str] = None,
        category_slug: Optional[str] = None,
        max_price: Optional[Any] = None,
        location: Optional[str] = None,
        type_etablissement: Optional[str] = None,
        is_available: bool = True,
        limit: int = 6,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Recherche multicritère de produits réels en base.
        """
        qs = cls.get_base_product_queryset(is_available=is_available)

        if query:
            search_terms = cls.expand_search_terms(query)
            query_filter = Q()
            for term in search_terms:
                query_filter |= (
                    Q(nom__icontains=term) |
                    Q(description__icontains=term) |
                    Q(categorie__nom__icontains=term)
                )
            qs = qs.filter(query_filter)

        if category_slug:
            c_str = str(category_slug).strip().lower()
            c_clean = normalize_text(c_str)
            qs = qs.filter(
                Q(categorie__slug__icontains=c_clean) |
                Q(categorie__nom__icontains=c_str) |
                Q(categorie__nom__icontains=c_clean)
            )

        budget_val = parse_budget(max_price)
        if budget_val is not None:
            qs = qs.filter(prix_base__lte=budget_val)

        if location:
            loc_str = str(location).strip()
            qs = qs.filter(
                Q(etablissement__adresse__icontains=loc_str) |
                Q(etablissement__nom__icontains=loc_str)
            )

        if type_etablissement:
            qs = qs.filter(etablissement__type_etablissement__iexact=str(type_etablissement).strip())

        qs = qs.distinct().order_by('-date_creation')
        total_count = qs.count()

        start_idx = max(0, int(offset))
        end_idx = start_idx + int(limit)
        page_qs = qs[start_idx:end_idx]

        results = []
        for p in page_qs:
            results.append({
                "id": p.id,
                "nom": p.nom,
                "description": p.description or "",
                "prix": float(p.prix_base),
                "prix_formate": f"{float(p.prix_base):,.0f} FCFA".replace(",", " "),
                "image_url": p.image_url or "assets/images/thieboudienne.jpg",
                "etablissement_id": p.etablissement.id if p.etablissement else None,
                "etablissement_nom": p.etablissement.nom if p.etablissement else "AYYOU",
                "etablissement_adresse": p.etablissement.adresse if p.etablissement else "Dakar",
                "etablissement_type": p.etablissement.type_etablissement if p.etablissement else "RESTAURANT",
                "categorie_id": p.categorie.id if p.categorie else None,
                "categorie_nom": p.categorie.nom if p.categorie else "",
                "est_disponible": p.est_disponible,
                "temps_livraison": None
            })

        has_more = end_idx < total_count
        remaining_count = max(0, total_count - end_idx)

        return {
            "success": True,
            "type": "product_search",
            "total_count": total_count,
            "has_more": has_more,
            "remaining_count": remaining_count,
            "offset": start_idx,
            "limit": int(limit),
            "filters": {
                "query": query,
                "category_slug": category_slug,
                "max_price": budget_val,
                "location": location
            },
            "results": results
        }

    @classmethod
    def search_establishments_by_product(
        cls,
        product_query: Optional[str] = None,
        max_price: Optional[Any] = None,
        location: Optional[str] = None,
        type_etablissement: Optional[str] = None,
        limit: int = 6,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Recherche spécialisée d'établissements qui proposent UN PRODUIT RÉEL correspondant.
        FLUX OBLIGATOIRE : Produit -> Etablissement (Jamais de correspondance sur le nom d'établissement).
        """
        budget_val = parse_budget(max_price)

        # 1. Partir du QuerySet Produit valide
        prod_qs = cls.get_base_product_queryset(is_available=True)

        search_terms = set()
        if product_query:
            search_terms = cls.expand_search_terms(product_query)
            q_p_filter = Q()
            for term in search_terms:
                q_p_filter |= Q(nom__icontains=term) | Q(description__icontains=term)
            prod_qs = prod_qs.filter(q_p_filter)

        if budget_val is not None:
            prod_qs = prod_qs.filter(prix_base__lte=budget_val)

        # Extraire les IDs d'établissements rattachés aux produits trouvés
        matching_est_ids = prod_qs.values_list('etablissement_id', flat=True).distinct()

        # 2. Filtrer la base d'établissements uniquement par ces IDs
        est_qs = cls.get_base_establishment_queryset().filter(id__in=matching_est_ids)

        if location:
            loc_str = str(location).strip()
            est_qs = est_qs.filter(Q(adresse__icontains=loc_str) | Q(nom__icontains=loc_str))

        if type_etablissement:
            est_qs = est_qs.filter(type_etablissement__iexact=str(type_etablissement).strip())

        est_qs = est_qs.order_by('-note_moyenne', 'nom')
        total_count = est_qs.count()

        start_idx = max(0, int(offset))
        end_idx = start_idx + int(limit)
        page_ests = est_qs[start_idx:end_idx]

        results = []
        for e in page_ests:
            # Récupérer le plat échantillon correspondant exactement à la recherche
            e_prods = prod_qs.filter(etablissement=e)
            sample_prod = e_prods.first() or e.produits.filter(est_disponible=True).first()

            if not sample_prod:
                # Sécurité : ne jamais retourner un établissement sans produit valide
                continue

            image = e.couverture_url or e.logo_url or sample_prod.image_url or "assets/images/thieboudienne.jpg"
            cat_nom = sample_prod.categorie.nom if sample_prod.categorie else (e.specialite or "Sénégalais & Fast-Food")

            results.append({
                "id": e.id,
                "nom": e.nom,
                "type_etablissement": e.type_etablissement,
                "statut": e.statut,
                "adresse": e.adresse or "Dakar",
                "note_moyenne": float(e.note_moyenne),
                "nombre_avis": e.nombre_avis,
                "logo_url": e.logo_url or "",
                "couverture_url": e.couverture_url or "",
                "image_url": image,
                "categorie_nom": cat_nom,
                "produit_propose": sample_prod.nom,
                "product_id": sample_prod.id,
                "prix": float(sample_prod.prix_base),
                "prix_formate": f"{float(sample_prod.prix_base):,.0f} FCFA".replace(",", " ")
            })

        has_more = end_idx < total_count
        remaining_count = max(0, total_count - end_idx)

        return {
            "success": True,
            "type": "restaurant_search",
            "total_count": total_count,
            "has_more": has_more,
            "remaining_count": remaining_count,
            "offset": start_idx,
            "limit": int(limit),
            "filters": {
                "product_query": product_query,
                "max_price": budget_val,
                "location": location
            },
            "results": results
        }

    @classmethod
    def search_establishments(
        cls,
        type_etablissement: Optional[str] = None,
        query: Optional[str] = None,
        location: Optional[str] = None,
        max_price: Optional[Any] = None,
        limit: int = 6,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Recherche générale d'établissements. Si un mot-clé ou un budget est spécifié,
        délègue à search_establishments_by_product() pour garantir qu'aucun restaurant
        sans le produit demandé n'est retourné.
        """
        if query or max_price is not None:
            return cls.search_establishments_by_product(
                product_query=query,
                max_price=max_price,
                location=location,
                type_etablissement=type_etablissement,
                limit=limit,
                offset=offset
            )

        # Découverte globale d'établissements ayant au moins 1 produit dispo
        est_qs = cls.get_base_establishment_queryset()

        if type_etablissement:
            est_qs = est_qs.filter(type_etablissement__iexact=str(type_etablissement).strip())

        if location:
            loc_str = str(location).strip()
            est_qs = est_qs.filter(Q(adresse__icontains=loc_str) | Q(nom__icontains=loc_str))

        est_qs = est_qs.order_by('-note_moyenne', 'nom')
        total_count = est_qs.count()

        start_idx = max(0, int(offset))
        end_idx = start_idx + int(limit)
        page_ests = est_qs[start_idx:end_idx]

        results = []
        for e in page_ests:
            sample_prod = e.produits.filter(est_disponible=True).first()
            if not sample_prod:
                continue

            image = e.couverture_url or e.logo_url or sample_prod.image_url or "assets/images/thieboudienne.jpg"
            cat_nom = sample_prod.categorie.nom if sample_prod.categorie else (e.specialite or "Sénégalais & Fast-Food")

            results.append({
                "id": e.id,
                "nom": e.nom,
                "type_etablissement": e.type_etablissement,
                "statut": e.statut,
                "adresse": e.adresse or "Dakar",
                "note_moyenne": float(e.note_moyenne),
                "nombre_avis": e.nombre_avis,
                "logo_url": e.logo_url or "",
                "couverture_url": e.couverture_url or "",
                "image_url": image,
                "categorie_nom": cat_nom,
                "produit_propose": sample_prod.nom,
                "product_id": sample_prod.id,
                "prix": float(sample_prod.prix_base),
                "prix_formate": f"{float(sample_prod.prix_base):,.0f} FCFA".replace(",", " ")
            })

        has_more = end_idx < total_count
        remaining_count = max(0, total_count - end_idx)

        return {
            "success": True,
            "type": "restaurant_search",
            "total_count": total_count,
            "has_more": has_more,
            "remaining_count": remaining_count,
            "offset": start_idx,
            "limit": int(limit),
            "results": results
        }

    @classmethod
    def get_establishment_products(
        cls,
        establishment_id: int,
        is_available: bool = True,
        category_slug: Optional[str] = None,
        max_price: Optional[Any] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Récupère les produits d'un établissement spécifique.
        Garantit de retourner uniquement les vrais produits disponibles de cet établissement.
        """
        qs = cls.get_base_product_queryset(is_available=is_available).filter(
            etablissement_id=establishment_id
        )

        if category_slug:
            c_clean = normalize_text(category_slug)
            qs = qs.filter(
                Q(categorie__slug__icontains=c_clean) |
                Q(categorie__nom__icontains=category_slug)
            )

        budget_val = parse_budget(max_price)
        if budget_val is not None:
            qs = qs.filter(prix_base__lte=budget_val)

        total_count = qs.count()
        start_idx = max(0, int(offset))
        end_idx = start_idx + int(limit)

        results = []
        for p in qs[start_idx:end_idx]:
            results.append({
                "id": p.id,
                "nom": p.nom,
                "description": p.description or "",
                "prix": float(p.prix_base),
                "prix_formate": f"{float(p.prix_base):,.0f} FCFA".replace(",", " "),
                "image_url": p.image_url or "assets/images/thieboudienne.jpg",
                "etablissement_id": p.etablissement_id,
                "etablissement_nom": p.etablissement.nom if p.etablissement else "",
                "categorie_id": p.categorie_id,
                "categorie_nom": p.categorie.nom if p.categorie else "",
                "est_disponible": p.est_disponible
            })

        return {
            "success": True,
            "establishment_id": establishment_id,
            "total_count": total_count,
            "has_more": end_idx < total_count,
            "offset": start_idx,
            "limit": int(limit),
            "results": results
        }

    @classmethod
    def get_product(cls, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un produit unique par son ID réel en base.
        """
        try:
            p = cls.get_base_product_queryset(is_available=False).get(id=product_id)
            return {
                "id": p.id,
                "nom": p.nom,
                "description": p.description or "",
                "prix": float(p.prix_base),
                "prix_formate": f"{float(p.prix_base):,.0f} FCFA".replace(",", " "),
                "image_url": p.image_url or "assets/images/thieboudienne.jpg",
                "etablissement_id": p.etablissement.id if p.etablissement else None,
                "etablissement_nom": p.etablissement.nom if p.etablissement else "AYYOU",
                "etablissement_adresse": p.etablissement.adresse if p.etablissement else "Dakar",
                "categorie_id": p.categorie.id if p.categorie else None,
                "categorie_nom": p.categorie.nom if p.categorie else "",
                "est_disponible": p.est_disponible
            }
        except (Produit.DoesNotExist, ValueError, TypeError):
            return None

    @classmethod
    def get_category(cls, category_id_or_slug: Any) -> Optional[Dict[str, Any]]:
        """
        Récupère une catégorie si active et contenant au moins 1 produit disponible.
        """
        qs = cls.get_base_category_queryset()
        try:
            if str(category_id_or_slug).isdigit():
                cat = qs.get(id=int(category_id_or_slug))
            else:
                cat = qs.get(slug=str(category_id_or_slug))

            return {
                "id": cat.id,
                "nom": cat.nom,
                "slug": cat.slug,
                "icone": cat.icone or "utensils",
                "image_url": cat.image_url or "",
                "nombre_plats": cat.nombre_plats_dispo
            }
        except (Categorie.DoesNotExist, ValueError):
            return None

    @classmethod
    def get_categories_with_products(cls, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Récupère uniquement les catégories actives possédant au moins 1 produit disponible.
        Exclut les 5 catégories vides en base.
        """
        cats = cls.get_base_category_queryset()[:limit]
        results = []
        for c in cats:
            results.append({
                "id": c.id,
                "nom": c.nom,
                "slug": c.slug,
                "icone": c.icone or "utensils",
                "image_url": c.image_url or "",
                "nombre_plats": getattr(c, 'nombre_plats_dispo', 0)
            })
        return results
