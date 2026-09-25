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
                titre="Paiement confirmé"
            ).exists()

            if not deja_notifie:
                Notification.objects.create(
                    utilisateur=commande.utilisateur,
                    titre="Paiement confirmé",
                    message=f"Votre paiement pour la commande #{commande.numero_commande} a été confirmé.",
                    type_notification='ORDER',
                    reference_type='Commande',
                    reference_id=notif_ref
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
