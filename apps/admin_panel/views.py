from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.users.models import Utilisateur, ProfilLivreur, Role, UtilisateurRole, DocumentLivreur
from apps.catalog.models import Etablissement, Produit, Categorie, DocumentEtablissement
from apps.orders.models import Commande
from apps.deliveries.models import Livraison
from apps.payments.models import Paiement
from apps.admin_panel.models import AuditLog
from apps.admin_panel.permissions import IsSuperAdmin
from apps.admin_panel.serializers import (
    AdminUserSerializer,
    AdminDriverSerializer,
    AdminBusinessSerializer,
    AdminCategorySerializer,
    AdminCatalogProductSerializer,
    AdminOrderSerializer,
    AdminDeliverySerializer,
    AdminPaymentSerializer,
    AuditLogSerializer,
)
from apps.admin_panel.services import AdminDashboardService, AdminAuditService
from apps.notifications.n8n_service import N8nNotificationService


class AdminDashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        kpis = AdminDashboardService.get_kpis()
        return Response(kpis, status=status.HTTP_200_OK)


class AdminPendingActionsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        actions = AdminDashboardService.get_pending_actions()
        return Response(actions, status=status.HTTP_200_OK)


class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserSerializer
    queryset = Utilisateur.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        est_actif = self.request.query_params.get('est_actif')
        role = self.request.query_params.get('role')

        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(nom__icontains=search) |
                Q(prenom__icontains=search) |
                Q(numero_telephone__icontains=search)
            )
        if est_actif is not None:
            is_active_bool = est_actif.lower() in ('true', '1')
            qs = qs.filter(est_actif=is_active_bool)
        if role:
            qs = qs.filter(roles_attribues__role__nom__iexact=role)
        return qs.distinct()

    @action(detail=True, methods=['patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        user.est_actif = not user.est_actif
        user.save(update_fields=['est_actif'])

        status_str = "ACTIVATION" if user.est_actif else "DESACTIVATION"
        AdminAuditService.log_action(
            request=request,
            action=f"TOGGLE_USER_STATUS_{status_str}",
            ressource="Utilisateur",
            resource_id=user.id,
            details={'est_actif': user.est_actif, 'user_email': user.email}
        )
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-role')
    @transaction.atomic
    def assign_role(self, request, pk=None):
        user = self.get_object()
        role_nom = request.data.get('role')
        if not role_nom:
            return Response({'error': 'Le paramètre role est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role_obj, _ = Role.objects.get_or_create(nom=role_nom.upper())
            UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_obj)
            AdminAuditService.log_action(
                request=request,
                action="ASSIGN_USER_ROLE",
                ressource="Utilisateur",
                resource_id=user.id,
                details={'role_attribue': role_nom}
            )
            return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminBusinessViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminBusinessSerializer
    queryset = Etablissement.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        type_etab = self.request.query_params.get('type_etablissement')
        est_verifie = self.request.query_params.get('est_verifie')
        statut_verif = self.request.query_params.get('statut_verification')

        if search:
            qs = qs.filter(Q(nom__icontains=search) | Q(adresse__icontains=search) | Q(telephone__icontains=search))
        if type_etab:
            qs = qs.filter(type_etablissement__iexact=type_etab)
        if est_verifie is not None:
            verifie_bool = est_verifie.lower() in ('true', '1')
            qs = qs.filter(est_verifie=verifie_bool)
        if statut_verif:
            qs = qs.filter(statut_verification__iexact=statut_verif)
        return qs

    @action(detail=True, methods=['patch'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        etablissement = self.get_object()
        ancien_statut = etablissement.statut_verification

        etablissement.statut_verification = Etablissement.STATUT_VALIDE
        etablissement.est_verifie = True
        etablissement.save(update_fields=['statut_verification', 'est_verifie'])

        # Synchroniser les documents EN_ATTENTE -> VALIDE
        etablissement.documents.filter(
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        ).update(statut=DocumentEtablissement.STATUT_VALIDE)

        AdminAuditService.log_action(
            request=request,
            action="APPROVE_BUSINESS",
            ressource="Etablissement",
            resource_id=etablissement.id,
            details={'nom': etablissement.nom, 'type': etablissement.type_etablissement}
        )

        # Déclenchement n8n uniquement lors de la transition vers VALIDE
        if ancien_statut != Etablissement.STATUT_VALIDE:
            transaction.on_commit(
                lambda: N8nNotificationService.send_pro_approval_for_etablissement(etablissement)
            )

        return Response(AdminBusinessSerializer(etablissement).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='reject')
    @transaction.atomic
    def reject(self, request, pk=None):
        etablissement = self.get_object()
        etablissement.statut_verification = Etablissement.STATUT_REFUSE
        etablissement.est_verifie = False
        etablissement.save(update_fields=['statut_verification', 'est_verifie'])

        # Synchroniser les documents EN_ATTENTE -> REFUSE
        etablissement.documents.filter(
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        ).update(statut=DocumentEtablissement.STATUT_REFUSE)

        motif = request.data.get('motif', '')

        AdminAuditService.log_action(
            request=request,
            action="REJECT_BUSINESS",
            ressource="Etablissement",
            resource_id=etablissement.id,
            details={'nom': etablissement.nom, 'motif': motif}
        )

        transaction.on_commit(
            lambda: N8nNotificationService.send_pro_rejection_for_etablissement(etablissement, motif)
        )

        return Response(AdminBusinessSerializer(etablissement).data, status=status.HTTP_200_OK)


class AdminDriverViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminDriverSerializer
    queryset = ProfilLivreur.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        statut_verif = self.request.query_params.get('statut_verification')
        type_veh = self.request.query_params.get('type_vehicule')

        if search:
            qs = qs.filter(
                Q(utilisateur__nom__icontains=search) |
                Q(utilisateur__prenom__icontains=search) |
                Q(utilisateur__email__icontains=search) |
                Q(utilisateur__numero_telephone__icontains=search)
            )
        if statut_verif:
            qs = qs.filter(statut_verification__iexact=statut_verif)
        if type_veh:
            qs = qs.filter(type_vehicule__iexact=type_veh)
        return qs

    @action(detail=True, methods=['patch'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        driver = self.get_object()
        ancien_statut = driver.statut_verification

        driver.statut_verification = ProfilLivreur.STATUT_VALIDE
        driver.full_clean()
        driver.save(update_fields=['statut_verification'])

        # Synchroniser les documents EN_ATTENTE -> VALIDE
        driver.documents.filter(
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        ).update(statut=DocumentLivreur.STATUT_VALIDE)

        AdminAuditService.log_action(
            request=request,
            action="APPROVE_DRIVER",
            ressource="ProfilLivreur",
            resource_id=driver.id,
            details={'driver_name': driver.utilisateur.get_full_name()}
        )

        # Déclenchement n8n uniquement lors de la transition vers VALIDE
        if ancien_statut != ProfilLivreur.STATUT_VALIDE:
            transaction.on_commit(
                lambda: N8nNotificationService.send_pro_approval_for_driver(driver)
            )

        return Response(AdminDriverSerializer(driver).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='reject')
    @transaction.atomic
    def reject(self, request, pk=None):
        driver = self.get_object()
        motif = request.data.get('motif', 'Dossier non conforme')
        driver.statut_verification = ProfilLivreur.STATUT_REFUSE
        driver.est_disponible = False
        driver.save(update_fields=['statut_verification', 'est_disponible'])

        # Synchroniser les documents EN_ATTENTE -> REFUSE
        driver.documents.filter(
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        ).update(statut=DocumentLivreur.STATUT_REFUSE)

        AdminAuditService.log_action(
            request=request,
            action="REJECT_DRIVER",
            ressource="ProfilLivreur",
            resource_id=driver.id,
            details={'driver_name': driver.utilisateur.get_full_name(), 'motif': motif}
        )

        transaction.on_commit(
            lambda: N8nNotificationService.send_pro_rejection_for_driver(driver, motif)
        )

        return Response(AdminDriverSerializer(driver).data, status=status.HTTP_200_OK)


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminOrderSerializer
    queryset = Commande.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        statut_cmd = self.request.query_params.get('statut')

        if search:
            qs = qs.filter(
                Q(numero_commande__icontains=search) |
                Q(utilisateur__nom__icontains=search) |
                Q(nom_destinataire__icontains=search)
            )
        if statut_cmd:
            qs = qs.filter(statut__iexact=statut_cmd)
        return qs

    @action(detail=True, methods=['patch'], url_path='status')
    def update_order_status(self, request, pk=None):
        commande = self.get_object()
        nouveau_statut = request.data.get('statut')
        if not nouveau_statut:
            return Response({'error': 'Le paramètre statut est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        ancien_statut = commande.statut
        commande.statut = nouveau_statut
        commande.save(update_fields=['statut'])

        AdminAuditService.log_action(
            request=request,
            action="UPDATE_ORDER_STATUS",
            ressource="Commande",
            resource_id=commande.id,
            details={'numero_commande': commande.numero_commande, 'ancien': ancien_statut, 'nouveau': nouveau_statut}
        )
        return Response(AdminOrderSerializer(commande).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign-driver')
    @transaction.atomic
    def assign_driver(self, request, pk=None):
        commande = self.get_object()
        driver_id = request.data.get('driver_id')
        if not driver_id:
            return Response({'error': 'driver_id est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        driver = get_object_or_404(ProfilLivreur, pk=driver_id)
        if driver.statut_verification != ProfilLivreur.STATUT_VALIDE:
            return Response({'error': 'Livreur non validé.'}, status=status.HTTP_400_BAD_REQUEST)
        if not hasattr(commande, 'livraison') or not commande.livraison:
            return Response({'error': 'Aucune livraison associée à cette commande.'}, status=status.HTTP_400_BAD_REQUEST)

        livraison = commande.livraison
        livraison.livreur = driver
        livraison.statut = Livraison.STATUT_AFFECTEE
        livraison.save(update_fields=['livreur', 'statut'])

        AdminAuditService.log_action(
            request=request,
            action="MANUAL_ASSIGN_DRIVER",
            ressource="Livraison",
            resource_id=livraison.id,
            details={'commande_numero': commande.numero_commande, 'driver_id': driver.id}
        )
        return Response(AdminOrderSerializer(commande).data, status=status.HTTP_200_OK)


class AdminDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminDeliverySerializer
    queryset = Livraison.objects.all().order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        statut_livr = self.request.query_params.get('statut')
        if statut_livr:
            qs = qs.filter(statut__iexact=statut_livr)
        return qs

    @action(detail=True, methods=['post'], url_path='close-incident')
    def close_incident(self, request, pk=None):
        livraison = self.get_object()
        resolution = request.data.get('resolution', 'Incident résolu par le Super Admin')

        AdminAuditService.log_action(
            request=request,
            action="CLOSE_DELIVERY_INCIDENT",
            ressource="Livraison",
            resource_id=livraison.id,
            details={'commande_numero': livraison.commande.numero_commande, 'resolution': resolution}
        )
        return Response(AdminDeliverySerializer(livraison).data, status=status.HTTP_200_OK)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminCategorySerializer
    queryset = Categorie.objects.all().order_by('ordre', 'nom')

    @action(detail=False, methods=['post'], url_path='reorder')
    @transaction.atomic
    def reorder(self, request):
        orders = request.data.get('orders', [])
        if not isinstance(orders, list):
            return Response({'error': 'orders doit être une liste.'}, status=status.HTTP_400_BAD_REQUEST)

        for item in orders:
            cat_id = item.get('id')
            ordre_val = item.get('ordre')
            if cat_id is not None and ordre_val is not None:
                Categorie.objects.filter(id=cat_id).update(ordre=ordre_val)

        AdminAuditService.log_action(
            request=request,
            action="REORDER_CATEGORIES",
            ressource="Categorie",
            details={'count': len(orders)}
        )
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class AdminCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminCatalogProductSerializer
    queryset = Produit.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        etablissement_id = self.request.query_params.get('etablissement')
        categorie_id = self.request.query_params.get('categorie')

        if search:
            qs = qs.filter(Q(nom__icontains=search) | Q(description__icontains=search))
        if etablissement_id:
            qs = qs.filter(etablissement_id=etablissement_id)
        if categorie_id:
            qs = qs.filter(categorie_id=categorie_id)
        return qs

    @action(detail=True, methods=['patch'], url_path='moderate')
    def moderate(self, request, pk=None):
        produit = self.get_object()
        est_disponible = request.data.get('est_disponible')
        stock_ayyou_reserve = request.data.get('stock_ayyou_reserve')

        if est_disponible is not None:
            if isinstance(est_disponible, str):
                produit.est_disponible = est_disponible.lower() in ('true', '1')
            else:
                produit.est_disponible = bool(est_disponible)

        if stock_ayyou_reserve is not None:
            try:
                produit.stock_ayyou_reserve = int(stock_ayyou_reserve)
            except (ValueError, TypeError):
                pass

        produit.save()

        AdminAuditService.log_action(
            request=request,
            action="MODERATE_PRODUCT",
            ressource="Produit",
            resource_id=produit.id,
            details={'nom': produit.nom, 'est_disponible': produit.est_disponible, 'stock_ayyou_reserve': produit.stock_ayyou_reserve}
        )
        return Response(AdminCatalogProductSerializer(produit).data, status=status.HTTP_200_OK)


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminPaymentSerializer
    queryset = Paiement.objects.all().order_by('-date_creation')

    def get_queryset(self):
        qs = super().get_queryset()
        statut_pay = self.request.query_params.get('statut')
        methode = self.request.query_params.get('methode')

        if statut_pay:
            qs = qs.filter(statut__iexact=statut_pay)
        if methode:
            qs = qs.filter(methode__iexact=methode)
        return qs

    @action(detail=True, methods=['post'], url_path='reconcile')
    @transaction.atomic
    def reconcile(self, request, pk=None):
        paiement = self.get_object()
        note = request.data.get('note', 'Rapprochement manuel effectué par le Super Admin')

        if not isinstance(paiement.metadata, dict):
            paiement.metadata = {}
        paiement.metadata['reconciled'] = True
        paiement.save(update_fields=['metadata'])

        AdminAuditService.log_action(
            request=request,
            action="RECONCILE_PAYMENT",
            ressource="Paiement",
            resource_id=paiement.id,
            details={'reference': paiement.reference, 'note': note}
        )
        return Response(AdminPaymentSerializer(paiement).data, status=status.HTTP_200_OK)


class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().order_by('-timestamp')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        action_param = self.request.query_params.get('action')
        ressource_param = self.request.query_params.get('ressource')

        if search:
            qs = qs.filter(
                Q(action__icontains=search) |
                Q(ressource__icontains=search) |
                Q(admin_email__icontains=search) |
                Q(resource_id__icontains=search)
            )
        if action_param:
            qs = qs.filter(action__iexact=action_param)
        if ressource_param:
            qs = qs.filter(ressource__iexact=ressource_param)
        return qs
