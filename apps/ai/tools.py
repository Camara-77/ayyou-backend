import math
from django.db.models import Q
from apps.catalog.models import Produit, Etablissement, Categorie
from apps.orders.models import Commande, RepasPlanifie, AdresseLivraison
from apps.deliveries.models import Livraison
from decimal import Decimal


from apps.catalog.catalog_service import CatalogSearchService, parse_budget


FOOD_SYNONYMS = {
    'burger': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'hamburger': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'hamburgers': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'cheeseburger': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'cheeseburgers': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'thieb': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu jen', 'ceebu jën'],
    'thieboudienne': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu jen', 'ceebu jën'],
    'thiéboudienne': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu jen', 'ceebu jën'],
    'tieb': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu jen', 'ceebu jën'],
    'ceebu': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu jen', 'ceebu jën'],
    'yassa': ['yassa'],
    'mafe': ['mafe', 'mafé'],
    'mafé': ['mafe', 'mafé'],
    'dibi': ['dibi', 'dibiterie'],
    'tacos': ['tacos', 'taco', 'french tacos'],
    'pizza': ['pizza', 'pizzas', 'pizzeria'],
    'pastels': ['pastels', 'pastel'],
    'pastel': ['pastels', 'pastel'],
    'attieke': ['attieke', 'attiéké'],
    'attiéké': ['attieke', 'attiéké'],
    'placali': ['placali'],
    'soupou': ['soupou', 'kandia', 'soupou kandia'],
    'kandia': ['soupou', 'kandia', 'soupou kandia'],
    'bissap': ['bissap'],
    'bouye': ['bouye'],
    'salade': ['salade', 'salad'],
    'crepe': ['crepe', 'crêpe', 'crêpes', 'crepes'],
    'crêpe': ['crepe', 'crêpe', 'crêpes', 'crepes'],
    'glace': ['glace', 'sundae', 'crème glacée'],
    'sandwich': ['sandwich', 'tangana'],
    'tangana': ['tangana', 'sandwich'],
    'poulet': ['poulet'],
    'poisson': ['poisson', 'thiof'],
    'thiof': ['thiof', 'poisson'],
    'viande': ['viande', 'boeuf', 'bœuf', 'agneau'],
    'agneau': ['agneau', 'dibi'],
    'crevettes': ['crevette', 'crevettes', 'gambas'],
    'gambas': ['gambas', 'crevette', 'crevettes'],
}


def search_food(query=None, category_slug=None, max_price=None, location=None, type_etablissement=None, is_available=True, limit=5, offset=0):
    """
    Recherche multicritère de produits/plats réels dans la base de données AYYOU via CatalogSearchService.
    """
    res = CatalogSearchService.search_products(
        query=query,
        category_slug=category_slug,
        max_price=max_price,
        location=location,
        type_etablissement=type_etablissement,
        is_available=is_available,
        limit=limit,
        offset=offset
    )
    return res.get("results", [])


def search_food_paginated(query=None, category_slug=None, max_price=None, location=None, type_etablissement=None, is_available=True, limit=6, offset=0):
    """
    Recherche de plats avec pagination via CatalogSearchService.
    """
    return CatalogSearchService.search_products(
        query=query,
        category_slug=category_slug,
        max_price=max_price,
        location=location,
        type_etablissement=type_etablissement,
        is_available=is_available,
        limit=limit,
        offset=offset
    )


def search_establishments(type_etablissement=None, query=None, location=None, limit=5, offset=0):
    """
    Recherche d'établissements réels ayant au moins 1 produit dispo via CatalogSearchService.
    """
    res = CatalogSearchService.search_establishments(
        type_etablissement=type_etablissement,
        query=query,
        location=location,
        limit=limit,
        offset=offset
    )
    return res.get("results", [])


def search_establishments_paginated(type_etablissement=None, query=None, location=None, max_price=None, limit=6, offset=0):
    """
    Recherche d'établissements avec pagination via CatalogSearchService.
    Garantit qu'aucun établissement sans produit exploitable n'est retourné.
    """
    return CatalogSearchService.search_establishments(
        type_etablissement=type_etablissement,
        query=query,
        location=location,
        max_price=max_price,
        limit=limit,
        offset=offset
    )


def search_active_categories(limit=10):
    """
    Récupère les catégories actives possédant au moins 1 produit dispo via CatalogSearchService.
    Exclut systématiquement les 5 catégories vides en base.
    """
    return CatalogSearchService.get_categories_with_products(limit=limit)


