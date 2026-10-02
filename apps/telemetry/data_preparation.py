from typing import Dict, Any, List, Optional
from datetime import datetime
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone

from apps.telemetry.models import VideoEventLog
from apps.users.models import Utilisateur, ProfilClient
from apps.catalog.models import PublicationFeed, Produit, Etablissement, LikeProduit
from apps.orders.models import Commande, LigneCommande


class TelemetryDataCleaner:
    """
    Module de nettoyage et de validation des événements bruts de télémétrie.
    Ne modifie pas la base de données brute VideoEventLog, mais garantit l'intégrité
    des données transmises au Feature Engineering.
    """

    @staticmethod
    def calculate_completion_rate(watch_time_seconds: Optional[float], video_duration_seconds: Optional[float]) -> float:
        """
        Calcule le taux de complétion d'une vidéo.
        Garantit une valeur strictement comprise entre 0.0 et 1.0 (0.0 <= completion_rate <= 1.0).
        Protection contre division par zéro, valeurs NULL, et durées négatives.
        """
        if watch_time_seconds is None or video_duration_seconds is None:
            return 0.0

        try:
            wt = float(watch_time_seconds)
            vd = float(video_duration_seconds)
        except (ValueError, TypeError):
            return 0.0

        if wt < 0 or vd <= 0:
            return 0.0

        rate = wt / vd
        if rate > 1.0:
            return 1.0
        return round(rate, 4)

    @staticmethod
    def is_valid_event(event: Any) -> bool:
        """
        Vérifie si un événement de télémétrie est valide et exploitable.
        """
        if not event:
            return False

        # Extraction des attributs (dict ou modèle ORM)
        if isinstance(event, dict):
            publication_id = event.get('publication_id') or event.get('publication')
            event_type = event.get('event_type')
            watch_time = event.get('watch_time_seconds', 0.0)
            duration = event.get('video_duration_seconds', 0.0)
        else:
            publication_id = getattr(event, 'publication_id', None)
            event_type = getattr(event, 'event_type', None)
            watch_time = getattr(event, 'watch_time_seconds', 0.0)
            duration = getattr(event, 'video_duration_seconds', 0.0)

        if not publication_id:
            return False

        valid_types = [choice[0] for choice in VideoEventLog.CHOIX_EVENT_TYPES]
        if event_type not in valid_types:
            return False

        if watch_time is not None and watch_time < 0:
            return False

        if duration is not None and duration < 0:
            return False

        return True


