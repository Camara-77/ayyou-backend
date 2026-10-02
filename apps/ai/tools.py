import math
from django.db.models import Q
from apps.catalog.models import Produit, Etablissement, Categorie
from apps.orders.models import Commande
from apps.deliveries.models import Livraison


def search_food(query=None, category_slug=None, max_price=None, location=None, type_etablissement=None, is_available=True, limit=5):
    """
    Recherche multicritère de produits/plats réels dans la base de données AYYOU.
    Toutes les données sont extraites directement de PostgreSQL via l'ORM.
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
            "temps_livraison": None
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
            "temps_livraison": None
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


def get_user_orders(user_id=None, limit=5):
    """
    Récupère les commandes appartenant exclusivement au client connecté (user_id).
    Sécurité : Si user_id est absent, refuse la consultation.
    """
    if not user_id:
        return {
            "success": False,
            "reason": "NOT_AUTHENTICATED",
            "message": "Veuillez vous connecter pour consulter vos commandes personnelles.",
            "count": 0,
            "results": []
        }

    try:
        commandes = Commande.objects.filter(utilisateur_id=user_id).order_by('-date_creation')[:limit]
        results = []
        for c in commandes:
            produits_list = []
            etablissements_list = set()
            for sc in c.sous_commandes.all():
                if sc.etablissement:
                    etablissements_list.add(sc.etablissement.nom)
                for ligne in sc.lignes.all():
                    produits_list.append({
                        "produit_id": ligne.produit_id,
                        "nom": ligne.nom_produit_snapshot,
                        "quantite": ligne.quantite,
                        "prix_unitaire": float(ligne.prix_unitaire),
                        "total_ligne": float(ligne.total_ligne)
                    })

            livraison_info = None
            if hasattr(c, 'livraison') and c.livraison:
                liv = c.livraison
                livraison_info = {
                    "livraison_id": liv.id,
                    "statut": liv.statut,
                    "statut_display": liv.get_statut_display(),
                    "livreur_nom": liv.livreur.utilisateur.get_full_name() if (liv.livreur and liv.livreur.utilisateur) else None,
                    "date_attribution": liv.date_attribution.isoformat() if liv.date_attribution else None
                }

            results.append({
                "commande_id": c.id,
                "numero_commande": c.numero_commande,
                "statut": c.statut,
                "statut_display": c.get_statut_display(),
                "montant_total": float(c.total),
                "total_formate": f"{float(c.total):,.0f} FCFA".replace(",", " "),
                "date_creation": c.date_creation.isoformat() if c.date_creation else None,
                "etablissements": list(etablissements_list),
                "produits": produits_list,
                "livraison": livraison_info
            })

        return {
            "success": True,
            "reason": "OK",
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "reason": "ERROR",
            "message": str(e),
            "count": 0,
            "results": []
        }


def get_delivery_status(order_id_or_number, user_id=None):
    """
    Récupère le statut de livraison d'une commande appartenant à user_id.
    Sécurité stricte : Ne renvoie JAMAIS le code_validation PIN 4 chiffres ni le token_qr.
    """
    if not user_id:
        return {
            "success": False,
            "reason": "NOT_AUTHENTICATED",
            "message": "Veuillez vous connecter pour consulter le suivi de livraison."
        }

    try:
        filter_kwargs = {"utilisateur_id": user_id}
        if str(order_id_or_number).isdigit():
            filter_kwargs["id"] = int(order_id_or_number)
        else:
            filter_kwargs["numero_commande"] = str(order_id_or_number).strip()

        commande = Commande.objects.get(**filter_kwargs)
        if not hasattr(commande, 'livraison') or not commande.livraison:
            return {
                "success": False,
                "reason": "NO_DELIVERY",
                "message": f"La commande {commande.numero_commande} n'a pas encore de livraison enregistrée.",
                "commande": {
                    "numero_commande": commande.numero_commande,
                    "statut": commande.statut,
                    "statut_display": commande.get_statut_display()
                }
            }

        liv = commande.livraison
        livreur_info = None
        if liv.livreur:
            u = liv.livreur.utilisateur
            livreur_info = {
                "nom": u.get_full_name() if u else "Livreur AYYOU",
                "telephone": u.numero_telephone if u else "",
                "vehicule": liv.livreur.type_vehicule if hasattr(liv.livreur, 'type_vehicule') else "Moto",
                "zone": liv.livreur.zone_couverture if hasattr(liv.livreur, 'zone_couverture') else "Dakar"
            }

        return {
            "success": True,
            "reason": "OK",
            "delivery": {
                "livraison_id": liv.id,
                "numero_commande": commande.numero_commande,
                "statut": liv.statut,
                "statut_display": liv.get_statut_display(),
                "est_validee": liv.est_validee,
                "livreur": livreur_info,
                "adresse_livraison": commande.adresse_livraison,
                "date_attribution": liv.date_attribution.isoformat() if liv.date_attribution else None,
                "derniere_mise_a_jour": liv.updated_at.isoformat() if liv.updated_at else None
            }
        }
    except Commande.DoesNotExist:
        return {
            "success": False,
            "reason": "NOT_FOUND",
            "message": "Commande introuvable ou vous n'êtes pas autorisé à la consulter."
        }


def search_by_location(latitude, longitude, query=None, category_slug=None, max_price=None, radius_km=10.0, limit=5):
    """
    Recherche des plats et établissements proches des coordonnées GPS spécifiées.
    Calcul Haversine effectué côté Python (Django ORM + filtre de distance).
    """
    try:
        user_lat = float(latitude)
        user_lon = float(longitude)
    except (TypeError, ValueError):
        return search_food(query=query, category_slug=category_slug, max_price=max_price, limit=limit)

    qs = Produit.objects.select_related('etablissement', 'categorie').filter(
        etablissement__statut_verification=Etablissement.STATUT_VALIDE,
        est_disponible=True
    )

    if query:
        q_str = str(query).strip()
        qs = qs.filter(Q(nom__icontains=q_str) | Q(description__icontains=q_str))

    if category_slug:
        c_str = str(category_slug).strip().lower()
        qs = qs.filter(categorie__slug__icontains=c_str)

    if max_price is not None:
        try:
            qs = qs.filter(prix_base__lte=float(max_price))
        except (ValueError, TypeError):
            pass

    annotated_results = []
    for p in qs:
        e = p.etablissement
        if e and e.latitude is not None and e.longitude is not None:
            e_lat = float(e.latitude)
            e_lon = float(e.longitude)

            # Haversine distance in km
            d_lat = math.radians(e_lat - user_lat)
            d_lon = math.radians(e_lon - user_lon)
            a = math.sin(d_lat / 2)**2 + math.cos(math.radians(user_lat)) * math.cos(math.radians(e_lat)) * math.sin(d_lon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance_km = round(6371.0 * c, 2)

            if distance_km <= radius_km:
                annotated_results.append((distance_km, {
                    "id": p.id,
                    "nom": p.nom,
                    "description": p.description or "",
                    "prix": float(p.prix_base),
                    "prix_formate": f"{float(p.prix_base):,.0f} FCFA".replace(",", " "),
                    "image_url": p.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_id": e.id,
                    "etablissement_nom": e.nom,
                    "etablissement_adresse": e.adresse or "Dakar",
                    "distance_km": distance_km,
                    "distance_formatee": f"{distance_km:.1f} km",
                    "est_disponible": p.est_disponible,
                    "temps_livraison": None
                }))

    # Sort by distance
    annotated_results.sort(key=lambda x: x[0])
    return [item[1] for item in annotated_results[:limit]]