def search_multi_criteria(query=None, category_slug=None, max_price=None, location=None, limit=5):
    """
    Recherche combinée multi-critères.
    """
    return search_food(query=query, category_slug=category_slug, max_price=max_price, location=location, limit=limit)


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
    Récupère un produit spécifique par son ID réel en base via CatalogSearchService.
    """
    return CatalogSearchService.get_product(product_id)


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


def get_establishment_products(establishment_id, category_slug=None, max_price=None, limit=20, offset=0):
    """
    Récupère les produits disponibles d'un établissement spécifique via CatalogSearchService.
    """
    return CatalogSearchService.get_establishment_products(
        establishment_id=establishment_id,
        category_slug=category_slug,
        max_price=max_price,
        limit=limit,
        offset=offset
    )



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


def get_user_plannings(user_id, date_planifiee=None, creneau=None, query=None, limit=10):
    """
    Récupère les repas planifiés appartenant au client connecté (user_id).
    Filtre par date, créneau ou recherche par nom de produit.
    """
    if not user_id:
        return {"success": False, "reason": "NOT_AUTHENTICATED", "results": []}

    try:
        qs = RepasPlanifie.objects.select_related('produit', 'etablissement', 'variante').filter(
            utilisateur_id=user_id
        ).exclude(statut=RepasPlanifie.STATUT_ANNULE)

        if date_planifiee:
            qs = qs.filter(date_planifiee=date_planifiee)
        if creneau:
            qs = qs.filter(creneau__iexact=str(creneau).strip())
        if query:
            q_str = str(query).strip()
            qs = qs.filter(
                Q(produit__nom__icontains=q_str) |
                Q(etablissement__nom__icontains=q_str) |
                Q(instructions__icontains=q_str)
            )

        results = []
        for r in qs.order_by('date_planifiee', 'creneau')[:limit]:
            results.append({
                "id": r.id,
                "produit_id": r.produit_id,
                "nom_produit": r.produit.nom if r.produit else "",
                "etablissement_id": r.etablissement_id,
                "nom_etablissement": r.etablissement.nom if r.etablissement else "",
                "date_planifiee": r.date_planifiee.strftime('%Y-%m-%d'),
                "creneau": r.creneau,
                "creneau_display": r.get_creneau_display(),
                "quantite": r.quantite,
                "prix_total": float(r.prix_total),
                "prix_formate": f"{float(r.prix_total):,.0f} FCFA".replace(",", " "),
                "instructions": r.instructions or "",
                "statut": r.statut,
                "statut_display": r.get_statut_display()
            })

        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {"success": False, "reason": "ERROR", "message": str(e), "results": []}


def get_planning_by_id(planning_id, user_id):
    """
    Récupère un repas planifié spécifique appartenant à user_id.
    """
    if not user_id:
        return None
    try:
        r = RepasPlanifie.objects.select_related('produit', 'etablissement', 'variante').get(
            id=planning_id, utilisateur_id=user_id
        )
        return {
            "id": r.id,
            "produit_id": r.produit_id,
            "nom_produit": r.produit.nom if r.produit else "",
            "etablissement_id": r.etablissement_id,
            "nom_etablissement": r.etablissement.nom if r.etablissement else "",
            "date_planifiee": r.date_planifiee.strftime('%Y-%m-%d'),
            "creneau": r.creneau,
            "creneau_display": r.get_creneau_display(),
            "quantite": r.quantite,
            "prix_total": float(r.prix_total),
            "prix_formate": f"{float(r.prix_total):,.0f} FCFA".replace(",", " "),
            "instructions": r.instructions or "",
            "statut": r.statut,
            "statut_display": r.get_statut_display()
        }
    except RepasPlanifie.DoesNotExist:
        return None


def update_user_planning(planning_id, user_id, changes_dict):
    """
    Met à jour un repas planifié appartenant à user_id après validation de l'utilisateur.
    Gère la modification de restaurant, produit, date, heure, créneau, quantité, instructions et recalcul du prix total.
    """
    if not user_id:
        return {"success": False, "message": "Utilisateur non authentifié."}

    try:
        repas = RepasPlanifie.objects.select_related('produit', 'etablissement', 'variante').get(id=planning_id, utilisateur_id=user_id)
        if repas.statut == RepasPlanifie.STATUT_ANNULE:
            return {"success": False, "message": "Impossible de modifier un repas planifié annulé."}

        new_etablissement = repas.etablissement
        if 'etablissement_id' in changes_dict and changes_dict['etablissement_id']:
            try:
                new_etablissement = Etablissement.objects.get(id=changes_dict['etablissement_id'])
            except Etablissement.DoesNotExist:
                return {"success": False, "message": "Le restaurant demandé est introuvable."}

        new_produit = repas.produit
        if 'produit_id' in changes_dict and changes_dict['produit_id']:
            try:
                new_produit = Produit.objects.get(id=changes_dict['produit_id'])
                if not ('etablissement_id' in changes_dict and changes_dict['etablissement_id']):
                    new_etablissement = new_produit.etablissement
            except Produit.DoesNotExist:
                return {"success": False, "message": "Le plat demandé est introuvable."}

        if new_produit and new_etablissement:
            if new_produit.etablissement_id and new_produit.etablissement_id != new_etablissement.id:
                return {
                    "success": False,
                    "message": f"Le plat '{new_produit.nom}' n'est pas proposé par le restaurant '{new_etablissement.nom}'."
                }

        repas.etablissement = new_etablissement
        repas.produit = new_produit

        if 'date_planifiee' in changes_dict and changes_dict['date_planifiee']:
            repas.date_planifiee = changes_dict['date_planifiee']

        if 'heure_planifiee' in changes_dict and changes_dict['heure_planifiee']:
            repas.heure_planifiee = changes_dict['heure_planifiee']

        if 'creneau' in changes_dict and changes_dict['creneau']:
            creneau_val = str(changes_dict['creneau']).upper().strip()
            if creneau_val in [c[0] for c in RepasPlanifie.CHOIX_CRENEAUX]:
                repas.creneau = creneau_val

        if 'quantite' in changes_dict and changes_dict['quantite'] is not None:
            try:
                qty = int(changes_dict['quantite'])
                if qty > 0:
                    repas.quantite = qty
            except (ValueError, TypeError):
                pass

        if 'instructions' in changes_dict and changes_dict['instructions'] is not None:
            repas.instructions = str(changes_dict['instructions']).strip()

        # Recalcul du prix total
        if repas.produit:
            prix_unit = Decimal(str(repas.produit.prix_base))
            if repas.variante:
                prix_unit += Decimal(str(repas.variante.surcout_prix))
            repas.prix_total = prix_unit * Decimal(str(repas.quantite))

        repas.save()

        return {
            "success": True,
            "message": "Le repas planifié a été mis à jour avec succès !",
            "planning": {
                "id": repas.id,
                "nom_produit": repas.produit.nom if repas.produit else "",
                "nom_etablissement": repas.etablissement.nom if repas.etablissement else "",
                "date_planifiee": repas.date_planifiee.strftime('%Y-%m-%d'),
                "heure_planifiee": str(repas.heure_planifiee) if repas.heure_planifiee else None,
                "creneau": repas.creneau,
                "creneau_display": repas.get_creneau_display(),
                "quantite": repas.quantite,
                "prix_total": float(repas.prix_total),
                "prix_formate": f"{float(repas.prix_total):,.0f} FCFA".replace(",", " ")
            }
        }
    except RepasPlanifie.DoesNotExist:
        return {"success": False, "message": "Le repas planifié est introuvable ou ne vous appartient pas."}
    except Exception as e:
        return {"success": False, "message": f"Erreur lors de la modification : {str(e)}"}


def cancel_user_planning(planning_id, user_id):
    """
    Annule un repas planifié appartenant à user_id.
    """
    if not user_id:
        return {"success": False, "message": "Utilisateur non authentifié."}

    try:
        repas = RepasPlanifie.objects.get(id=planning_id, utilisateur_id=user_id)
        repas.statut = RepasPlanifie.STATUT_ANNULE
        repas.save(update_fields=['statut', 'date_modification'])
        return {
            "success": True,
            "message": f"Le repas planifié '{repas.produit.nom if repas.produit else ''}' a été annulé avec succès."
        }
    except RepasPlanifie.DoesNotExist:
        return {"success": False, "message": "Le repas planifié est introuvable ou ne vous appartient pas."}


def update_order_delivery_info(order_id_or_number, user_id, new_address_id=None, new_instructions=None):
    """
    Tente de modifier l'adresse ou les instructions de livraison d'une commande appartenant à user_id.
    Contrôle métier Django : Refuse la modification si la commande est déjà en livraison (STATUT_EN_LIVRAISON) ou livrée (STATUT_LIVREE).
    """
    if not user_id:
        return {"success": False, "message": "Veuillez vous connecter pour modifier votre commande."}

    try:
        filter_kwargs = {"utilisateur_id": user_id}
        if str(order_id_or_number).isdigit():
            filter_kwargs["id"] = int(order_id_or_number)
        else:
            filter_kwargs["numero_commande"] = str(order_id_or_number).strip()

        commande = Commande.objects.get(**filter_kwargs)

        if commande.statut in [Commande.STATUT_EN_LIVRAISON, Commande.STATUT_LIVREE, Commande.STATUT_ANNULEE]:
            return {
                "success": False,
                "message": f"La commande {commande.numero_commande} est déjà au statut '{commande.get_statut_display()}'. Les modifications de livraison ne sont plus autorisées par le système AYYOU."
            }

        if new_address_id:
            try:
                addr = AdresseLivraison.objects.get(id=new_address_id, utilisateur_id=user_id)
                commande.adresse_livraison = addr.adresse
                if addr.latitude and addr.longitude:
                    commande.latitude_livraison = addr.latitude
                    commande.longitude_livraison = addr.longitude
            except AdresseLivraison.DoesNotExist:
                return {"success": False, "message": "L'adresse de livraison sélectionnée est introuvable."}

        if new_instructions is not None:
            commande.instructions_livraison = str(new_instructions).strip()

        commande.save()

        return {
            "success": True,
            "message": f"Les informations de livraison pour la commande {commande.numero_commande} ont été mises à jour !",
            "commande": {
                "numero_commande": commande.numero_commande,
                "adresse_livraison": commande.adresse_livraison,
                "instructions_livraison": commande.instructions_livraison
            }
        }
    except Commande.DoesNotExist:
        return {"success": False, "message": "Commande introuvable ou vous n'êtes pas autorisé à la modifier."}