class FeatureExtractor:
    """
    Extrait et calcule les caractéristiques (Features) pour les Utilisateurs, les Vidéos et les Interactions.
    """

    @staticmethod
    def extract_user_features(
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        at_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extrait le profil de caractéristiques d'un utilisateur (connecté ou anonyme) à un instant T (at_datetime).
        
        RÈGLE ANTI-FUITE TEMPORELLE (created_at < at_datetime) :
        Seuls les événements et interactions créés STRICTEMENT AVANT at_datetime sont pris en compte.
        """
        ref_time = at_datetime or timezone.now()

        features = {
            'is_authenticated': False,
            'user_account_age_days': 0,
            'user_total_orders': 0,
            'user_avg_order_amount': 0.0,
            'user_total_likes': 0,
            'user_total_events': 0,
            'user_avg_watch_time': 0.0,
            'user_avg_completion_rate': 0.0,
            'user_top_category_id': None,
        }

        if user_id:
            try:
                user = Utilisateur.objects.get(pk=user_id)
                features['is_authenticated'] = True
                
                # Ancienneté relative à ref_time
                if user.date_creation:
                    delta = ref_time - user.date_creation
                    features['user_account_age_days'] = max(0, delta.days)

                # Commandes passées créées strictement avant ref_time
                commandes = Commande.objects.filter(
                    utilisateur=user,
                    statut__in=['PAYEE', 'LIVREE'],
                    date_creation__lt=ref_time
                )
                features['user_total_orders'] = commandes.count()
                avg_total = commandes.aggregate(Avg('total'))['total__avg']
                features['user_avg_order_amount'] = float(avg_total) if avg_total else 0.0

                # Likes créés strictly avant ref_time
                features['user_total_likes'] = LikeProduit.objects.filter(
                    utilisateur=user,
                    date_creation__lt=ref_time
                ).count()

                # Events Télémétrie créés strictly avant ref_time (exclut l'événement courant et les futurs)
                events = VideoEventLog.objects.filter(
                    utilisateur=user,
                    created_at__lt=ref_time
                )
                features['user_total_events'] = events.count()
                avg_wt = events.aggregate(Avg('watch_time_seconds'))['watch_time_seconds__avg']
                features['user_avg_watch_time'] = float(avg_wt) if avg_wt else 0.0

                # Top Categorie commandée strictement avant ref_time
                lignes = LigneCommande.objects.filter(
                    sous_commande__commande__utilisateur=user,
                    sous_commande__commande__date_creation__lt=ref_time,
                    produit__isnull=False
                )
                top_cat = lignes.values('produit__categorie_id').annotate(cnt=Count('id')).order_by('-cnt').first()
                if top_cat:
                    features['user_top_category_id'] = top_cat['produit__categorie_id']

            except Utilisateur.DoesNotExist:
                pass
        elif session_id:
            # Traitement pour utilisateur anonyme via session (strictly avant ref_time)
            events = VideoEventLog.objects.filter(
                session_id=session_id,
                created_at__lt=ref_time
            )
            features['user_total_events'] = events.count()
            avg_wt = events.aggregate(Avg('watch_time_seconds'))['watch_time_seconds__avg']
            features['user_avg_watch_time'] = float(avg_wt) if avg_wt else 0.0

        return features

    @staticmethod
    def extract_video_features(
        publication_id: Any,
        at_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extrait le profil de caractéristiques d'une vidéo / publication feed à un instant T (at_datetime).
        
        RÈGLE ANTI-FUITE TEMPORELLE (created_at < at_datetime) :
        Seuls les événements et interactions créés STRICTEMENT AVANT at_datetime sont pris en compte.
        """
        ref_time = at_datetime or timezone.now()

        features = {
            'publication_id': str(publication_id),
            'video_recency_hours': 0.0,
            'video_duration_seconds': 0.0,
            'video_total_likes': 0,
            'video_total_shares': 0,
            'dish_id': None,
            'dish_price': 0.0,
            'dish_category_id': None,
            'resto_id': None,
            'resto_rating': 0.0,
            'resto_reviews_count': 0,
            'resto_type': None,
            'video_total_views': 0,
            'video_avg_completion_rate': 0.0,
        }

        try:
            pub = PublicationFeed.objects.select_related('produit', 'etablissement', 'produit__categorie').get(pk=publication_id)
            
            if pub.date_publication:
                delta = ref_time - pub.date_publication
                features['video_recency_hours'] = max(0.0, round(delta.total_seconds() / 3600.0, 2))

            features['video_total_likes'] = pub.nombre_likes
            features['video_total_shares'] = pub.nombre_partages

            if pub.produit:
                features['dish_id'] = str(pub.produit.id)
                features['dish_price'] = float(pub.produit.prix_base)
                if pub.produit.categorie:
                    features['dish_category_id'] = pub.produit.categorie.id

            if pub.etablissement:
                features['resto_id'] = str(pub.etablissement.id)
                features['resto_rating'] = float(pub.etablissement.note_moyenne)
                features['resto_reviews_count'] = pub.etablissement.nombre_avis
                features['resto_type'] = pub.etablissement.type_etablissement

            # Agrégation des télémétries sur la vidéo créées strictement avant ref_time
            events = VideoEventLog.objects.filter(publication=pub, created_at__lt=ref_time)
            features['video_total_views'] = events.filter(event_type__in=['IMPRESSION', 'PLAY', 'WATCH']).count()

        except PublicationFeed.DoesNotExist:
            pass

        return features

    @staticmethod
    def extract_interaction_features(event: Any) -> Dict[str, Any]:
        """
        Extrait les caractéristiques propres à une interaction de visionnage spécifique.
        """
        if isinstance(event, dict):
            wt = event.get('watch_time_seconds', 0.0)
            vd = event.get('video_duration_seconds', 0.0)
            pos = event.get('feed_position', 0)
            etype = event.get('event_type')
            dt = event.get('created_at') or timezone.now()
        else:
            wt = getattr(event, 'watch_time_seconds', 0.0)
            vd = getattr(event, 'video_duration_seconds', 0.0)
            pos = getattr(event, 'feed_position', 0)
            etype = getattr(event, 'event_type', '')
            dt = getattr(event, 'created_at', timezone.now())

        completion_rate = TelemetryDataCleaner.calculate_completion_rate(wt, vd)
        is_skip = (etype == VideoEventLog.EVENT_SKIP) or (wt < 3.0 and etype not in [VideoEventLog.EVENT_LIKE, VideoEventLog.EVENT_CART_ADD, VideoEventLog.EVENT_DISH_CLICK])
        is_completed = (etype == VideoEventLog.EVENT_COMPLETED) or (completion_rate >= 0.90)

        if isinstance(dt, datetime):
            hour = dt.hour
            weekday = dt.weekday()
        else:
            hour = timezone.now().hour
            weekday = timezone.now().weekday()

        return {
            'event_type': etype,
            'watch_time_seconds': float(wt or 0.0),
            'video_duration_seconds': float(vd or 0.0),
            'completion_rate': completion_rate,
            'feed_position': int(pos or 0),
            'is_skip': is_skip,
            'is_completed': is_completed,
            'hour_of_day': hour,
            'day_of_week': weekday,
        }


class DatasetBuilder:
    """
    Construit le dataset d'apprentissage tabulaire dénormalisé pour le futur modèle LightGBM.
    """

    @staticmethod
    def compute_relevance_label(event_type: str, completion_rate: float) -> int:
        """
        Calcule la variable cible (Target Relevance Score entre 0 et 4) pour un événement.
        - 0 : Skip / Intérêt nul (< 3s)
        - 1 : Vue partielle (< 50%)
        - 2 : Vue complète / Complétion (>= 90%)
        - 3 : Like / Partage (Engagement social)
        - 4 : Clic Plat / Ajout Panier (Conversion commerciale)
        """
        if event_type in [VideoEventLog.EVENT_CART_ADD, VideoEventLog.EVENT_DISH_CLICK]:
            return 4
        if event_type in [VideoEventLog.EVENT_LIKE, VideoEventLog.EVENT_SHARE]:
            return 3
        if event_type == VideoEventLog.EVENT_COMPLETED or completion_rate >= 0.90:
            return 2
        if event_type == VideoEventLog.EVENT_SKIP or (completion_rate < 0.15 and event_type not in [VideoEventLog.EVENT_PLAY, VideoEventLog.EVENT_IMPRESSION]):
            return 0
        return 1

    @classmethod
    def build_dataset_row(cls, event: Any) -> Optional[Dict[str, Any]]:
        """
        Construit une ligne unique dénormalisée du dataset d'apprentissage.
        Garantit qu'aucun événement futur (>= created_at) ne fuite dans les features historiques.
        """
        if not TelemetryDataCleaner.is_valid_event(event):
            return None

        if isinstance(event, dict):
            user_id = event.get('utilisateur_id') or event.get('utilisateur')
            session_id = event.get('session_id')
            publication_id = event.get('publication_id') or event.get('publication')
            event_dt = event.get('created_at')
        else:
            user_id = event.utilisateur_id if hasattr(event, 'utilisateur_id') else None
            session_id = event.session_id
            publication_id = event.publication_id
            event_dt = getattr(event, 'created_at', None)

        if not isinstance(event_dt, datetime):
            event_dt = timezone.now()

        user_feats = FeatureExtractor.extract_user_features(
            user_id=user_id,
            session_id=session_id,
            at_datetime=event_dt
        )
        video_feats = FeatureExtractor.extract_video_features(
            publication_id=publication_id,
            at_datetime=event_dt
        )
        interaction_feats = FeatureExtractor.extract_interaction_features(event)

        target_label = cls.compute_relevance_label(
            interaction_feats['event_type'],
            interaction_feats['completion_rate']
        )

        row = {
            'query_session_id': session_id,
            'user_id': user_id,
            'publication_id': str(publication_id),
            'target_relevance': target_label,
            **user_feats,
            **video_feats,
            **interaction_feats,
        }

        return row

    @classmethod
    def build_training_dataset(cls, queryset=None) -> List[Dict[str, Any]]:
        """
        Génère l'ensemble du dataset d'apprentissage à partir des événements de télémétrie.
        """
        if queryset is None:
            queryset = VideoEventLog.objects.all().order_by('created_at')

        dataset = []
        for event in queryset:
            row = cls.build_dataset_row(event)
            if row is not None:
                dataset.append(row)

        return dataset
