from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from apps.users.models import Utilisateur
from apps.catalog.models import Produit, VarianteProduit, OptionProduit, Etablissement
from apps.orders.models import (
    Panier, PanierItem, Commande, SousCommande,
    LigneCommande, LigneCommandeVariante, LigneCommandeOption, AdresseLivraison
)


class CartService:
    """
    Service de gestion métier du Panier Client.
    """

    @staticmethod
    def get_or_create_active_cart(utilisateur: Utilisateur) -> Panier:
        """
        Récupère ou crée le panier actif de l'utilisateur.
        """
        panier, created = Panier.objects.get_or_create(
            utilisateur=utilisateur,
            actif=True
        )
        return panier

    @staticmethod
    def add_item_to_cart(
        utilisateur: Utilisateur,
        produit_id: int,
        quantite: int = 1,
        variante_id: int = None,
        option_ids: list = None
    ) -> PanierItem:
        """
        Ajoute un produit au panier actif de l'utilisateur avec validations strictes.
        """
        if quantite < 1:
            raise ValidationError(_("La quantité doit être supérieure ou égale à 1."))

        # 1. Vérification de l'existence et de la disponibilité du produit
        try:
            produit = Produit.objects.select_related('etablissement').get(id=produit_id)
        except Produit.DoesNotExist:
            raise ValidationError(_("Le produit sélectionné n'existe pas."))

        if not produit.est_disponible:
            raise ValidationError(_(f"Le produit '{produit.nom}' n'est pas disponible actuellement."))

        # 2. Vérification du statut de l'établissement
        if produit.etablissement.statut == Etablissement.STATUT_FERME:
            raise ValidationError(_(f"L'établissement '{produit.etablissement.nom}' est actuellement fermé."))

        # 3. Validation de la variante
        variante = None
        if variante_id:
            try:
                variante = VarianteProduit.objects.get(id=variante_id, produit=produit)
            except VarianteProduit.DoesNotExist:
                raise ValidationError(_("La variante sélectionnée est invalide ou n'appartient pas à ce produit."))

        # Vérifier si une variante est requise mais manquante
        variante_requise = produit.variantes.filter(est_requis=True).first()
        if variante_requise and not variante:
            raise ValidationError(_(f"Le choix d'une variante est obligatoire pour le produit '{produit.nom}'."))

        # 4. Validation des options
        valid_options = []
        if option_ids:
            options_qs = OptionProduit.objects.filter(id__in=option_ids, produit=produit)
            if options_qs.count() != len(option_ids):
                raise ValidationError(_("Une ou plusieurs options sélectionnées sont invalides pour ce produit."))
            valid_options = list(options_qs)

        # 5. Récupération du panier et création/mise à jour de l'item
        panier = CartService.get_or_create_active_cart(utilisateur)

        # Vérification si un article identique existe déjà dans le panier (même produit, variante et options identiques)
        existing_items = PanierItem.objects.filter(
            panier=panier,
            produit=produit,
            variante=variante
        )

        target_item = None
        if option_ids:
            sorted_option_ids = sorted([int(oid) for oid in option_ids])
            for item in existing_items:
                item_opt_ids = sorted(list(item.options.values_list('id', flat=True)))
                if item_opt_ids == sorted_option_ids:
                    target_item = item
                    break
        else:
            for item in existing_items:
                if item.options.count() == 0:
                    target_item = item
                    break

        if target_item:
            target_item.quantite += quantite
            target_item.prix_unitaire = produit.prix_base
            target_item.save()
        else:
            target_item = PanierItem.objects.create(
                panier=panier,
                produit=produit,
                quantite=quantite,
                prix_unitaire=produit.prix_base,
                variante=variante
            )
            if valid_options:
                target_item.options.set(valid_options)

        return target_item

    @staticmethod
    def update_item_quantity(utilisateur: Utilisateur, item_id: int, quantite: int) -> PanierItem:
        """
        Met à jour la quantité d'un article du panier.
        """
        if quantite < 1:
            raise ValidationError(_("La quantité doit être supérieure ou égale à 1."))

        panier = CartService.get_or_create_active_cart(utilisateur)
        try:
            item = PanierItem.objects.get(id=item_id, panier=panier)
        except PanierItem.DoesNotExist:
            raise ValidationError(_("L'article demandé n'existe pas dans votre panier."))

        if not item.produit.est_disponible:
            raise ValidationError(_(f"Le produit '{item.produit.nom}' n'est plus disponible."))

        item.quantite = quantite
        item.save()
        return item

    @staticmethod
    def remove_item(utilisateur: Utilisateur, item_id: int):
        """
        Supprime un article du panier.
        """
        panier = CartService.get_or_create_active_cart(utilisateur)
        try:
            item = PanierItem.objects.get(id=item_id, panier=panier)
            item.delete()
        except PanierItem.DoesNotExist:
            raise ValidationError(_("L'article n'existe pas dans votre panier."))

    @staticmethod
    def clear_cart(utilisateur: Utilisateur):
        """
        Vide entièrement le panier actif de l'utilisateur.
        """
        panier = CartService.get_or_create_active_cart(utilisateur)
        panier.items.all().delete()


