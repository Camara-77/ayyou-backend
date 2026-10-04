import datetime
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import RepasPlanifie
from .serializers_planning import RepasPlanifieSerializer


class PlanningListCreateView(APIView):
    """
    GET /api/orders/planning/
    POST /api/orders/planning/
    Gestion du planning personnel d'un Client AYYOU.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = RepasPlanifie.objects.filter(utilisateur=user).exclude(statut=RepasPlanifie.STATUT_ANNULE).select_related('produit', 'etablissement', 'variante')

        date_str = request.query_params.get('date')
        annee_param = request.query_params.get('annee')
        mois_param = request.query_params.get('mois')

        today = timezone.now().date()
        target_year = today.year
        target_month = today.month

        if annee_param and annee_param.isdigit():
            target_year = int(annee_param)
        if mois_param and mois_param.isdigit():
            target_month = int(mois_param)

        selected_date = None
        if date_str:
            try:
                selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                target_year = selected_date.year
                target_month = selected_date.month
            except ValueError:
                selected_date = None

        # Ensemble des repas du mois cible
        month_qs = queryset.filter(
            date_planifiee__year=target_year,
            date_planifiee__month=target_month
        ).order_by('date_planifiee', 'creneau')

        # Liste des dates distinctes du mois possédant au moins un repas planifié
        dates_avec_repas = list(
            month_qs.values_list('date_planifiee', flat=True).distinct().order_by('date_planifiee')
        )
        dates_avec_repas_str = [d.strftime('%Y-%m-%d') for d in dates_avec_repas]

        # Repas affichés (soit pour la date spécifique sélectionnée, soit tous les repas du mois)
        if selected_date:
            repas_qs = month_qs.filter(date_planifiee=selected_date)
        else:
            repas_qs = month_qs

        serializer = RepasPlanifieSerializer(repas_qs, many=True)

        return Response({
            'annee': target_year,
            'mois': target_month,
            'selected_date': selected_date.strftime('%Y-%m-%d') if selected_date else None,
            'total_repas_mois': month_qs.count(),
            'dates_avec_repas': dates_avec_repas_str,
            'repas': serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RepasPlanifieSerializer(data=request.data)
        if serializer.is_valid():
            repas = serializer.save(utilisateur=request.user)
            return Response(RepasPlanifieSerializer(repas).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlanningDetailView(APIView):
    """
    GET /api/orders/planning/{id}/
    PATCH /api/orders/planning/{id}/
    DELETE /api/orders/planning/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(
            RepasPlanifie.objects.select_related('produit', 'etablissement', 'variante'),
            pk=pk,
            utilisateur=request.user
        )

    def get(self, request, pk):
        repas = self.get_object(request, pk)
        serializer = RepasPlanifieSerializer(repas)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        repas = self.get_object(request, pk)
        serializer = RepasPlanifieSerializer(repas, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        repas = self.get_object(request, pk)
        if repas.statut == RepasPlanifie.STATUT_COMMANDE:
            return Response(
                {"detail": "Ce repas a déjà été transformé en commande et ne peut pas être supprimé."},
                status=status.HTTP_400_BAD_REQUEST
            )
        repas.statut = RepasPlanifie.STATUT_ANNULE
        repas.rappel_valide = False
        repas.rappel_reporte = False
        repas.save(update_fields=['statut', 'rappel_valide', 'rappel_reporte', 'date_modification'])

        try:
            from apps.notifications.models import Notification
            Notification.objects.filter(
                utilisateur=request.user,
                reference_type='RepasPlanifie',
                reference_id=str(repas.id)
            ).update(statut=Notification.STATUT_ECHEC)
        except Exception:
            pass

        return Response(status=status.HTTP_204_NO_CONTENT)

