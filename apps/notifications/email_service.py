import os
import logging
from typing import Optional
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction

from .models import Notification
from apps.catalog.models import Etablissement
from apps.users.models import ProfilLivreur

logger = logging.getLogger('apps.notifications')


class EmailNotificationService:
    """
    Service d'envoi d'emails transactionnels pour AYYOU.
    Reçoit un objet Notification (canal EMAIL), construit le contenu HTML et Texte,
    et expédie l'email via le service de messagerie Django (EmailMultiAlternatives).
    Découplé des modèles métier (commandes, livraisons, etc.).
    """

    DEFAULT_HTML_TEMPLATE = 'notifications/emails/base_notification.html'
    DEFAULT_TXT_TEMPLATE = 'notifications/emails/base_notification.txt'

    @classmethod
    def envoyer_email_notification(cls, notification: Notification) -> bool:
        """
        Envoie un email pour une notification donnée si son canal est EMAIL.
        Mets à jour le statut de la notification (STATUT_ENVOYEE ou STATUT_ECHEC).
        Retourne True si l'email a été envoyé avec succès, False sinon.
        Ne lève pas d'exception pour garantir la résilience du système.
        """
        if notification.canal != Notification.CANAL_EMAIL:
            logger.info(f"[EMAIL SERVICE] Ignoré: La notification #{notification.id} utilise le canal '{notification.canal}' (requis: '{Notification.CANAL_EMAIL}').")
            return False

        destinataire = notification.utilisateur
        recipient_email = getattr(destinataire, 'email', None)

        if not recipient_email or not str(recipient_email).strip():
            logger.warning(f"[EMAIL SERVICE] Échec: Adresse email manquante ou invalide pour le destinataire de la notification #{notification.id}.")
            notification.statut = Notification.STATUT_ECHEC
            notification.save(update_fields=['statut', 'updated_at'])
            return False

        destinataire_nom = destinataire.get_full_name() if hasattr(destinataire, 'get_full_name') else ''
        if not destinataire_nom or not destinataire_nom.strip():
            destinataire_nom = recipient_email

        context = {
            'titre': notification.titre,
            'message': notification.message,
            'reference_type': notification.reference_type,
            'reference_id': notification.reference_id,
            'destinataire_nom': destinataire_nom,
            'metadata': notification.metadata or {},
        }

        try:
            html_content = render_to_string(cls.DEFAULT_HTML_TEMPLATE, context)
            text_content = render_to_string(cls.DEFAULT_TXT_TEMPLATE, context)

            subject = notification.titre
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'AYYOU <no-reply@ayyou.com>')

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            msg.attach_alternative(html_content, "text/html")

            msg.send(fail_silently=False)

            notification.statut = Notification.STATUT_ENVOYEE
            notification.save(update_fields=['statut', 'updated_at'])

            logger.info(f"[EMAIL SERVICE] Email envoyé avec succès pour la notification #{notification.id} à {recipient_email}")
            return True

        except Exception as e:
            # Sécurité : aucun mot de passe SMTP, secret ou token n'est inscrit dans les logs
            logger.error(f"[EMAIL SERVICE] Erreur d'envoi pour notification #{notification.id}: {type(e).__name__} - {str(e)}")
            notification.statut = Notification.STATUT_ECHEC
            notification.save(update_fields=['statut', 'updated_at'])
            return False

    @classmethod
    def dispatch_email_on_commit(cls, notification: Notification) -> None:
        """
        Déclenche l'envoi d'email après le commit de la transaction SQL (transaction.on_commit).
        Si aucune transaction atomique n'est active, l'envoi s'exécute immédiatement.
        """
        if transaction.get_connection().in_atomic_block:
            transaction.on_commit(lambda: cls.envoyer_email_notification(notification))
        else:
            cls.envoyer_email_notification(notification)

    @classmethod
    def send_pro_approval_email_for_etablissement(cls, etablissement: Etablissement) -> Optional[Notification]:
        """
        Génère et déclenche l'email de validation de compte pour un Restaurant ou Vendeur à domicile.
        """
        proprietaire = etablissement.proprietaire
        if not proprietaire:
            logger.warning(f"[EMAIL SERVICE] Impossible d'envoyer l'email d'approbation : Etablissement #{etablissement.id} sans propriétaire.")
            return None

        prenom = proprietaire.prenom or proprietaire.get_full_name() or etablissement.nom
        frontend_base = os.getenv('AYYOU_PRO_URL', os.getenv('FRONTEND_URL', 'http://localhost:4200')).rstrip('/')
        if etablissement.type_etablissement == Etablissement.TYPE_VENDEUR:
            type_label = "Vendeur à domicile"
            login_url = f"{frontend_base}/vendeur/login"
        else:
            type_label = "Restaurant"
            login_url = f"{frontend_base}/pro/login"

        titre = "Bienvenue chez AYYOU — Votre candidature est acceptée"
        message = (
            f"Bonjour {prenom},\n\n"
            f"Nous avons le plaisir de vous annoncer que votre candidature pour l'établissement « {etablissement.nom} » ({type_label}) a été acceptée.\n\n"
            f"Bienvenue dans la grande famille AYYOU.\n\n"
            f"Vous pouvez maintenant accéder à votre espace professionnel avec l'adresse email et le mot de passe utilisés lors de votre inscription :\n"
            f"{login_url}\n\n"
            f"Cordialement,\n"
            f"L'équipe AYYOU"
        )

        notification = Notification.objects.create(
            utilisateur=proprietaire,
            type_notification=Notification.TYPE_PRO_VALIDATION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='Etablissement',
            reference_id=str(etablissement.id),
            metadata={
                'event': 'PRO_ACCOUNT_APPROVED',
                'type': etablissement.type_etablissement,
                'name': etablissement.nom,
                'login_url': login_url
            }
        )
        cls.dispatch_email_on_commit(notification)
        from apps.notifications.n8n_service import N8nNotificationService
        N8nNotificationService.send_pro_approval_for_etablissement(etablissement)
        return notification

    @classmethod
    def send_pro_rejection_email_for_etablissement(cls, etablissement: Etablissement, motif: str) -> Optional[Notification]:
        """
        Génère et déclenche l'email de refus de compte pour un Restaurant ou Vendeur à domicile.
        """
        proprietaire = etablissement.proprietaire
        if not proprietaire:
            logger.warning(f"[EMAIL SERVICE] Impossible d'envoyer l'email de refus : Etablissement #{etablissement.id} sans propriétaire.")
            return None

        prenom = proprietaire.prenom or proprietaire.get_full_name() or etablissement.nom
        motif_clean = (motif or 'Dossier non conforme').strip()

        titre = "AYYOU — Mise à jour de votre candidature"
        message = (
            f"Bonjour {prenom},\n\n"
            f"Nous avons examiné votre dossier d'inscription pour l'établissement « {etablissement.nom} » à AYYOU.\n\n"
            f"Après vérification, nous ne pouvons malheureusement pas valider votre candidature pour le moment.\n\n"
            f"Motif :\n"
            f"{motif_clean}\n\n"
            f"Nous vous invitons à corriger les éléments concernés et à soumettre à nouveau les documents nécessaires.\n\n"
            f"Cordialement,\n\n"
            f"L'équipe AYYOU"
        )

        notification = Notification.objects.create(
            utilisateur=proprietaire,
            type_notification=Notification.TYPE_PRO_VALIDATION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='Etablissement',
            reference_id=str(etablissement.id),
            metadata={
                'event': 'PRO_ACCOUNT_REJECTED',
                'type': etablissement.type_etablissement,
                'name': etablissement.nom,
                'motif': motif_clean
            }
        )
        cls.dispatch_email_on_commit(notification)
        from apps.notifications.n8n_service import N8nNotificationService
        N8nNotificationService.send_pro_rejection_for_etablissement(etablissement, motif_clean)
        return notification

    @classmethod
    def send_pro_approval_email_for_driver(cls, driver: ProfilLivreur) -> Optional[Notification]:
        """
        Génère et déclenche l'email de validation de compte pour un Livreur.
        """
        utilisateur = driver.utilisateur
        if not utilisateur:
            logger.warning(f"[EMAIL SERVICE] Impossible d'envoyer l'email d'approbation : Livreur #{driver.id} sans utilisateur.")
            return None

        driver_name = utilisateur.get_full_name() or utilisateur.email
        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        login_url = f"{frontend_base}/delivery/login"

        titre = "Félicitations ! Votre compte Livreur AYYOU a été validé"
        message = (
            f"Bonjour {driver_name},\n\n"
            f"Nous avons le plaisir de vous informer que votre profil de livreur partenaire AYYOU "
            f"a été vérifié et validé avec succès.\n\n"
            f"Vous pouvez dès à présent vous connecter à votre espace livreur pour commencer à recevoir des courses :\n"
            f"{login_url}\n\n"
            f"Bienvenue dans l'équipe des livreurs AYYOU !"
        )

        notification = Notification.objects.create(
            utilisateur=utilisateur,
            type_notification=Notification.TYPE_PRO_VALIDATION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='ProfilLivreur',
            reference_id=str(driver.id),
            metadata={
                'event': 'PRO_ACCOUNT_APPROVED',
                'type': 'LIVREUR',
                'name': driver_name,
                'login_url': login_url
            }
        )
        cls.dispatch_email_on_commit(notification)
        from apps.notifications.n8n_service import N8nNotificationService
        N8nNotificationService.send_pro_approval_for_driver(driver)
        return notification

    @classmethod
    def send_pro_rejection_email_for_driver(cls, driver: ProfilLivreur, motif: str) -> Optional[Notification]:
        """
        Génère et déclenche l'email de refus de compte pour un Livreur.
        """
        utilisateur = driver.utilisateur
        if not utilisateur:
            logger.warning(f"[EMAIL SERVICE] Impossible d'envoyer l'email de refus : Livreur #{driver.id} sans utilisateur.")
            return None

        driver_name = utilisateur.get_full_name() or utilisateur.email
        motif_clean = (motif or 'Dossier non conforme').strip()

        titre = "Information concernant votre demande de compte Livreur AYYOU"
        message = (
            f"Bonjour {driver_name},\n\n"
            f"Nous avons examiné votre dossier de candidature pour devenir livreur partenaire AYYOU.\n\n"
            f"Malheureusement, votre profil n'a pas pu être validé pour le motif suivant :\n"
            f"« {motif_clean} »\n\n"
            f"Vous pouvez réviser vos documents ou contacter l'équipe support pour toute question."
        )

        notification = Notification.objects.create(
            utilisateur=utilisateur,
            type_notification=Notification.TYPE_PRO_VALIDATION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='ProfilLivreur',
            reference_id=str(driver.id),
            metadata={
                'event': 'PRO_ACCOUNT_REJECTED',
                'type': 'LIVREUR',
                'name': driver_name,
                'motif': motif_clean
            }
        )
        cls.dispatch_email_on_commit(notification)
        from apps.notifications.n8n_service import N8nNotificationService
        N8nNotificationService.send_pro_rejection_for_driver(driver, motif_clean)
        return notification

    @classmethod
    def send_subscription_confirmation_email(cls, abonnement) -> Optional[Notification]:
        """
        Envoyer un email de confirmation d'activation ou renouvellement d'abonnement PRO.
        """
        etablissement = abonnement.etablissement
        proprietaire = etablissement.proprietaire
        if not proprietaire:
            logger.warning(f"[EMAIL SERVICE] Etablissement #{etablissement.id} sans propriétaire pour email abonnement.")
            return None

        date_exp_str = abonnement.date_expiration.strftime('%d/%m/%Y à %H:%M') if abonnement.date_expiration else ''
        ref_tx = abonnement.paiement.reference if abonnement.paiement else 'N/A'
        titre = f"Confirmation d'abonnement PRO AYYOU — {etablissement.nom}"
        message = (
            f"Bonjour {etablissement.nom},\n\n"
            f"Votre paiement d'abonnement PRO AYYOU de {abonnement.montant:,.0f} FCFA a été confirmé avec succès.\n\n"
            f"Détails de l'abonnement :\n"
            f"- Établissement : {etablissement.nom}\n"
            f"- Statut : ACTIF\n"
            f"- Période : du {abonnement.date_debut.strftime('%d/%m/%Y')} au {date_exp_str}\n"
            f"- Référence transaction : {ref_tx}\n\n"
            f"Votre établissement, vos produits et vos vidéos sont désormais visibles sur la plateforme AYYOU.\n\n"
            f"Merci de votre confiance !"
        )


        notification = Notification.objects.create(
            utilisateur=proprietaire,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='AbonnementPro',
            reference_id=str(abonnement.id),
            metadata={
                'event': 'PRO_SUBSCRIPTION_CONFIRMED',
                'etablissement_id': etablissement.id,
                'etablissement_nom': etablissement.nom,
                'montant': str(abonnement.montant),
                'date_expiration': date_exp_str
            }
        )

        cls.dispatch_email_on_commit(notification)
        return notification

    @classmethod
    def send_subscription_expiration_reminder_email(cls, etablissement: Etablissement, days_remaining: int = 5) -> Optional[Notification]:
        """
        Envoyer un email de rappel d'expiration d'abonnement (J-5 ou J-1 / 24 heures).
        """
        proprietaire = etablissement.proprietaire
        if not proprietaire:
            logger.warning(f"[EMAIL SERVICE] Etablissement #{etablissement.id} sans propriétaire pour rappel abonnement.")
            return None

        date_exp_str = etablissement.date_expiration_abonnement.strftime('%d/%m/%Y à %H:%M') if etablissement.date_expiration_abonnement else ''
        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        renew_url = f"{frontend_base}/pro/subscription"

        delai_str = "demain (dans 24h)" if days_remaining == 1 else f"dans {days_remaining} jours"
        titre = f"Rappel : Votre abonnement PRO AYYOU expire {delai_str} — {etablissement.nom}"
        message = (
            f"Bonjour {etablissement.nom},\n\n"
            f"Votre abonnement PRO AYYOU pour l'établissement « {etablissement.nom} » arrivera à expiration le {date_exp_str}.\n\n"
            f"Afin d'éviter toute interruption de la visibilité de votre établissement, de vos produits et de vos vidéos sur AYYOU, "
            f"ainsi que le blocage des nouvelles commandes, nous vous invitons à renouveler votre abonnement mensuel (10 000 FCFA) depuis votre espace PRO :\n"
            f"{renew_url}\n\n"
            f"Merci de faire partie de la communauté AYYOU !"
        )

        notification = Notification.objects.create(
            utilisateur=proprietaire,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='Etablissement',
            reference_id=str(etablissement.id),
            metadata={
                'event': f'PRO_SUBSCRIPTION_REMINDER_J{days_remaining}',
                'etablissement_id': etablissement.id,
                'etablissement_nom': etablissement.nom,
                'date_expiration': date_exp_str,
                'renew_url': renew_url,
                'days_remaining': days_remaining
            }
        )
        cls.dispatch_email_on_commit(notification)
        return notification

    @classmethod
    def send_subscription_suspension_email(cls, etablissement: Etablissement) -> Optional[Notification]:
        """
        Envoyer un email de notification de suspension lorsque l'abonnement PRO est expiré.
        """
        proprietaire = etablissement.proprietaire
        if not proprietaire:
            logger.warning(f"[EMAIL SERVICE] Etablissement #{etablissement.id} sans propriétaire pour email suspension.")
            return None

        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        renew_url = f"{frontend_base}/pro/subscription"

        titre = f"Avis de suspension : Votre abonnement PRO AYYOU a expiré — {etablissement.nom}"
        message = (
            f"Bonjour {etablissement.nom},\n\n"
            f"Nous vous informons que votre abonnement PRO AYYOU pour l'établissement « {etablissement.nom} » a expiré.\n\n"
            f"Conséquences de la suspension :\n"
            f"- Votre établissement et vos produits ne sont plus visibles par les clients sur la plateforme.\n"
            f"- Vos vidéos du Feed AYYOU sont masquées.\n"
            f"- La création et la modification de vos plats/menus sont suspendues.\n"
            f"- Vous ne pouvez plus recevoir de nouvelles commandes.\n\n"
            f"Pour réactiver instantanément votre compte et restaurer l'ensemble de vos fonctionnalités, vous pouvez renouveler votre abonnement mensuel (10 000 FCFA) en 1 clic via PayTech :\n"
            f"{renew_url}\n\n"
            f"L'équipe AYYOU reste à votre disposition."
        )

        notification = Notification.objects.create(
            utilisateur=proprietaire,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            canal=Notification.CANAL_EMAIL,
            titre=titre,
            message=message,
            statut=Notification.STATUT_EN_ATTENTE,
            reference_type='Etablissement',
            reference_id=str(etablissement.id),
            metadata={
                'event': 'PRO_SUBSCRIPTION_SUSPENDED',
                'etablissement_id': etablissement.id,
                'etablissement_nom': etablissement.nom,
                'renew_url': renew_url
            }
        )
        cls.dispatch_email_on_commit(notification)
        return notification


