from django.utils import timezone
from django.db.models import Sum, Q, Count
from decimal import Decimal

from apps.users.models import Utilisateur, ProfilLivreur
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.orders.models import Commande
from apps.deliveries.models import Livraison
from apps.payments.models import Paiement
from apps.admin_panel.models import AuditLog


class AdminDashboardService:
    @staticmethod
    def get_kpis():
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        total_utilisateurs = Utilisateur.objects.count()
        restaurants = Etablissement.objects.filter(type_etablissement=Etablissement.TYPE_RESTAURANT).count()
        vendeurs = Etablissement.objects.filter(type_etablissement=Etablissement.TYPE_VENDEUR).count()
        livreurs = ProfilLivreur.objects.count()
        livreurs_disponibles = ProfilLivreur.objects.filter(
            est_disponible=True,
            statut_verification=ProfilLivreur.STATUT_VALIDE
        ).count()

        commandes_jour = Commande.objects.filter(date_creation__gte=today_start).count()
        livraisons_actives = Livraison.objects.exclude(
            statut__in=[Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]
        ).count()

        gmv_query = Commande.objects.filter(
            date_creation__gte=today_start,
            paiements__statut=Paiement.STATUT_PAYE
        ).aggregate(total_gmv=Sum('total'))
        gmv_jour = gmv_query['total_gmv'] or Decimal('0.00')

        pending_etablissements = Etablissement.objects.filter(est_verifie=False).count()
        pending_livreurs = ProfilLivreur.objects.filter(statut_verification=ProfilLivreur.STATUT_EN_ATTENTE).count()
        dossiers_en_attente = pending_etablissements + pending_livreurs

        return {
            'total_utilisateurs': total_utilisateurs,
            'restaurants': restaurants,
            'vendeurs': vendeurs,
            'livreurs': livreurs,
            'livreurs_disponibles': livreurs_disponibles,
            'commandes_jour': commandes_jour,
            'livraisons_actives': livraisons_actives,
            'gmv_jour': float(gmv_jour),
            'dossiers_en_attente': dossiers_en_attente,
            'details_dossiers': {
                'etablissements_non_verifies': pending_etablissements,
                'livreurs_en_attente': pending_livreurs,
            }
        }

    @staticmethod
    def get_pending_actions():
        pending_etablissements = Etablissement.objects.filter(est_verifie=False)[:20]
        pending_livreurs = ProfilLivreur.objects.filter(statut_verification=ProfilLivreur.STATUT_EN_ATTENTE)[:20]

        etablissements_data = [
            {
                'id': e.id,
                'type': 'ETABISSEMENT',
                'type_etablissement': e.type_etablissement,
                'nom': e.nom,
                'proprietaire': e.proprietaire.get_full_name() if e.proprietaire else None,
                'email': e.proprietaire.email if e.proprietaire else None,
                'date_creation': e.date_creation,
            }
            for e in pending_etablissements
        ]

        livreurs_data = [
            {
                'id': l.id,
                'type': 'LIVREUR',
                'nom': l.utilisateur.get_full_name(),
                'email': l.utilisateur.email,
                'telephone': l.utilisateur.numero_telephone,
                'type_vehicule': l.type_vehicule,
                'date_creation': l.date_creation,
            }
            for l in pending_livreurs
        ]

        return {
            'etablissements_en_attente': etablissements_data,
            'livreurs_en_attente': livreurs_data,
        }


class AdminAuditService:
    @staticmethod
    def log_action(request, action, ressource, resource_id='', statut=AuditLog.STATUT_SUCCESS, details=None):
        if details is None:
            details = {}

        # SÉCURITÉ : Nettoyer tout mot de passe, secret OTP, token JWT du dictionnaire de détails
        sanitized_details = {}
        if isinstance(details, dict):
            for k, v in details.items():
                if any(secret_key in k.lower() for secret_key in ['password', 'token', 'otp', 'secret', 'auth']):
                    sanitized_details[k] = '[CONFIDENTIAL]'
                else:
                    sanitized_details[k] = v

        ip_address = None
        user = None
        user_email = ''

        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')

            if hasattr(request, 'user') and request.user and request.user.is_authenticated:
                user = request.user
                user_email = request.user.email

        AuditLog.objects.create(
            administrateur=user,
            admin_email=user_email,
            action=action,
            ressource=ressource,
            resource_id=str(resource_id),
            ip_address=ip_address,
            statut=statut,
            details=sanitized_details,
        )