class OrderService:
    """
    Service de gestion des Commandes et du processus de Checkout.
    """

    @staticmethod
    @transaction.atomic
    def checkout(
        utilisateur: Utilisateur,
        adresse_livraison: str,
        latitude_livraison: float = None,
        longitude_livraison: float = None,
        instructions_livraison: str = '',
        nom_destinataire: str = '',
        telephone_destinataire: str = ''
    ) -> Commande:
        """
        Exécute le checkout de manière atomique :
        - Valide le panier actif et l'absence de panier vide
        - Vérifie la disponibilité des produits
        - Crée la Commande principale
        - Divise et crée les SousCommandes par établissement (Multi-établissements)
        - Crée les LigneCommande et leurs snapshots (variantes et options)
        - Désactive le panier converti et recrée un panier vierge
        """
        panier = CartService.get_or_create_active_cart(utilisateur)
        items = list(panier.items.select_related(
            'produit', 'produit__etablissement', 'variante'
        ).prefetch_related('options').all())

        if not items:
            raise ValidationError(_("Votre panier est vide. Impossible de passer la commande."))

        # Valider les informations destinataire par défaut si non fournies
        if not nom_destinataire:
            nom_destinataire = utilisateur.get_full_name() or "Client AYYOU"
        if not telephone_destinataire:
            telephone_destinataire = utilisateur.numero_telephone

        # 1. Vérification globale de la disponibilité des produits et établissements
        for item in items:
            if not item.produit.est_disponible:
                raise ValidationError(_(f"Le produit '{item.produit.nom}' n'est plus disponible au catalogue."))
            if item.produit.etablissement.statut == Etablissement.STATUT_FERME:
                raise ValidationError(_(f"L'établissement '{item.produit.etablissement.nom}' est actuellement fermé."))

        # 2. Création de la Commande principale
        commande = Commande.objects.create(
            utilisateur=utilisateur,
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('0.00'),
            frais_livraison=Decimal('0.00'),
            total=Decimal('0.00'),
            adresse_livraison=adresse_livraison,
            latitude_livraison=Decimal(str(latitude_livraison)) if latitude_livraison is not None else None,
            longitude_livraison=Decimal(str(longitude_livraison)) if longitude_livraison is not None else None,
            instructions_livraison=instructions_livraison or '',
            nom_destinataire=nom_destinataire,
            telephone_destinataire=telephone_destinataire
        )

        # 3. Regroupement des items par établissement (Multi-établissements)
        items_par_etablissement = {}
        for item in items:
            etab = item.produit.etablissement
            if etab.id not in items_par_etablissement:
                items_par_etablissement[etab.id] = {
                    'etablissement': etab,
                    'items': []
                }
            items_par_etablissement[etab.id]['items'].append(item)

        # 4. Création des SousCommandes et Lignes de Commande avec Snapshots
        sous_total_global = Decimal('0.00')
        frais_livraison_global = Decimal('0.00')

        for etab_id, group in items_par_etablissement.items():
            etablissement = group['etablissement']
            group_items = group['items']

            # Frais de livraison forfaitaire par établissement (ex: 1000 FCFA)
            frais_livraison_etab = Decimal('1000.00')

            sous_commande = SousCommande.objects.create(
                commande=commande,
                etablissement=etablissement,
                statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
                sous_total=Decimal('0.00'),
                frais_livraison=frais_livraison_etab,
                total=Decimal('0.00')
            )

            sous_total_etab = Decimal('0.00')

            for item in group_items:
                prix_unitaire_item = item.calculer_prix_total_unitaire()
                total_ligne_item = prix_unitaire_item * Decimal(str(item.quantite))
                sous_total_etab += total_ligne_item

                ligne = LigneCommande.objects.create(
                    sous_commande=sous_commande,
                    produit=item.produit,
                    nom_produit_snapshot=item.produit.nom,
                    quantite=item.quantite,
                    prix_unitaire=prix_unitaire_item,
                    total_ligne=total_ligne_item
                )

                # Snapshot variante
                if item.variante:
                    LigneCommandeVariante.objects.create(
                        ligne_commande=ligne,
                        variante=item.variante,
                        nom_variante_snapshot=item.variante.titre,
                        prix_supplementaire_snapshot=item.variante.surcout_prix
                    )

                # Snapshot options / suppléments
                for opt in item.options.all():
                    LigneCommandeOption.objects.create(
                        ligne_commande=ligne,
                        option=opt,
                        nom_option_snapshot=opt.titre,
                        type_option_snapshot=opt.type_option,
                        prix_supplementaire_snapshot=opt.surcout_prix
                    )

            sous_commande.sous_total = sous_total_etab
            sous_commande.total = sous_total_etab + frais_livraison_etab
            sous_commande.save(update_fields=['sous_total', 'total'])

            sous_total_global += sous_total_etab
            frais_livraison_global += frais_livraison_etab

        # 5. Mise à jour des totaux globaux de la commande
        commande.sous_total = sous_total_global
        commande.frais_livraison = frais_livraison_global
        commande.total = sous_total_global + frais_livraison_global
        commande.save(update_fields=['sous_total', 'frais_livraison', 'total'])

        # 6. Désactiver le panier converti et libérer un nouveau panier actif
        panier.actif = False
        panier.save(update_fields=['actif'])

        Panier.objects.create(utilisateur=utilisateur, actif=True)

        return commande
