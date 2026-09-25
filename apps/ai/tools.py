from django.db.models import Q
from apps.catalog.models import Produit, Etablissement, Categorie


def search_food(query=None, category_slug=None, max_price=None, location=None, type_etablissement=None, is_available=True, limit=5):
    """
    Recherche multicritère de produits/plats réels dans la base de données AYYOU.
    Toutes les données sont extraites directement de PostgreSQL.
    """
    qs = Produit.objects.select_related('etablissement', 'categorie').filter(
        etablissement__statut_verification=Etablissement.STATUT_VALIDE
    )

    if is_available:
        qs = qs.filter(est_disponible=True)

    if query:
        q_str = str(query).strip()
        qs = qs.filter(
            Q(nom__icontains=q_str) |
            Q(description__icontains=q_str) |
            Q(categorie__nom__icontains=q_str)
        )

    if category_slug:
        c_str = str(category_slug).strip().lower()
        c_clean = c_str.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        qs = qs.filter(
            Q(categorie__slug__icontains=c_clean) |
            Q(categorie__nom__icontains=c_str) |
            Q(categorie__nom__icontains=c_clean)
        )

    if max_price is not None:
        try:
            max_p = float(max_price)
            if max_p > 0:
                qs = qs.filter(prix_base__lte=max_p)
        except (ValueError, TypeError):
            pass

    if location:
        loc_str = str(location).strip()
        qs = qs.filter(
            Q(etablissement__adresse__icontains=loc_str) |
            Q(etablissement__nom__icontains=loc_str)
        )

    if type_etablissement:
        qs = qs.filter(etablissement__type_etablissement__iexact=str(type_etablissement).strip())

    results = []
    for p in qs[:limit]:
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
            "est_disponible": p.est_disponible,
            "temps_livraison": "15-25 min"
        })
    return results


def search_establishments(type_etablissement=None, query=None, location=None, limit=5):
    """
    Recherche d'établissements réels (Restaurants ou Vendeurs).
    """
    qs = Etablissement.objects.filter(statut_verification=Etablissement.STATUT_VALIDE)

    if type_etablissement:
        qs = qs.filter(type_etablissement__iexact=str(type_etablissement).strip())

    if query:
        q_str = str(query).strip()
        qs = qs.filter(Q(nom__icontains=q_str) | Q(description__icontains=q_str))

    if location:
        loc_str = str(location).strip()
        qs = qs.filter(Q(adresse__icontains=loc_str) | Q(nom__icontains=loc_str))

    results = []
    for e in qs[:limit]:
        results.append({
            "id": e.id,
            "nom": e.nom,
            "type_etablissement": e.type_etablissement,
            "statut": e.statut,
            "adresse": e.adresse or "Dakar",
            "note_moyenne": float(e.note_moyenne),
            "nombre_avis": e.nombre_avis,
            "logo_url": e.logo_url or ""
        })
    return results


def search_by_category(category_slug, location=None, max_price=None, limit=5):
    """
    Recherche de plats par catégorie.
    """
    return search_food(category_slug=category_slug, location=location, max_price=max_price, limit=limit)


def search_by_budget(max_budget, location=None, food_query=None, limit=5):
    """
    Recherche de plats d'un budget maximum.
    """
    return search_food(query=food_query, max_price=max_budget, location=location, limit=limit)


def get_product(product_id):
    """
    Récupère un produit spécifique par son ID réel en base.
    """
    try:
        p = Produit.objects.select_related('etablissement', 'categorie').get(
            id=product_id,
            etablissement__statut_verification=Etablissement.STATUT_VALIDE
        )
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
            "est_disponible": p.est_disponible,
            "temps_livraison": "15-25 min"
        }
    except (Produit.DoesNotExist, ValueError):
        return None


def get_establishment(establishment_id):
    """
    Récupère un établissement spécifique par son ID réel en base.
    """
    try:
        e = Etablissement.objects.get(id=establishment_id, statut_verification=Etablissement.STATUT_VALIDE)
        return {
            "id": e.id,
            "nom": e.nom,
            "type_etablissement": e.type_etablissement,
            "statut": e.statut,
            "adresse": e.adresse or "Dakar",
            "note_moyenne": float(e.note_moyenne),
            "nombre_avis": e.nombre_avis,
            "logo_url": e.logo_url or ""
        }
    except (Etablissement.DoesNotExist, ValueError):
        return None
