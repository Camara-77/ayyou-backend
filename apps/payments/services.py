from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Commande
from apps.payments.models import Paiement, Facture


class PaymentService:
    """
    Service métier centralisant la logique de paiement et de facturation AYYOU.
    Toutes les opérations financières s'appuient strictement sur les montants calculés par le serveur.
    """

    @staticmethod
    @transaction.atomic
    def initier_paiement(commande: Commande, methode: str) -> Paiement:
        """
        Initialise une transaction de paiement pour une commande donnée.
        Le montant est déterminé strictement à partir du montant total calculé par le serveur.
        """
        if commande.total <= Decimal('0.00'):
            raise ValidationError(_("La commande associée présente un montant invalide."))

        valid_methodes = [m[0] for m in Paiement.CHOIX_METHODES]
        if methode not in valid_methodes:
            raise ValidationError(_("La méthode de paiement sélectionnée est invalide."))

        # Vérifier si un paiement non payé existe déjà ou en créer un nouveau
        paiement_existant = Paiement.objects.filter(
            commande=commande,
            statut__in=[Paiement.STATUT_EN_ATTENTE, Paiement.STATUT_INITIE]
        ).first()

        if paiement_existant:
            paiement_existant.methode = methode
            paiement_existant.statut = Paiement.STATUT_INITIE
            paiement_existant.montant = commande.total
            paiement_existant.save(update_fields=['methode', 'statut', 'montant'])
            return paiement_existant

        paiement = Paiement.objects.create(
            commande=commande,
            montant=commande.total,
            methode=methode,
            statut=Paiement.STATUT_INITIE
        )
        return paiement

    @staticmethod
    @transaction.atomic
    def confirmer_paiement(paiement: Paiement, transaction_externe: str = None) -> Paiement:
        """
        Confirme le paiement de manière atomique :
        1. Valide la transition d'état
        2. Marque le paiement comme PAYE avec la date d'exécution
        3. Met à jour la commande associée et ses sous-commandes vers PAYEE
        4. Génère et lie automatiquement la facture client acquittée
        """
        if paiement.statut == Paiement.STATUT_PAYE:
            return paiement

        if paiement.statut in [Paiement.STATUT_ECHOUE, Paiement.STATUT_EXPIRE, Paiement.STATUT_ANNULE]:
            raise ValidationError(_(f"Transition de statut invalide : impossible de confirmer un paiement {paiement.get_statut_display().lower()}."))

        paiement.statut = Paiement.STATUT_PAYE
        paiement.date_paiement = timezone.now()
        if transaction_externe:
            paiement.transaction_externe = transaction_externe
        paiement.save(update_fields=['statut', 'date_paiement', 'transaction_externe'])

        # Mise à jour de la Commande et des SousCommandes
        commande = paiement.commande
        commande.statut = Commande.STATUT_PAYEE
        commande.save(update_fields=['statut', 'date_modification'])

        commande.sous_commandes.update(statut=Commande.STATUT_PAYEE)

        # Génération ou mise à jour de la Facture
        facture = PaymentService.generer_facture(commande, paiement)
        facture.est_payee = True
        facture.date_paiement = paiement.date_paiement
        facture.paiement = paiement
        facture.save(update_fields=['est_payee', 'date_paiement', 'paiement'])

        # Création d'une Notification Client Idempotente (si non existante)
        if commande.utilisateur:
            from apps.notifications.models import Notification
            notif_ref = str(commande.id)
            deja_notifie = Notification.objects.filter(
                utilisateur=commande.utilisateur,
                reference_type='Commande',
                reference_id=notif_ref,
                type_notification='ORDER'
            ).exists()

            if not deja_notifie:
                code_pin = None
                if hasattr(commande, 'livraison') and commande.livraison and commande.livraison.code_validation:
                    code_pin = commande.livraison.code_validation

                nom_plat = "Commande AYYOU"
                if commande.sous_commandes.exists():
                    sc = commande.sous_commandes.first()
                    if sc.lignes.exists():
                        first_ligne = sc.lignes.first()
                        nom_plat = first_ligne.nom_produit_snapshot or (first_ligne.produit.nom if first_ligne.produit else "Commande AYYOU")

                montant_fmt = f"{int(commande.total):,} FCFA".replace(',', ' ')

                Notification.objects.create(
                    utilisateur=commande.utilisateur,
                    titre="Facture disponible",
                    message=f"Commande {nom_plat} payée — {montant_fmt}",
                    type_notification='ORDER',
                    reference_type='Commande',
                    reference_id=notif_ref,
                    metadata={
                        'commande_id': commande.id,
                        'numero_commande': commande.numero_commande,
                        'montant': float(commande.total),
                        'montant_formate': montant_fmt,
                        'nom_plat': nom_plat,
                        'code_pin': code_pin
                    }
                )

        return paiement

    @staticmethod
    @transaction.atomic
    def echouer_paiement(paiement: Paiement, motif: str = '') -> Paiement:
        """
        Marque une tentative de paiement comme échouée.
        """
        if paiement.statut == Paiement.STATUT_PAYE:
            raise ValidationError(_("Impossible de marquer comme échoué un paiement déjà confirmé et payé."))

        paiement.statut = Paiement.STATUT_ECHOUE
        if motif:
            metadata = paiement.metadata or {}
            metadata['motif_echec'] = motif
            paiement.metadata = metadata
            paiement.save(update_fields=['statut', 'metadata'])
        else:
            paiement.save(update_fields=['statut'])
        return paiement

    @staticmethod
    @transaction.atomic
    def annuler_paiement(paiement: Paiement, motif: str = '') -> Paiement:
        """
        Annule une intention de paiement.
        """
        if paiement.statut == Paiement.STATUT_PAYE:
            raise ValidationError(_("Impossible d'annuler un paiement déjà confirmé et payé."))

        paiement.statut = Paiement.STATUT_ANNULE
        if motif:
            metadata = paiement.metadata or {}
            metadata['motif_annulation'] = motif
            paiement.metadata = metadata
            paiement.save(update_fields=['statut', 'metadata'])
        else:
            paiement.save(update_fields=['statut'])
        return paiement

    @staticmethod
    @transaction.atomic
    def expirer_paiement(paiement: Paiement) -> Paiement:
        """
        Passe une intention de paiement en état expiré.
        """
        if paiement.statut == Paiement.STATUT_PAYE:
            raise ValidationError(_("Impossible d'expirer un paiement déjà confirmé et payé."))

        paiement.statut = Paiement.STATUT_EXPIRE
        paiement.save(update_fields=['statut'])
        return paiement

    @staticmethod
    @transaction.atomic
    def generer_facture(commande: Commande, paiement: Paiement = None) -> Facture:
        """
        Génère une facture immuable avec snapshots d'articles pour une commande.
        """
        details_lignes = []
        for sc in commande.sous_commandes.all():
            for ligne in sc.lignes.all():
                details_lignes.append({
                    'etablissement': sc.etablissement.nom,
                    'produit': ligne.nom_produit_snapshot,
                    'quantite': ligne.quantite,
                    'prix_unitaire': str(ligne.prix_unitaire),
                    'total_ligne': str(ligne.total_ligne)
                })

        facture, created = Facture.objects.get_or_create(
            commande=commande,
            defaults={
                'paiement': paiement,
                'nom_client_snapshot': commande.nom_destinataire or commande.utilisateur.get_full_name(),
                'telephone_client_snapshot': commande.telephone_destinataire or commande.utilisateur.numero_telephone,
                'adresse_livraison_snapshot': commande.adresse_livraison,
                'montant_ht': commande.sous_total,
                'frais_livraison': commande.frais_livraison,
                'montant_total': commande.total,
                'details_lignes_snapshot': details_lignes,
                'est_payee': (paiement.statut == Paiement.STATUT_PAYE) if (paiement and paiement.statut) else False,
                'date_paiement': paiement.date_paiement if (paiement and paiement.statut == Paiement.STATUT_PAYE) else None
            }
        )
        return facture

    @staticmethod
    def ajouter_un_mois_calendaire(dt):
        import calendar
        month = dt.month % 12 + 1
        year = dt.year + (dt.month // 12)
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    @staticmethod
    @transaction.atomic
    def initier_paiement_abonnement(etablissement, methode: str = Paiement.METHODE_WAVE) -> Paiement:

        """
        Initialise une transaction de paiement d'abonnement PRO pour un établissement.
        Le montant est STRICTEMENT imposé à 10 000.00 FCFA côté serveur.
        """
        from apps.catalog.models import Etablissement
        import uuid

        if etablissement.type_etablissement not in [Etablissement.TYPE_RESTAURANT, Etablissement.TYPE_VENDEUR]:
            raise ValidationError(_("Seuls les Restaurants et Vendeurs peuvent souscrire un abonnement PRO."))

        valid_methodes = [m[0] for m in Paiement.CHOIX_METHODES]
        if methode not in valid_methodes:
            raise ValidationError(_("La méthode de paiement sélectionnée est invalide."))

        montant_fixe = Decimal('10000.00')

        # Récupérer un paiement en attente existant ou en créer un nouveau
        paiement_existant = Paiement.objects.filter(
            etablissement=etablissement,
            type_paiement=Paiement.TYPE_ABONNEMENT_PRO,
            statut__in=[Paiement.STATUT_EN_ATTENTE, Paiement.STATUT_INITIE]
        ).first()

        if paiement_existant:
            paiement_existant.methode = methode
            paiement_existant.statut = Paiement.STATUT_INITIE
            paiement_existant.montant = montant_fixe
            paiement_existant.save(update_fields=['methode', 'statut', 'montant'])
            return paiement_existant

        date_str = timezone.now().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        ref = f"SUB-PAY-{date_str}-{suffix}"

        paiement = Paiement.objects.create(
            etablissement=etablissement,
            type_paiement=Paiement.TYPE_ABONNEMENT_PRO,
            reference=ref,
            montant=montant_fixe,
            methode=methode,
            statut=Paiement.STATUT_INITIE
        )
        return paiement

    @staticmethod
    @transaction.atomic
    def confirmer_paiement_abonnement(paiement: Paiement, transaction_externe: str = None) -> Paiement:
        """
        Confirme le paiement d'un abonnement PRO de manière atomique :
        1. Garantit l'idempotence (si déjà PAYE, retourne le paiement).
        2. Calcule les dates (1 mois calendaire) :
           - SI actif (expiration > now) : nouvelle_expiration = date_expiration_actuelle + 1 mois
           - SI expiré / inactif : nouvelle_debut = now, nouvelle_expiration = now + 1 mois
        3. Met à jour l'Etablissement (statut_abonnement = ACTIF, dates d'abonnement).
        4. Crée AbonnementPro et FactureAbonnement.
        5. Déclenche l'email d'activation/renouvellement.
        """
        from apps.catalog.models import Etablissement
        from apps.payments.models import AbonnementPro, FactureAbonnement
        from apps.notifications.email_service import EmailNotificationService

        if paiement.statut == Paiement.STATUT_PAYE:
            return paiement

        if paiement.type_paiement != Paiement.TYPE_ABONNEMENT_PRO or not paiement.etablissement:
            raise ValidationError(_("Ce paiement n'est pas un paiement d'abonnement PRO valide."))

        now = timezone.now()
        etablissement = paiement.etablissement

        # Déterminer la nouvelle plage de dates d'abonnement (1 mois calendaire)
        if etablissement.statut_abonnement == Etablissement.STATUT_ABONNEMENT_ACTIF and etablissement.date_expiration_abonnement and etablissement.date_expiration_abonnement > now:
            nouvelle_debut = etablissement.date_debut_abonnement or now
            nouvelle_expiration = PaymentService.ajouter_un_mois_calendaire(etablissement.date_expiration_abonnement)
        else:
            nouvelle_debut = now
            nouvelle_expiration = PaymentService.ajouter_un_mois_calendaire(now)

        paiement.statut = Paiement.STATUT_PAYE
        paiement.date_paiement = now
        if transaction_externe:
            paiement.transaction_externe = transaction_externe
        paiement.save(update_fields=['statut', 'date_paiement', 'transaction_externe'])

        # Mise à jour de l'Établissement
        etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_ACTIF
        etablissement.date_debut_abonnement = nouvelle_debut
        etablissement.date_expiration_abonnement = nouvelle_expiration
        etablissement.save(update_fields=['statut_abonnement', 'date_debut_abonnement', 'date_expiration_abonnement'])

        # Création ou récupération de l'AbonnementPro (Idempotence)
        abonnement_pro, created = AbonnementPro.objects.get_or_create(
            paiement=paiement,
            defaults={
                'etablissement': etablissement,
                'montant': paiement.montant,
                'date_debut': nouvelle_debut,
                'date_expiration': nouvelle_expiration,
                'statut': AbonnementPro.STATUT_PAYE
            }
        )

        # Création de la FactureAbonnement PRO
        if created or not hasattr(abonnement_pro, 'facture'):
            proprietaire = etablissement.proprietaire
            FactureAbonnement.objects.create(
                abonnement=abonnement_pro,
                etablissement=etablissement,
                nom_etablissement_snapshot=etablissement.nom,
                type_etablissement_snapshot=etablissement.get_type_etablissement_display(),
                nom_proprietaire_snapshot=proprietaire.get_full_name() if proprietaire else "Partenaire AYYOU",
                email_proprietaire_snapshot=proprietaire.email if proprietaire else "",
                montant_ht=paiement.montant,
                montant_total=paiement.montant
            )

        # Déclencher l'email de confirmation d'abonnement
        EmailNotificationService.send_subscription_confirmation_email(abonnement_pro)

        # Déclencher la notification In-App d'activation/réactivation d'abonnement
        if proprietaire:
            from apps.notifications.models import Notification
            date_exp_str = nouvelle_expiration.strftime('%d/%m/%Y à %H:%M')
            Notification.objects.create(
                utilisateur=proprietaire,
                type_notification=Notification.TYPE_SUBSCRIPTION,
                canal=Notification.CANAL_IN_APP,
                titre=f"Abonnement PRO activé — {etablissement.nom}",
                message=f"Votre abonnement PRO AYYOU est désormais ACTIF jusqu'au {date_exp_str}. Votre établissement, vos produits et vos vidéos sont de nouveau visibles du public.",
                statut=Notification.STATUT_ENVOYEE,
                reference_type='AbonnementPro',
                reference_id=str(abonnement_pro.id),
                metadata={
                    'event': 'PRO_SUBSCRIPTION_CONFIRMED',
                    'etablissement_id': etablissement.id,
                    'etablissement_nom': etablissement.nom,
                    'date_expiration': date_exp_str
                }
            )

        return paiement


