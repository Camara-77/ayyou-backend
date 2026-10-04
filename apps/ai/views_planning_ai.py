import re
import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.catalog.models import Produit, Etablissement, Categorie
from apps.ai.vision_service import VisionService
from apps.ai.models import AIConversation, AIMessage
from apps.ai.serializers import AIConversationSerializer, AIMessageSerializer
from apps.ai.tools import (
    search_active_categories,
    search_food,
    search_establishments,
    search_food_paginated,
    search_establishments_paginated
)


class SafeJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None


FOOD_SYNONYMS = {
    'burger': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
    'burgers': ['burger', 'hamburgers', 'hamburger', 'cheeseburger', 'cheeseburgers', 'smashburger'],
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
    'pizzas': ['pizza', 'pizzas', 'pizzeria'],
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


class AIVisionAnalyzeView(APIView):
    """
    POST /api/ai/vision-analyze/
    Analyse d'image multimodale (JPG, PNG, WEBP) pour détection d'aliments
    et correspondance avec le catalogue réel PostgreSQL AYYOU.
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uploaded_file = request.FILES.get('image')
        if not uploaded_file:
            return Response(
                {"detail": "Le fichier 'image' est requis (JPG, PNG, WEBP)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        res = VisionService.analyze_food_image(uploaded_file)
        return Response(res, status=status.HTTP_200_OK)


class AIPlanningParseView(APIView):
    """
    POST /api/ai/planning-parse/
    Analyse d'une demande de planification (texte ou voix transcrite) et validation
    stricte anti-hallucination contre la base de données PostgreSQL AYYOU.
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]

    DAYS_MAP = {
        'lundi': 0,
        'mardi': 1,
        'mercredi': 2,
        'jeudi': 3,
        'vendredi': 4,
        'samedi': 5,
        'dimanche': 6
    }

    MONTHS_FR = [
        '', 'Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin',
        'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.'
    ]

    DAYS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

    def post(self, request):
        prompt = request.data.get('prompt', '').strip()
        force_action = request.data.get('force_action', '').strip().upper() or request.data.get('action', '').strip().upper()
        conversation_id = request.data.get('conversation_id')
        if not prompt and force_action not in ['GET_PRODUCT_DETAIL', 'FOOD_SEARCH', 'RESTAURANT_SEARCH', 'CATEGORY_SEARCH']:
            return Response(
                {"detail": "Le champ 'prompt' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        prompt_lower = prompt.lower()
        user = request.user if (hasattr(request, 'user') and request.user and request.user.is_authenticated) else None
        session_key = request.session.session_key if hasattr(request, 'session') else None

        conversation = None
        if conversation_id:
            try:
                conversation = AIConversation.objects.get(id=conversation_id)
            except (AIConversation.DoesNotExist, ValueError):
                conversation = None

        if not conversation:
            conv_title = prompt[:35] if prompt else "Nouvelle conversation"
            conversation = AIConversation.objects.create(
                utilisateur=user,
                session_key=session_key,
                titre=conv_title,
                context_data={}
            )

        ctx = conversation.context_data or {}
        last_products = ctx.get('last_products', [])
        last_selected_product_id = ctx.get('last_selected_product_id')
        last_searched_term = ctx.get('last_searched_term', '')
        last_dt = ctx.get('last_detected_datetime', {})
        pending_selection = ctx.get('pending_selection')
        awaiting_confirmation = ctx.get('awaiting_confirmation', False)
        last_matching_ests = ctx.get('last_matching_establishments', [])
        last_results = ctx.get('last_results') or {}
        previous_results = ctx.get('previous_results')
        selected_restaurant = ctx.get('selected_restaurant')
        selected_product = ctx.get('selected_product')

        context_product = None
        if last_selected_product_id:
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=last_selected_product_id)
            except Produit.DoesNotExist:
                context_product = None
        elif selected_product and isinstance(selected_product, dict) and selected_product.get('id'):
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=selected_product['id'])
            except Produit.DoesNotExist:
                context_product = None
        elif last_products and isinstance(last_products[0], dict) and last_products[0].get('id'):
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=last_products[0]['id'])
            except Produit.DoesNotExist:
                context_product = None

        req_product_id = request.data.get('product_id')
        req_establishment_id = request.data.get('establishment_id')
        try:
            req_offset = max(0, int(request.data.get('offset', 0)))
        except (ValueError, TypeError):
            req_offset = 0
        try:
            req_limit = max(1, int(request.data.get('limit', 6)))
        except (ValueError, TypeError):
            req_limit = 6

        # Parse potential date & time from prompt
        parsed_target_date, parsed_date_label = self._parse_date(prompt_lower)
        parsed_time_label, parsed_creneau = self._parse_time(prompt_lower)

        # Update datetime context ONLY if explicitly specified in prompt
        if parsed_target_date is not None:
            last_dt['date_iso'] = parsed_target_date.strftime('%Y-%m-%d')
            last_dt['date_label'] = parsed_date_label
        if parsed_time_label is not None:
            last_dt['time_label'] = parsed_time_label
            last_dt['creneau'] = parsed_creneau

        if parsed_target_date is not None or parsed_time_label is not None:
            ctx['last_detected_datetime'] = last_dt

        # -------------------------------------------------------------
        # ACTION 0: BACK_TO_RESTAURANTS ("Retour aux restaurants")
        # -------------------------------------------------------------
        is_back_request = force_action == 'BACK_TO_RESTAURANTS' or any(w in prompt_lower for w in ['retour', 'retour aux restaurants', 'revenir en arrière', 'revenir en arriere'])
        if is_back_request and previous_results:
            ctx['last_results'] = previous_results
            ctx['previous_results'] = None
            conversation.context_data = ctx
            res_data = {
                "status": "restaurant_search",
                "intent": "RESTAURANT_SEARCH",
                "type": "catalog_results",
                "entity": "restaurant",
                "message": "Voici à nouveau la liste des restaurants :",
                "user_text": prompt,
                "matching_establishments": previous_results.get("items", []),
                "suggested_actions": []
            }
            return self._save_message_and_respond(conversation, prompt, res_data, matching_establishments=previous_results.get("items", []))

        # -------------------------------------------------------------
        # ACTION 0.5: SHOW_RESTAURANT_DISHES ("Ses plats" / "Son menu")
        # -------------------------------------------------------------
        is_dishes_request = force_action == 'SHOW_RESTAURANT_DISHES' or any(w in prompt_lower for w in ['ses plats', 'ses produits', 'son menu', 'sa carte', 'voir ses plats', 'plats du restaurant'])
        if is_dishes_request:
            target_est = selected_restaurant
            if not target_est and req_establishment_id:
                from apps.ai.tools import get_establishment
                target_est = get_establishment(req_establishment_id)
            if not target_est and selected_product:
                e_id = selected_product.get('etablissement_id')
                if e_id:
                    est_obj = Etablissement.objects.filter(id=e_id).first()
                    if est_obj:
                        target_est = {
                            "id": est_obj.id,
                            "nom": est_obj.nom,
                            "adresse": est_obj.adresse or "Dakar"
                        }
            if not target_est and last_matching_ests:
                target_est = last_matching_ests[0]
            elif not target_est and last_results and last_results.get('type') == 'restaurant_search' and last_results.get('items'):
                target_est = last_results['items'][0]

            if target_est and target_est.get('id'):
                from apps.catalog.catalog_service import CatalogSearchService
                dishes_res = CatalogSearchService.get_establishment_products(establishment_id=target_est['id'])
                items = dishes_res.get('results', [])
                ctx['previous_results'] = last_results or {"type": "restaurant_search", "items": last_matching_ests}
                ctx['last_results'] = {"type": "restaurant_dishes", "restaurant": target_est, "items": items}
                ctx['selected_restaurant'] = target_est
                res_data = {
                    "status": "restaurant_dishes",
                    "intent": "PRODUCT_SEARCH",
                    "type": "catalog_results",
                    "entity": "product",
                    "message": f"Voici les plats proposés par {target_est['nom']} :",
                    "user_text": prompt,
                    "matching_products": items,
                    "detected_establishment": target_est,
                    "suggested_actions": [
                        {"label": "← Retour aux restaurants", "action": "BACK_TO_RESTAURANTS"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, matching_products=items)

        # -------------------------------------------------------------
        # ACTION 0.9: ORDER_PRODUCT / ADD_TO_CART ("Commande-le", "Ajoute au panier", etc.)
        # -------------------------------------------------------------
        order_triggers = [
            'commande-le', 'commandes-le', 'commande le', 'commander', 'commande',
            'ajoute-le au panier', 'ajoute au panier', 'ajouter au panier', 'mets au panier',
            'mettre au panier', 'dans le panier', 'je prends', 'j\'en prends', 'j`en prends',
            'achete', 'acheter', 'je veux commander', 'prends-le', 'prends le', 'prends la'
        ]
        is_order_trigger = force_action in ['ORDER_PRODUCT', 'ADD_TO_CART'] or any(t in prompt_lower for t in order_triggers)
        is_asking_how_to = any(w in prompt_lower for w in ['comment commander', 'comment faire pour commander', 'aide'])

        if is_order_trigger and not is_asking_how_to and force_action != 'CREATE_PLANNING':
            # 1. Parsing de la quantité explicite (ex: "2 thiéboudiennes", "deux burgers", "j'en prends 3")
            order_qty = 1
            qty_word_map = {'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, '2': 2, '3': 3, '4': 4, '5': 5}
            for word, val in qty_word_map.items():
                if re.search(r'\b' + re.escape(word) + r'\b', prompt_lower):
                    order_qty = val
                    break

            # 2. Détermination du produit cible
            target_prod_obj = None

            # 2a. Via ID explicite transmis dans la requête
            if req_product_id:
                try:
                    target_prod_obj = Produit.objects.select_related('etablissement').get(id=req_product_id)
                except Produit.DoesNotExist:
                    target_prod_obj = None

            # 2b. Via anaphore ("le premier", "le deuxième", "le moins cher", etc.)
            if not target_prod_obj:
                ref_items = []
                if last_results and last_results.get('items') and last_results.get('type') != 'restaurant_search':
                    ref_items = last_results['items']
                elif last_products:
                    ref_items = last_products

                idx = None
                if any(w in prompt_lower for w in ['troisième', '3ème', '3eme', 'troisieme']):
                    idx = 2
                elif any(w in prompt_lower for w in ['deuxième', '2ème', '2eme', 'deuxieme']):
                    idx = 1
                elif any(w in prompt_lower for w in ['premier', '1er', '1ere', 'première']):
                    idx = 0
                elif any(w in prompt_lower for w in ['dernier', 'dernière']):
                    idx = len(ref_items) - 1 if ref_items else None
                elif 'moins cher' in prompt_lower and ref_items:
                    sorted_prods = sorted(ref_items, key=lambda x: float(x.get('prix', 0) or 0))
                    idx = ref_items.index(sorted_prods[0])
                elif 'plus cher' in prompt_lower and ref_items:
                    sorted_prods = sorted(ref_items, key=lambda x: float(x.get('prix', 0) or 0), reverse=True)
                    idx = ref_items.index(sorted_prods[0])

                if idx is not None and ref_items and 0 <= idx < len(ref_items):
                    p_info = ref_items[idx]
                    try:
                        target_prod_obj = Produit.objects.select_related('etablissement').get(id=p_info['id'])
                    except Produit.DoesNotExist:
                        target_prod_obj = None

            # 2c. Via le contexte courant (dernier produit sélectionné)
            if not target_prod_obj and context_product:
                target_prod_obj = context_product

            # 2d. Via recherche textuelle dans le catalogue
            if not target_prod_obj:
                matched_p, _ = self._find_matching_product(prompt)
                if matched_p:
                    target_prod_obj = matched_p

            # 3. Si aucun produit n'est déterminé
            if not target_prod_obj:
                res_data = {
                    "status": "missing_info",
                    "intent": "ADD_TO_CART",
                    "message": "Quel plat souhaitez-vous commander ?",
                    "user_text": prompt,
                    "suggested_actions": [
                        {"label": "Rechercher des plats", "action": "FOOD_SEARCH"},
                        {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

            # 4. Vérifications de disponibilité et statut établissement sur PostgreSQL
            if not target_prod_obj.est_disponible:
                res_data = {
                    "status": "product_unavailable",
                    "intent": "ADD_TO_CART",
                    "message": f"Ce plat ('{target_prod_obj.nom}') n'est malheureusement plus disponible actuellement.",
                    "user_text": prompt,
                    "detected_product": None,
                    "suggested_actions": [
                        {"label": "Rechercher d'autres plats", "action": "FOOD_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=target_prod_obj)

            if target_prod_obj.etablissement and target_prod_obj.etablissement.statut == Etablissement.STATUT_FERME:
                res_data = {
                    "status": "establishment_closed",
                    "intent": "ADD_TO_CART",
                    "message": f"L'établissement '{target_prod_obj.etablissement.nom}' est actuellement fermé.",
                    "user_text": prompt,
                    "detected_product": None,
                    "suggested_actions": [
                        {"label": "Voir d'autres restaurants", "action": "RESTAURANT_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=target_prod_obj)

            # 5. Tout est valide -> Retourner la commande d'ajout au panier avec prix réel PostgreSQL
            prix_real = float(target_prod_obj.prix_base)
            prix_fmt = f"{prix_real:,.0f} FCFA".replace(",", " ")
            est_nom = target_prod_obj.etablissement.nom if target_prod_obj.etablissement else "AYYOU"

            ctx['selected_product'] = {
                "id": target_prod_obj.id,
                "nom": target_prod_obj.nom,
                "prix": prix_real,
                "prix_formate": prix_fmt,
                "image_url": target_prod_obj.image_url or "assets/images/thieboudienne.jpg",
                "etablissement_id": target_prod_obj.etablissement.id if target_prod_obj.etablissement else None,
                "etablissement_nom": est_nom
            }
            ctx['last_selected_product_id'] = target_prod_obj.id
            conversation.context_data = ctx
            conversation.save()

            res_data = {
                "status": "order_requested",
                "intent": "ADD_TO_CART",
                "type": "action_cart",
                "message": f"Ajout de {target_prod_obj.nom} ({prix_fmt}) chez {est_nom} au panier...",
                "user_text": prompt,
                "quantite": order_qty,
                "detected_product": {
                    "id": target_prod_obj.id,
                    "nom": target_prod_obj.nom,
                    "prix": prix_real,
                    "prix_formate": prix_fmt,
                    "image_url": target_prod_obj.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_id": target_prod_obj.etablissement.id if target_prod_obj.etablissement else None,
                    "etablissement_nom": est_nom,
                    "etablissement_adresse": target_prod_obj.etablissement.adresse if target_prod_obj.etablissement else "Dakar"
                },
                "detected_establishment": {
                    "id": target_prod_obj.etablissement.id if target_prod_obj.etablissement else None,
                    "nom": est_nom,
                    "adresse": target_prod_obj.etablissement.adresse if target_prod_obj.etablissement else "Dakar"
                } if target_prod_obj.etablissement else None,
                "suggested_actions": [
                    {"label": "Voir le panier", "action": "VIEW_CART"},
                    {"label": "Continuer", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=target_prod_obj)

        # -------------------------------------------------------------
        # ACTION 0.95: GET_PRODUCT_DETAIL ("Voir la fiche produit", "Détail")
        # -------------------------------------------------------------
        if force_action == 'GET_PRODUCT_DETAIL' or (req_product_id and any(w in prompt_lower for w in ['détail', 'detail', 'fiche', 'voir le plat', 'voir ce plat'])):
            p_detail_id = req_product_id or last_selected_product_id
            if not p_detail_id and context_product:
                p_detail_id = context_product.id

            prod_detail_dict = None
            if p_detail_id:
                from apps.catalog.catalog_service import CatalogSearchService
                prod_detail_dict = CatalogSearchService.get_product(p_detail_id)

            if not prod_detail_dict:
                res_data = {
                    "status": "product_not_found",
                    "intent": "GET_PRODUCT_DETAIL",
                    "message": "Le plat demandé est introuvable ou n'est plus répertorié.",
                    "user_text": prompt,
                    "suggested_actions": [
                        {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

            ctx['selected_product'] = prod_detail_dict
            ctx['last_selected_product_id'] = prod_detail_dict['id']
            conversation.context_data = ctx
            conversation.save()

            res_data = {
                "status": "product_detail",
                "intent": "GET_PRODUCT_DETAIL",
                "type": "catalog_results",
                "entity": "product",
                "message": f"Voici la fiche détaillée de '{prod_detail_dict['nom']}' chez {prod_detail_dict.get('etablissement_nom', 'AYYOU')} :",
                "user_text": prompt,
                "detected_product": prod_detail_dict,
                "detected_establishment": {
                    "id": prod_detail_dict.get('etablissement_id'),
                    "nom": prod_detail_dict.get('etablissement_nom', 'AYYOU'),
                    "adresse": prod_detail_dict.get('etablissement_adresse', 'Dakar')
                },
                "suggested_actions": [
                    {"label": "Commander", "action": "ADD_TO_CART"},
                    {"label": "Planifier", "action": "CREATE_PLANNING"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)


        # -------------------------------------------------------------
        # ACTION 1: DECLINE_PLANNING ("Non" / Refus de planification, modification ou suppression)
        # -------------------------------------------------------------
        is_decline_word = any(prompt_lower.startswith(w) for w in ['non', 'annuler', 'pas maintenant', 'refuser', 'stop'])
        if force_action == 'DECLINE_PLANNING' or is_decline_word:
            was_updating = bool(ctx.get('pending_update') or ctx.get('editing_planning_id') or ctx.get('awaiting_update_confirmation'))
            was_deleting = bool(ctx.get('pending_delete_id') or ctx.get('awaiting_delete_confirmation'))
            ctx['pending_selection'] = None
            ctx['pending_update'] = None
            ctx['pending_delete_id'] = None
            ctx['awaiting_confirmation'] = False
            ctx['awaiting_update_confirmation'] = False
            ctx['awaiting_delete_confirmation'] = False
            ctx['editing_planning_id'] = None
            ctx['selectable_plannings'] = None
            ctx['selectable_delete_plannings'] = None

            if was_deleting:
                msg_text = "La suppression a été annulée. Votre repas planifié est conservé."
            elif was_updating:
                msg_text = "Vous avez annulé la modification. Comment puis-je vous aider ?"
            else:
                msg_text = "D'accord 😊 Vous pouvez continuer votre recherche."

            res_data = {
                "status": "declined",
                "intent": "DECLINE_PLANNING",
                "message": msg_text,
                "user_text": prompt,
                "detected_product": None,
                "detected_establishment": None,
                "detected_datetime": None,
                "suggested_actions": [
                    {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"},
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # ACTION 2: CONFIRM_PLANNING ("Oui, planifier" / Confirmation)
        # -------------------------------------------------------------
        is_confirm_word = any(prompt_lower.startswith(w) for w in ['oui', 'confirm', 'd\'accord', 'daccord', 'ok']) or 'je confirme' in prompt_lower or 'oui, planifier' in prompt_lower or 'oui, modifier' in prompt_lower or 'oui, supprimer' in prompt_lower

        # ACTION 2.3: CONFIRM_DELETE_PLANNING (Confirmation de suppression)
        awaiting_del_confirm = ctx.get('awaiting_delete_confirmation', False)
        pending_del_id = ctx.get('pending_delete_id') or request.data.get('planning_id')
        if force_action == 'CONFIRM_DELETE_PLANNING' or (awaiting_del_confirm and is_confirm_word):
            if pending_del_id and user:
                try:
                    from apps.orders.models import RepasPlanifie
                    repas = RepasPlanifie.objects.select_related('produit', 'etablissement').get(id=pending_del_id, utilisateur=user)
                    if repas.statut == RepasPlanifie.STATUT_COMMANDE:
                        ctx['pending_delete_id'] = None
                        ctx['awaiting_delete_confirmation'] = False
                        res_data = {
                            "status": "cannot_delete_converted",
                            "intent": "CONFIRM_DELETE_PLANNING",
                            "message": "Ce repas a déjà été transformé en commande validée et ne peut pas être supprimé.",
                            "user_text": prompt,
                            "suggested_actions": [
                                {"label": "Voir mon planning", "action": "VIEW_PLANNING"}
                            ]
                        }
                        return self._save_message_and_respond(conversation, prompt, res_data)

                    repas.statut = RepasPlanifie.STATUT_ANNULE
                    repas.rappel_valide = False
                    repas.rappel_reporte = False
                    repas.save(update_fields=['statut', 'rappel_valide', 'rappel_reporte', 'date_modification'])

                    try:
                        from apps.notifications.models import Notification
                        Notification.objects.filter(
                            utilisateur=user,
                            reference_type='RepasPlanifie',
                            reference_id=str(repas.id)
                        ).update(statut=Notification.STATUT_ECHEC)
                    except Exception:
                        pass

                    ctx['pending_delete_id'] = None
                    ctx['awaiting_delete_confirmation'] = False
                    ctx['selectable_delete_plannings'] = None

                    res_data = {
                        "status": "planning_deleted",
                        "intent": "CONFIRM_DELETE_PLANNING",
                        "message": f"C'est fait ! Votre repas de {repas.produit.nom} chez {repas.etablissement.nom} a bien été supprimé de votre planning.",
                        "user_text": prompt,
                        "planning_id": repas.id,
                        "suggested_actions": [
                            {"label": "Voir mon planning", "action": "VIEW_PLANNING"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)
                except RepasPlanifie.DoesNotExist:
                    return Response({"detail": "Le repas planifié à supprimer est introuvable ou appartient à un autre compte."}, status=status.HTTP_404_NOT_FOUND)

        # ACTION 2.2: CONFIRM_UPDATE_PLANNING (Confirmation de modification)
        awaiting_upd_confirm = ctx.get('awaiting_update_confirmation', False)
        pending_upd = ctx.get('pending_update')
        if force_action == 'CONFIRM_UPDATE_PLANNING' or (awaiting_upd_confirm and is_confirm_word):
            if pending_upd and user:
                r_id = pending_upd.get('planning_id')
                try:
                    from apps.orders.models import RepasPlanifie
                    repas = RepasPlanifie.objects.get(id=r_id, utilisateur=user)
                    new_p = Produit.objects.get(id=pending_upd['product_id'])
                    new_e = Etablissement.objects.get(id=pending_upd['establishment_id'])

                    repas.produit = new_p
                    repas.etablissement = new_e
                    repas.date_planifiee = pending_upd['date_iso']
                    repas.creneau = pending_upd['creneau']
                    if pending_upd.get('time_label'):
                        raw_t = str(pending_upd['time_label']).replace('h', ':').replace('H', ':')
                        if ':' in raw_t:
                            parts = raw_t.split(':')
                            repas.heure_planifiee = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                        else:
                            repas.heure_planifiee = raw_t
                    repas.prix_total = float(new_p.prix_base) * repas.quantite
                    repas.save()

                    date_lbl = pending_upd.get('date_label', pending_upd['date_iso'])
                    time_lbl = pending_upd.get('time_label', '')

                    ctx['pending_update'] = None
                    ctx['awaiting_update_confirmation'] = False
                    ctx['editing_planning_id'] = None

                    res_data = {
                        "status": "planning_updated",
                        "intent": "CONFIRM_UPDATE_PLANNING",
                        "message": f"Votre repas (n°{repas.id}) de {new_p.nom} chez {new_e.nom} a bien été modifié pour le {date_lbl.lower()}" + (f" à {time_lbl}" if time_lbl else "") + ".",
                        "user_text": prompt,
                        "planning_id": repas.id,
                        "detected_product": {
                            "id": new_p.id,
                            "nom": new_p.nom,
                            "prix": float(new_p.prix_base),
                            "prix_formate": f"{float(new_p.prix_base):,.0f} FCFA".replace(",", " "),
                            "image_url": new_p.image_url or "assets/images/thieboudienne.jpg",
                            "etablissement_id": new_e.id,
                            "etablissement_nom": new_e.nom
                        },
                        "detected_establishment": {
                            "id": new_e.id,
                            "nom": new_e.nom,
                            "adresse": new_e.adresse or "Dakar"
                        },
                        "suggested_actions": [
                            {"label": "Voir mon planning", "action": "VIEW_PLANNING", "planning_id": repas.id}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data, product=new_p)
                except RepasPlanifie.DoesNotExist:
                    return Response({"detail": "Le planning à modifier est introuvable ou appartient à un autre compte."}, status=status.HTTP_404_NOT_FOUND)

        if force_action == 'CONFIRM_PLANNING' or (awaiting_confirmation and is_confirm_word):
            p_id = pending_selection.get('product_id') if pending_selection else None
            if not p_id and context_product:
                p_id = context_product.id
            if not p_id and selected_product and isinstance(selected_product, dict):
                p_id = selected_product.get('id')

            if not p_id:
                res_data = {
                    "status": "missing_info",
                    "intent": "CREATE_PLANNING",
                    "message": "Aucun plat n'a encore été sélectionné pour la planification. Veuillez d'abord choisir un plat.",
                    "user_text": prompt,
                    "suggested_actions": [
                        {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"},
                        {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

            date_iso = (pending_selection and pending_selection.get('date_iso')) or last_dt.get('date_iso')
            date_lbl = (pending_selection and pending_selection.get('date_label')) or last_dt.get('date_label')
            time_lbl = (pending_selection and pending_selection.get('time_label')) or last_dt.get('time_label')
            creneau_val = (pending_selection and pending_selection.get('creneau')) or last_dt.get('creneau')

            try:
                prod = Produit.objects.select_related('etablissement').get(id=p_id)
                est = prod.etablissement
            except Produit.DoesNotExist:
                return Response({"detail": "Le produit sélectionné n'existe plus en base."}, status=status.HTTP_400_BAD_REQUEST)

            if not date_iso or not time_lbl:
                return self._get_missing_info_response(
                    conversation, prompt, product=prod,
                    date_iso=date_iso, date_label=date_lbl, time_label=time_lbl
                )

            from apps.orders.models import RepasPlanifie
            prix_val = (pending_selection and pending_selection.get('prix')) or float(prod.prix_base)

            # Protection anti-double submit : recherche un planning identique déjà créé
            repas_existant = None
            if user:
                repas_existant = RepasPlanifie.objects.filter(
                    utilisateur=user,
                    produit=prod,
                    etablissement=est,
                    date_planifiee=date_iso,
                    creneau=creneau_val
                ).exclude(statut=RepasPlanifie.STATUT_ANNULE).first()

                if not repas_existant:
                    repas_existant = RepasPlanifie.objects.create(
                        utilisateur=user,
                        produit=prod,
                        etablissement=est,
                        date_planifiee=date_iso,
                        creneau=creneau_val,
                        prix_total=prix_val,
                        quantite=1,
                        instructions=pending_selection.get('options', ''),
                        statut=RepasPlanifie.STATUT_PLANIFIE
                    )

            ctx['pending_selection'] = None
            ctx['awaiting_confirmation'] = False
            ctx['selected_product'] = None
            r_id = repas_existant.id if repas_existant else None

            res_data = {
                "status": "planning_created",
                "intent": "CONFIRM_PLANNING",
                "message": f"C'est fait ! Votre repas de {prod.nom} chez {est.nom} est planifié {date_lbl.lower()} à {time_lbl}.",
                "user_text": prompt,
                "planning_id": r_id,
                "detected_product": {
                    "id": prod.id,
                    "nom": prod.nom,
                    "prix": prix_val,
                    "prix_formate": f"{prix_val:,.0f} FCFA".replace(",", " "),
                    "image_url": prod.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_id": est.id,
                    "etablissement_nom": est.nom
                },
                "detected_establishment": {
                    "id": est.id,
                    "nom": est.nom,
                    "adresse": est.adresse or "Dakar"
                },
                "detected_datetime": {
                    "date_iso": date_iso,
                    "date_label": date_lbl,
                    "time_label": time_lbl,
                    "creneau": creneau_val
                },
                "suggested_actions": [
                    {"label": "Voir mon planning", "action": "VIEW_PLANNING", "planning_id": r_id}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=prod)

        # -------------------------------------------------------------
        # ACTION 2.5: RÉSOLUTION CONTEXTUELLE D'ANAPHORES & DE RÉFÉRENCES
        # ("le premier", "le deuxième", "le troisième", "le dernier", "le moins cher", "le plus cher", "il coute combien")
        # -------------------------------------------------------------
        ref_words = ['premier', '1er', '1ere', 'première', 'deuxième', '2ème', '2eme', 'deuxieme', 'troisième', '3ème', '3eme', 'troisieme', 'dernier', 'dernière', 'moins cher', 'plus cher', 'ce plat', 'ce restaurant']
        has_ref_word = any(w in prompt_lower for w in ref_words)

        if has_ref_word and not force_action:
            items = []
            res_type = 'product'
            if last_results and last_results.get('items'):
                items = last_results['items']
                res_type = last_results.get('type', 'product_search')
            elif last_matching_ests:
                items = last_matching_ests
                res_type = 'restaurant_search'
            elif last_products:
                items = last_products
                res_type = 'product_search'

            target_idx = None
            if any(w in prompt_lower for w in ['troisième', '3ème', '3eme', 'troisieme']):
                target_idx = 2
            elif any(w in prompt_lower for w in ['deuxième', '2ème', '2eme', 'deuxieme']):
                target_idx = 1
            elif any(w in prompt_lower for w in ['premier', '1er', '1ere', 'première']):
                target_idx = 0
            elif any(w in prompt_lower for w in ['dernier', 'dernière']):
                target_idx = len(items) - 1 if items else None
            elif 'moins cher' in prompt_lower and items:
                sorted_items = sorted(items, key=lambda x: float(x.get('prix', 0) or 0))
                target_idx = items.index(sorted_items[0])
            elif 'plus cher' in prompt_lower and items:
                sorted_items = sorted(items, key=lambda x: float(x.get('prix', 0) or 0), reverse=True)
                target_idx = items.index(sorted_items[0])

            if target_idx is not None:
                # ANTI-HALLUCINATION BOUNDS CHECK
                if not items or target_idx >= len(items) or target_idx < -len(items):
                    unit_name = "restaurants" if res_type == 'restaurant_search' else "plats"
                    res_data = {
                        "status": "out_of_bounds",
                        "intent": "ANAPHORA_RESOLUTION",
                        "message": f"Je n'ai que {len(items)} {unit_name} dans les résultats actuels.",
                        "user_text": prompt,
                        "suggested_actions": []
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

                selected_item = items[target_idx]
                if res_type == 'restaurant_search':
                    ctx['selected_restaurant'] = selected_item
                    res_data = {
                        "status": "restaurant_selected",
                        "intent": "SELECT_RESTAURANT",
                        "type": "catalog_results",
                        "entity": "restaurant",
                        "message": f"Vous avez sélectionné le restaurant {selected_item['nom']} ({selected_item.get('adresse', 'Dakar')}). Souhaitez-vous voir ses plats ?",
                        "user_text": prompt,
                        "detected_establishment": selected_item,
                        "suggested_actions": [
                            {"label": "Voir ses plats", "action": "SHOW_RESTAURANT_DISHES"},
                            {"label": "← Retour aux restaurants", "action": "BACK_TO_RESTAURANTS"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)
                else:
                    ctx['selected_product'] = selected_item
                    ctx['last_selected_product_id'] = selected_item['id']

                    date_iso = last_dt.get('date_iso')
                    date_lbl = last_dt.get('date_label')
                    time_lbl = last_dt.get('time_label')
                    creneau_val = last_dt.get('creneau')

                    prix_num = float(selected_item.get('prix', 0))
                    prix_fmt = selected_item.get('prix_formate') or f"{prix_num:,.0f} FCFA".replace(",", " ")
                    est_nom = selected_item.get('etablissement_nom', 'AYYOU')

                    if date_iso and time_lbl:
                        pending_selection = {
                            "product_id": selected_item['id'],
                            "product_nom": selected_item['nom'],
                            "establishment_id": selected_item.get('etablissement_id'),
                            "establishment_nom": est_nom,
                            "establishment_adresse": selected_item.get('etablissement_adresse', 'Dakar'),
                            "prix": prix_num,
                            "prix_formate": prix_fmt,
                            "image_url": selected_item.get('image_url', 'assets/images/thieboudienne.jpg'),
                            "date_iso": date_iso,
                            "date_label": date_lbl,
                            "time_label": time_lbl,
                            "creneau": creneau_val
                        }
                        ctx['pending_selection'] = pending_selection
                        ctx['awaiting_confirmation'] = True
                        msg_confirm = f"Vous avez sélectionné le plat '{selected_item['nom']}' ({prix_fmt}) chez {est_nom}.\n\nJe vous propose de planifier ce repas {date_lbl.lower()} à {time_lbl}. Voulez-vous confirmer ?"
                        actions = [
                            {"label": "Oui, planifier", "action": "CONFIRM_PLANNING"},
                            {"label": "Non", "action": "DECLINE_PLANNING"}
                        ]
                    else:
                        msg_confirm = f"Vous avez sélectionné le plat '{selected_item['nom']}' ({prix_fmt}) chez {est_nom}."
                        if not date_iso and not time_lbl:
                            msg_confirm += " Pour quelle date et à quelle heure souhaitez-vous planifier ce repas ?"
                        elif not date_iso:
                            msg_confirm += " Pour quelle date souhaitez-vous planifier ce repas ?"
                        else:
                            msg_confirm += " À quelle heure souhaitez-vous planifier ce repas ?"
                        actions = [
                            {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
                        ]

                    res_data = {
                        "status": "food_selected",
                        "intent": "SELECT_PRODUCT",
                        "message": msg_confirm,
                        "user_text": prompt,
                        "detected_product": selected_item,
                        "detected_datetime": last_dt if (date_iso and time_lbl) else None,
                        "suggested_actions": actions
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # ACTION 2.6: DEMANDE DE PRIX ("Il coûte combien ?")
        # -------------------------------------------------------------
        is_price_query = any(w in prompt_lower for w in ['combien', 'prix', 'tarif', 'coûte', 'coute']) and not any(k in prompt_lower for k in ['budget', 'moins de', 'max', 'autour de'])
        if is_price_query:
            sel_prod = ctx.get('selected_product') or pending_selection
            sel_resto = ctx.get('selected_restaurant')
            if sel_prod:
                px = float(sel_prod.get('prix', 0))
                px_fmt = sel_prod.get('prix_formate') or f"{px:,.0f} FCFA".replace(",", " ")
                p_nom = sel_prod.get('nom') or sel_prod.get('product_nom')
                e_nom = sel_prod.get('etablissement_nom') or sel_prod.get('establishment_nom', 'AYYOU')
                res_data = {
                    "status": "price_info",
                    "intent": "PRODUCT_SEARCH",
                    "message": f"Le plat '{p_nom}' est proposé au prix de {px_fmt} chez {e_nom}.",
                    "user_text": prompt,
                    "detected_product": sel_prod,
                    "suggested_actions": [
                        {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)
            elif sel_resto:
                res_data = {
                    "status": "price_info",
                    "intent": "RESTAURANT_SEARCH",
                    "message": f"Chez {sel_resto['nom']}, les prix des plats sont très accessibles. Vous pouvez consulter la liste de ses plats pour voir le tarif de chaque option.",
                    "user_text": prompt,
                    "detected_establishment": sel_resto,
                    "suggested_actions": [
                        {"label": "Voir ses plats", "action": "SHOW_RESTAURANT_DISHES"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # ACTION 3: SELECT_RESTAURANT (Sélection d'un restaurant réel)
        # -------------------------------------------------------------
        if (force_action == 'SELECT_RESTAURANT' or req_product_id or req_establishment_id) and force_action != 'CREATE_PLANNING':
            if req_establishment_id and not req_product_id:
                from apps.catalog.catalog_service import CatalogSearchService
                est_info = CatalogSearchService.get_establishment(req_establishment_id)
                if est_info:
                    dishes_res = CatalogSearchService.get_establishment_products(establishment_id=req_establishment_id)
                    items = dishes_res.get('results', [])
                    ctx['previous_results'] = last_results or {"type": "restaurant_search", "items": last_matching_ests}
                    ctx['last_results'] = {"type": "restaurant_dishes", "restaurant": est_info, "items": items}
                    ctx['selected_restaurant'] = est_info
                    res_data = {
                        "status": "restaurant_dishes",
                        "intent": "PRODUCT_SEARCH",
                        "type": "catalog_results",
                        "entity": "product",
                        "message": f"Voici les plats disponibles chez {est_info['nom']} :",
                        "user_text": prompt,
                        "matching_products": items,
                        "detected_establishment": est_info,
                        "suggested_actions": [
                            {"label": "← Retour aux restaurants", "action": "BACK_TO_RESTAURANTS"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data, matching_products=items)

            prod_target = None
            if req_product_id:
                try:
                    prod_target = Produit.objects.select_related('etablissement').get(id=req_product_id)
                except Produit.DoesNotExist:
                    prod_target = None

            if prod_target:
                est_target = prod_target.etablissement
                prix_num = float(prod_target.prix_base)

                ctx['selected_product'] = {
                    "id": prod_target.id,
                    "nom": prod_target.nom,
                    "prix": prix_num,
                    "etablissement_id": est_target.id if est_target else None,
                    "etablissement_nom": est_target.nom if est_target else "AYYOU"
                }
                ctx['last_selected_product_id'] = prod_target.id

                date_iso = last_dt.get('date_iso')
                date_lbl = last_dt.get('date_label')
                time_lbl = last_dt.get('time_label')
                creneau_val = last_dt.get('creneau')

                if date_iso and time_lbl:
                    pending_selection = {
                        "product_id": prod_target.id,
                        "product_nom": prod_target.nom,
                        "establishment_id": est_target.id if est_target else None,
                        "establishment_nom": est_target.nom if est_target else "AYYOU",
                        "establishment_adresse": est_target.adresse if est_target else "Dakar",
                        "prix": prix_num,
                        "prix_formate": f"{prix_num:,.0f} FCFA".replace(",", " "),
                        "image_url": prod_target.image_url or "assets/images/thieboudienne.jpg",
                        "date_iso": date_iso,
                        "date_label": date_lbl,
                        "time_label": time_lbl,
                        "creneau": creneau_val
                    }
                    ctx['pending_selection'] = pending_selection
                    ctx['awaiting_confirmation'] = True
                    msg_confirm = f"Vous avez sélectionné {est_target.nom if est_target else 'AYYOU'} pour votre {prod_target.nom}.\n\nJe vous propose de planifier ce repas {date_lbl.lower()} à {time_lbl}. Voulez-vous confirmer ?"
                    actions = [
                        {"label": "Oui, planifier", "action": "CONFIRM_PLANNING"},
                        {"label": "Non", "action": "DECLINE_PLANNING"}
                    ]
                else:
                    msg_confirm = f"Vous avez sélectionné {est_target.nom if est_target else 'AYYOU'} pour votre {prod_target.nom}."
                    if not date_iso and not time_lbl:
                        msg_confirm += " Pour quelle date et à quelle heure souhaitez-vous planifier ce repas ?"
                    elif not date_iso:
                        msg_confirm += " Pour quelle date souhaitez-vous planifier ce repas ?"
                    else:
                        msg_confirm += " À quelle heure souhaitez-vous planifier ce repas ?"
                    actions = [
                        {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
                    ]

                res_data = {
                    "status": "restaurant_selected",
                    "intent": "SELECT_RESTAURANT",
                    "message": msg_confirm,
                    "user_text": prompt,
                    "detected_product": {
                        "id": prod_target.id,
                        "nom": prod_target.nom,
                        "prix": prix_num,
                        "prix_formate": f"{prix_num:,.0f} FCFA".replace(",", " "),
                        "image_url": prod_target.image_url or "assets/images/thieboudienne.jpg",
                        "etablissement_id": est_target.id if est_target else None,
                        "etablissement_nom": est_target.nom if est_target else "AYYOU"
                    },
                    "detected_establishment": {
                        "id": est_target.id if est_target else None,
                        "nom": est_target.nom if est_target else "AYYOU",
                        "adresse": est_target.adresse if est_target else "Dakar"
                    } if est_target else None,
                    "detected_datetime": last_dt if (date_iso and time_lbl) else None,
                    "suggested_actions": actions
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=prod_target)

        # Résolution contextuelle ("le deuxième", "le premier", "il coute combien", "planifie-le")
        if not context_product and last_selected_product_id:
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=last_selected_product_id)
            except Produit.DoesNotExist:
                context_product = None

        if any(ref in prompt_lower for ref in ['deuxième', '2eme', '2ème', 'deuxieme']) and len(last_products) >= 2:
            prod_info = last_products[1]
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=prod_info['id'])
                ctx['last_selected_product_id'] = context_product.id
                conversation.context_data = ctx
                conversation.save()
            except Produit.DoesNotExist:
                pass
        elif any(ref in prompt_lower for ref in ['premier', '1er', '1ere']) and len(last_products) >= 1:
            prod_info = last_products[0]
            try:
                context_product = Produit.objects.select_related('etablissement', 'categorie').get(id=prod_info['id'])
                ctx['last_selected_product_id'] = context_product.id
                conversation.context_data = ctx
                conversation.save()
            except Produit.DoesNotExist:
                pass

        if context_product and ('combien' in prompt_lower or 'prix' in prompt_lower or 'tarif' in prompt_lower) and not any(k in prompt_lower for k in ['budget', 'moins de', 'max']):
            prix_val = float(context_product.prix_base)
            res_data = {
                "status": "food_search",
                "intent": "FOOD_SEARCH",
                "message": f"Le plat '{context_product.nom}' est proposé au prix de {prix_val:,.0f} FCFA chez {context_product.etablissement.nom if context_product.etablissement else 'AYYOU'}.",
                "user_text": prompt,
                "detected_product": {
                    "id": context_product.id,
                    "nom": context_product.nom,
                    "prix": prix_val,
                    "prix_formate": f"{prix_val:,.0f} FCFA".replace(",", " "),
                    "image_url": context_product.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_nom": context_product.etablissement.nom if context_product.etablissement else "AYYOU"
                },
                "suggested_actions": [
                    {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=context_product)

        # -------------------------------------------------------------
        # 1. INTENT = GREETING (Salutations simples : Bonjour, Salut, etc.)
        # -------------------------------------------------------------
        greeting_words = {'bonjour', 'salut', 'coucou', 'hello', 'bonsoir', 'hey', 'bonjour !', 'salut !', 'bonjour 👋'}
        clean_prompt = prompt_lower.strip()
        clean_words = set(re.findall(r'\b\w+\b', prompt_lower))
        is_pure_greeting = clean_prompt in greeting_words or bool(clean_words.intersection(greeting_words))
        has_food_or_action = any(w in prompt_lower for w in ['plat', 'restaurant', 'manger', 'repas', 'planifie', 'planifier', 'combien', 'budget', 'fcfa', 'menu', 'carte', 'commande', 'livraison', 'code', 'django', 'thieb', 'burger', 'pizza', 'poulet'])

        if is_pure_greeting and not has_food_or_action:
            res_data = {
                "status": "greeting",
                "intent": "GREETING",
                "message": "Bonjour 👋 Je suis AYYOU Copilote. Je peux vous aider à trouver des plats, rechercher des restaurants, comparer des options selon votre budget ou planifier vos repas. Que souhaitez-vous faire ?",
                "user_text": prompt,
                "suggested_actions": [
                    {"label": "Découvrir des restaurants", "action": "RESTAURANT_SEARCH"},
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 2. INTENT = CAPABILITIES (Demande des capacités du Copilote)
        # -------------------------------------------------------------
        if any(phrase in prompt_lower for phrase in ['que peux tu faire', 'que peux-tu faire', 'que sais tu faire', 'que sais-tu faire', 'qu\'est ce que tu sais faire', 'qu\'est-ce que tu sais faire', 'tes capacités', 'comment tu m\'aides', 'qu\'est-ce que tu peux faire']):
            res_data = {
                "status": "capabilities",
                "intent": "CAPABILITIES",
                "message": "Je suis AYYOU Copilote, votre assistant conversationnel alimentaire intelligent. Voici tout ce que je peux faire pour vous :\n\n• 🏪 **Découvrir des restaurants** par catégorie ou par quartier\n• 🍲 **Rechercher des plats** et spécialités (Thiéboudienne, Yassa, Burgers...)\n• 💰 **Filtrer selon votre budget** (ex: repas à moins de 3 000 FCFA)\n• 📅 **Planifier des repas** pour des dates et heures précises\n• 🚚 **Suivre vos commandes** et livraisons en direct\n• 📸 **Analyser vos photos de plats** grâce à l'IA Vision Moondream",
                "user_text": prompt,
                "suggested_actions": [
                    {"label": "Découvrir les restaurants", "action": "RESTAURANT_SEARCH"},
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 3. INTENT = GENERAL_CONVERSATION (Conversations génériques)
        # -------------------------------------------------------------
        if any(phrase in prompt_lower for phrase in ['comment vas tu', 'comment vas-tu', 'comment ca va', 'comment ça va', 'ça va', 'ca va']) and not has_food_or_action:
            res_data = {
                "status": "general_conversation",
                "intent": "GENERAL_CONVERSATION",
                "message": "Je vais très bien, merci ! Avez-vous une envie gourmande ou souhaitez-vous découvrir des restaurants aujourd'hui ?",
                "user_text": prompt,
                "suggested_actions": [
                    {"label": "Découvrir les restaurants", "action": "RESTAURANT_SEARCH"},
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 4. INTENT = OUT_OF_SCOPE (Refus technique & Sécurité anti-injection)
        # -------------------------------------------------------------
        tech_keywords = [
            'django', 'angular', 'postgres', 'postgresql', 'sql', 'code', 'source', 
            'permission', 'secret', 'architecture', 'prompt système', 'system prompt', 
            'modèle', 'modele', 'admin', 'password', 'mot de passe', 'api key', 'env', 
            'drop table', 'select *', 'delete from', 'script', 'eval', 'exec', 'token', 'key'
        ]
        if any(w in prompt_lower for w in tech_keywords) and not any(w in prompt_lower for w in ['plat', 'restaurant', 'manger', 'repas', 'commande', 'menu']):
            res_data = {
                "status": "out_of_scope",
                "intent": "OUT_OF_SCOPE",
                "message": "Je suis l'assistant alimentaire AYYOU. Je peux vous aider avec la découverte de plats, les restaurants, le budget, la planification et le conseil culinaire, mais pas avec les informations techniques internes de l'application.",
                "user_text": prompt,
                "suggested_actions": []
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 5. INTENT = BUDGET_DISCOVERY (Expression d'un budget seul "J'ai 5000 FCFA")
        # -------------------------------------------------------------
        clean_prompt_num = re.sub(r'\s+', '', prompt_lower)
        standalone_budget = re.search(r'^(?:j\'ai|j`ai|budget|monbudgetestde|monbudget:?|avec)?(\d+)(?:fcfa|f|cfa|francs)?\.?$', clean_prompt_num)
        if standalone_budget and not any(w in prompt_lower for w in ['planifie', 'planifier', 'manger', 'plat', 'poulet', 'thieb', 'burger', 'pizza']):
            budget_val = float(standalone_budget.group(1))
            ctx['last_budget'] = budget_val
            conversation.context_data = ctx
            conversation.save()

            res_data = {
                "status": "budget_discovery",
                "intent": "BUDGET_DISCOVERY",
                "message": f"Très bien ! Avec un budget de {budget_val:,.0f} FCFA, que souhaitez-vous manger ? Vous pouvez rechercher des plats ou découvrir les restaurants dans cette tranche de prix.".replace(',', ' '),
                "user_text": prompt,
                "suggested_actions": [
                    {"label": "Voir les plats disponibles", "action": "FOOD_SEARCH"},
                    {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 6. INTENT = APP_FOOD_HELP (Aide utilisation application)
        # -------------------------------------------------------------
        if any(phrase in prompt_lower for phrase in ['comment trouver un restaurant', 'comment commander', 'comment voir mon planning', 'comment fonctionne', 'aide moi sur l\'application']):
            res_data = {
                "status": "app_help",
                "intent": "APP_FOOD_HELP",
                "message": "Sur AYYOU, vous pouvez rechercher des plats par budget, découvrir les restaurants de Dakar par catégorie, planifier vos repas en avance ou suivre vos commandes en direct depuis votre espace client.",
                "user_text": prompt,
                "suggested_actions": [
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"},
                    {"label": "Découvrir les restaurants", "action": "RESTAURANT_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 7. INTENT = GENERAL_FOOD_HELP (Trivia culinaire, explications de spécialités sénégalaises/africaines)
        # -------------------------------------------------------------
        food_explanation_phrases = ['c\'est quoi le', 'c\'est quoi la', 'explique moi', 'explique-moi', 'qu\'est ce que le', 'qu\'est ce que la', 'définition de', 'recette de', 'plat traditionnel', 'spécialité sénégalaise']
        is_food_trivia = any(phrase in prompt_lower for phrase in food_explanation_phrases)
        if is_food_trivia:
            trivia_key = None
            for key in ['thieb', 'thiéboudienne', 'thieboudienne', 'yassa', 'mafe', 'mafé', 'dibi', 'pastels', 'soupou', 'kandia', 'attieke', 'attiéké', 'garba', 'placali']:
                if key in prompt_lower:
                    trivia_key = key
                    break
            
            explanations = {
                'thieb': "Le Thiéboudienne (Ceebu Jën) est le plat national sénégalais. Il se compose de riz cuit dans un bouillon de poisson au concentré de tomate, accompagné de légumes frais (cassave, chou, carotte, aubergine, piment) et du fameux rof (farce aux herbes et à l'ail).",
                'yassa': "Le Yassa est une spécialité sénégalaise emblématique préparée à base d'oignons caramélisés, de moutarde, de jus de citron vert et de piment, servi avec du poulet grillé ou du poisson accompagnant du riz blanc.",
                'mafe': "Le Mafé est une sauce généreuse à la pâte d'arachide mijotée avec de la viande (bœuf ou agneau) et des légumes, servie sur un lit de riz blanc chaud.",
                'dibi': "Le Dibi est une grillade traditionnelle sénégalaise de viande d'agneau assaisonnée, cuite au feu de bois dans les dibiteries et servie avec des oignons tranchés et de la moutarde.",
                'pastels': "Les Pastels sont des beignets croustillants sénégalais farcis au poisson épicé ou à la viande, généralement accompagnés d'une sauce tomate-oignon pimentée.",
                'attieke': "L'Attiéké est une semoule de manioc cuite à la vapeur, légèrement acidulée, traditionnellement accompagnée de poisson grillé et d'une aloko ou salade fraîche."
            }
            
            explanation_text = explanations.get(trivia_key or 'thieb', "Les plats sénégalais et africains sont riches en saveurs, cuisinés avec des produits frais locaux comme le poisson thiof, les viandes grillées au feu de bois et les sauces cuisinées avec soin.")
            
            matched_prod, searched_term = self._find_matching_product(prompt)
            term_to_search = searched_term or trivia_key or "thieb"
            qs_prods = search_food(query=term_to_search, limit=5)

            res_data = {
                "status": "food_help",
                "intent": "GENERAL_FOOD_HELP",
                "message": f"{explanation_text}\n\nVoici les restaurants AYYOU qui proposent ces spécialités :",
                "user_text": prompt,
                "matching_products": qs_prods,
                "suggested_actions": [
                    {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 7.4. INTENT = FOOD_RECOMMENDATION (Ingrédients / "Avec ces ingrédients, qu'est-ce que je peux manger ?")
        # -------------------------------------------------------------
        is_ingredient_query = any(w in prompt_lower for w in [
            'ingrédient', 'ingrédients', 'ingredient', 'ingredients',
            'qu\'est-ce que je peux manger avec', 'que puis-je manger avec', 'que peux-tu me proposer avec'
        ]) or ('manger' in prompt_lower and 'avec' in prompt_lower and ('des' in prompt_lower or 'du' in prompt_lower or 'de' in prompt_lower))

        if is_ingredient_query:
            ingredient_keywords = {
                'riz': ['riz', 'ceebu', 'thieb', 'yassa', 'mafe'],
                'poisson': ['poisson', 'thiof', 'ceebu', 'thieb', 'kandia', 'attieke'],
                'poulet': ['poulet', 'yassa'],
                'viande': ['viande', 'boeuf', 'bœuf', 'agneau', 'dibi', 'mafe'],
                'oignon': ['oignon', 'oignons', 'yassa'],
                'oignons': ['oignon', 'oignons', 'yassa'],
                'arachide': ['mafe', 'pâte d\'arachide', 'arachide'],
                'gombo': ['kandia', 'soupou kandia', 'gombo'],
                'attieke': ['attieke', 'attiéké'],
                'attiéké': ['attieke', 'attiéké'],
                'legumes': ['légumes', 'legumes', 'carotte', 'chou', 'manioc']
            }

            detected_ing_tokens = [ing for ing in ingredient_keywords if ing in prompt_lower]

            if not detected_ing_tokens and ('ingrédient' in prompt_lower or 'ingredient' in prompt_lower):
                res_data = {
                    "status": "food_recommendation",
                    "intent": "FOOD_RECOMMENDATION",
                    "type": "question",
                    "message": "Quels ingrédients possédez-vous (par exemple : riz, poisson, poulet, viande, oignons, gombo...) ? Dites-le moi et je vous proposerai les plats parfaits correspondants dans le catalogue AYYOU !",
                    "user_text": prompt,
                    "suggested_actions": [
                        {"label": "Rechercher des plats", "action": "FOOD_SEARCH"},
                        {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

            if detected_ing_tokens:
                search_terms_set = set()
                for ing in detected_ing_tokens:
                    search_terms_set.update(ingredient_keywords[ing])

                all_prods = Produit.objects.select_related('etablissement', 'categorie').filter(est_disponible=True)
                scored_prods = []
                for p in all_prods:
                    p_text = f"{p.nom} {p.description or ''} {p.categorie.nom if p.categorie else ''}".lower()
                    s = sum(50 for term in search_terms_set if term in p_text)
                    if s > 0:
                        scored_prods.append((s, p))

                scored_prods.sort(key=lambda x: x[0], reverse=True)
                if scored_prods:
                    best_product = scored_prods[0][1]
                    time_str = last_dt.get('time_label', '12h30') if last_dt else '12h30'
                    res_data = {
                        "status": "food_recommendation",
                        "intent": "FOOD_RECOMMENDATION",
                        "type": "catalog_results",
                        "entity": "product",
                        "message": f"Avec ces ingrédients ({', '.join(detected_ing_tokens)}), voici le plat idéal du catalogue AYYOU que je vous recommande :",
                        "user_text": prompt,
                        "detected_product": {
                            "id": best_product.id,
                            "nom": best_product.nom,
                            "description": best_product.description or f"Plat préparé avec des ingrédients de qualité chez {best_product.etablissement.nom if best_product.etablissement else 'AYYOU'}.",
                            "prix": float(best_product.prix_base),
                            "prix_formate": f"{float(best_product.prix_base):,.0f} FCFA".replace(",", " "),
                            "image_url": best_product.image_url or "assets/images/thieboudienne.jpg",
                            "etablissement_id": best_product.etablissement.id if best_product.etablissement else None,
                            "etablissement_nom": best_product.etablissement.nom if best_product.etablissement else "AYYOU",
                            "etablissement_adresse": best_product.etablissement.adresse if best_product.etablissement else "Dakar Plateau"
                        },
                        "suggested_actions": [
                            {"label": f"Planifier {time_str}", "action": "CREATE_PLANNING"},
                            {"label": "Commander", "action": "FOOD_SEARCH"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data, product=best_product)

        # -------------------------------------------------------------
        # 7.5. INTENT = FOOD_RECOMMENDATION ("Qu'est-ce que tu me recommandes...")
        # -------------------------------------------------------------
        is_rec_query = any(w in prompt_lower for w in ['recommande', 'recommandation', 'recommandes', 'suggères', 'suggère', 'idée', 'idee', 'coup de coeur', 'coup de cœur'])
        if is_rec_query:
            rec_product, _ = self._find_matching_product(prompt)
            if not rec_product:
                rec_product = Produit.objects.select_related('etablissement', 'categorie').filter(est_disponible=True).first()

            if rec_product:
                time_str = last_dt.get('time_label', '12h30') if last_dt else '12h30'
                res_data = {
                    "status": "food_recommendation",
                    "intent": "FOOD_RECOMMENDATION",
                    "type": "catalog_results",
                    "entity": "product",
                    "message": f"Je vous suggère notre coup de cœur du jour, équilibré, chaud et prêt pour votre créneau de {time_str} :",
                    "user_text": prompt,
                    "detected_product": {
                        "id": rec_product.id,
                        "nom": rec_product.nom,
                        "description": rec_product.description or f"Plat savoureux préparé avec des ingrédients frais chez {rec_product.etablissement.nom if rec_product.etablissement else 'AYYOU'}.",
                        "prix": float(rec_product.prix_base),
                        "prix_formate": f"{float(rec_product.prix_base):,.0f} FCFA".replace(",", " "),
                        "image_url": rec_product.image_url or "assets/images/thieboudienne.jpg",
                        "etablissement_id": rec_product.etablissement.id if rec_product.etablissement else None,
                        "etablissement_nom": rec_product.etablissement.nom if rec_product.etablissement else "AYYOU",
                        "etablissement_adresse": rec_product.etablissement.adresse if rec_product.etablissement else "Dakar Plateau"
                    },
                    "suggested_actions": [
                        {"label": f"Planifier {time_str}", "action": "CREATE_PLANNING"},
                        {"label": "Commander", "action": "FOOD_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=rec_product)
            else:
                res_data = {
                    "status": "food_recommendation",
                    "intent": "FOOD_RECOMMENDATION",
                    "type": "catalog_results",
                    "entity": "product",
                    "message": "Je peux vous proposer des plats disponibles selon votre budget ou catégorie, mais je n'ai pas suffisamment de données dans le catalogue pour établir une recommandation personnalisée.",
                    "user_text": prompt,
                    "suggested_actions": [
                        {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 8. INTENT = RESTAURANT_DISCOVERY & CATEGORY_SEARCH
        # -------------------------------------------------------------
        is_discovery_query = any(phrase in prompt_lower for phrase in ['propose-moi des restaurants', 'propose moi des restaurants', 'quels sont les restaurants', 'quels restaurants sont disponibles', 'découvrir des restaurants', 'quelles sont les catégories', 'découvrir les catégories', 'où manger', 'bons endroits'])
        matched_prod, searched_term = self._find_matching_product(prompt)
        target_term = searched_term or last_searched_term

        # Check if prompt targets a category directly
        category_match = None
        active_cats = search_active_categories(limit=12)
        for cat in active_cats:
            if cat['nom'].lower() in prompt_lower or cat['slug'].lower() in prompt_lower:
                category_match = cat
                break

        if (is_discovery_query or (force_action == 'RESTAURANT_SEARCH' and not target_term)) and not category_match:
            paginated_ests = search_establishments_paginated(limit=req_limit, offset=req_offset)
            top_ests = paginated_ests["results"]
            res_data = {
                "status": "restaurant_search",
                "intent": "RESTAURANT_DISCOVERY",
                "type": "catalog_results",
                "entity": "restaurant",
                "message": "Voici les catégories et les établissements disponibles sur AYYOU à Dakar. Cliquez sur un restaurant pour explorer son profil ou son menu :",
                "user_text": prompt,
                "suggested_categories": active_cats,
                "matching_establishments": top_ests,
                "total_count": paginated_ests["total_count"],
                "has_more": paginated_ests["has_more"],
                "remaining_count": paginated_ests.get("remaining_count", 0),
                "offset": paginated_ests["offset"],
                "limit": paginated_ests["limit"],
                "suggested_actions": [
                    {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        if category_match:
            paginated_cat_food = search_food_paginated(category_slug=category_match['slug'], limit=req_limit, offset=req_offset)
            cat_prods = paginated_cat_food["results"]
            res_data = {
                "status": "category_search",
                "intent": "CATEGORY_SEARCH",
                "type": "catalog_results",
                "entity": "product",
                "message": f"Voici la sélection de la catégorie '{category_match['nom']}' disponible sur AYYOU :",
                "user_text": prompt,
                "matching_products": cat_prods,
                "total_count": paginated_cat_food["total_count"],
                "has_more": paginated_cat_food["has_more"],
                "remaining_count": paginated_cat_food.get("remaining_count", 0),
                "offset": paginated_cat_food["offset"],
                "limit": paginated_cat_food["limit"],
                "suggested_actions": []
            }
            return self._save_message_and_respond(conversation, prompt, res_data)

        # -------------------------------------------------------------
        # 9. INTENT = RESTAURANT_SEARCH (Quels restaurants proposent un plat spécifique...)
        # -------------------------------------------------------------
        is_resto_query = any(phrase in prompt_lower for phrase in ['voir les restaurants', 'quels restaurants', 'où trouver', 'ou trouver', 'trouve moi un restaurant', 'trouve-moi un restaurant', 'quel restaurant', 'les restaurants', 'proposent des plats'])
        if (is_resto_query or force_action == 'RESTAURANT_SEARCH') and force_action != 'CREATE_PLANNING':
            if not target_term and (matched_prod or context_product):
                p_ref = matched_prod or context_product
                target_term = p_ref.nom

            clean_prompt_budget = re.sub(r'(\d+)\s+(\d{3})', r'\1\2', prompt_lower)
            budget_match_r = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)', clean_prompt_budget)
            if not budget_match_r:
                budget_match_r = re.search(r'(?:budget|moins de|max|maximum|autour de|avec)\s*(?:de\s*)?(\d+)', clean_prompt_budget)
            budget_val = float(budget_match_r.group(1)) if budget_match_r else None

            paginated_ests = search_establishments_paginated(
                query=target_term,
                max_price=budget_val,
                limit=req_limit,
                offset=req_offset
            )
            est_data = paginated_ests["results"]
            term_display = target_term or "vos envies"
            if budget_val:
                if target_term:
                    msg = f"Voici les restaurants AYYOU qui proposent du {term_display} avec un budget max de {budget_val:,.0f} FCFA :".replace(",", " ") if est_data else f"Je n'ai trouvé aucun restaurant AYYOU proposant du {term_display} dans la limite de {budget_val:,.0f} FCFA.".replace(",", " ")
                else:
                    msg = f"Voici les restaurants AYYOU ayant au moins un plat disponible dans la limite de {budget_val:,.0f} FCFA :".replace(",", " ") if est_data else f"Je n'ai trouvé aucun restaurant AYYOU proposant un plat dans la limite de {budget_val:,.0f} FCFA.".replace(",", " ")
            else:
                msg = f"Voici les restaurants AYYOU qui correspondent à '{term_display}' :" if est_data else f"Je n'ai trouvé aucun restaurant AYYOU proposant actuellement du {term_display}."

            ctx['last_matching_establishments'] = est_data
            if target_term:
                ctx['last_searched_term'] = target_term
            conversation.context_data = ctx

            res_data = {
                "status": "restaurant_search",
                "intent": "RESTAURANT_SEARCH",
                "type": "catalog_results",
                "entity": "restaurant",
                "message": msg,
                "user_text": prompt,
                "matching_establishments": est_data,
                "total_count": paginated_ests["total_count"],
                "has_more": paginated_ests["has_more"],
                "remaining_count": paginated_ests.get("remaining_count", 0),
                "offset": paginated_ests["offset"],
                "limit": paginated_ests["limit"],
                "detected_product": None,
                "detected_establishment": None,
                "suggested_actions": []
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=matched_prod if matched_prod else None, matching_establishments=est_data)

        # -------------------------------------------------------------
        # 10. INTENT = FOOD_SEARCH (Recherche par budget / Plats disponibles)
        # -------------------------------------------------------------
        clean_prompt_budget = re.sub(r'(\d+)\s+(\d{3})', r'\1\2', prompt_lower)
        budget_match = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)', clean_prompt_budget)
        if not budget_match:
            budget_match = re.search(r'(?:budget|moins de|max|maximum|autour de|avec)\s*(?:de\s*)?(\d+)', clean_prompt_budget)
        is_budget_query = bool(budget_match and any(kw in prompt_lower for kw in ['budget', 'moins de', 'max', 'maximum', 'autour de', 'fcfa', 'francs', 'cfa', 'avec', 'proposes', 'proposer']))
        is_food_search = any(phrase in prompt_lower for phrase in ['quels plats puis-je manger', 'quels plats sont disponibles', 'que puis-je manger', 'qu\'est-ce que tu me proposes', 'quels plats coûtent', 'rechercher des plats', 'je cherche un plat'])

        if (is_budget_query or is_food_search or force_action == 'FOOD_SEARCH') and force_action != 'CREATE_PLANNING':
            budget_val = float(budget_match.group(1)) if budget_match else None
            paginated_food = search_food_paginated(
                query=target_term,
                max_price=budget_val,
                limit=req_limit,
                offset=req_offset
            )
            prods = paginated_food["results"]
            total_cnt = paginated_food["total_count"]
            has_m = paginated_food["has_more"]
            rem_cnt = paginated_food.get("remaining_count", 0)

            # CAS 0 RÉSULTAT SOUS UN BUDGET PRÉCIS (P0-2.2)
            if budget_val and len(prods) == 0:
                closest_food = search_food_paginated(query=target_term, limit=3)
                closest_prods = closest_food.get("results", [])
                if target_term:
                    msg_text = f"Je n'ai trouvé aucun {target_term} à {budget_val:,.0f} FCFA ou moins.".replace(",", " ")
                    if closest_prods:
                        lowest_price = min(float(p.get('prix', 0) or 0) for p in closest_prods if p.get('prix'))
                        msg_text += f" Les options les plus proches pour '{target_term}' commencent à {lowest_price:,.0f} FCFA :".replace(",", " ")
                        prods = closest_prods
                        total_cnt = len(closest_prods)
                        has_m = False
                        rem_cnt = 0
                else:
                    msg_text = f"Je n'ai trouvé aucun plat disponible à {budget_val:,.0f} FCFA ou moins.".replace(",", " ")
                    if closest_prods:
                        lowest_price = min(float(p.get('prix', 0) or 0) for p in closest_prods if p.get('prix'))
                        msg_text += f" Les plats les plus accessibles sur AYYOU commencent à {lowest_price:,.0f} FCFA :".replace(",", " ")
                        prods = closest_prods
                        total_cnt = len(closest_prods)
                        has_m = False
                        rem_cnt = 0
            else:
                msg_text = f"Voici les plats disponibles sur AYYOU" + (f" pour un budget max de {budget_val:,.0f} FCFA :".replace(",", " ") if budget_val else " :")

            res_data = {
                "status": "food_search",
                "intent": "FOOD_SEARCH",
                "type": "catalog_results",
                "entity": "product",
                "message": msg_text,
                "user_text": prompt,
                "matching_products": prods,
                "total_count": total_cnt,
                "has_more": has_m,
                "remaining_count": rem_cnt,
                "offset": paginated_food["offset"],
                "limit": paginated_food["limit"],
                "detected_product": None,
                "detected_establishment": None,
                "suggested_actions": []
            }
            return self._save_message_and_respond(conversation, prompt, res_data, matching_products=prods)

        # -------------------------------------------------------------
        # 11.3. INTENT = DELETE_PLANNING (Suppression d'un repas planifié existant)
        # -------------------------------------------------------------
        delete_keywords = ['supprime', 'supprimer', 'efface', 'effacer', 'delete', 'retire', 'retirer']
        cancel_planning_keywords = ['annule', 'annuler', 'enleve', 'enlever']

        has_delete_word = any(w in prompt_lower for w in delete_keywords)
        has_cancel_plan_word = any(w in prompt_lower for w in cancel_planning_keywords) and not (awaiting_confirmation or awaiting_upd_confirm or ctx.get('awaiting_delete_confirmation')) and (
            'repas' in prompt_lower or 'planning' in prompt_lower or 'demain' in prompt_lower or 'midi' in prompt_lower or 'soir' in prompt_lower or bool(ctx.get('selectable_delete_plannings')) or bool(request.data.get('planning_id'))
        )

        is_delete_intent = force_action == 'DELETE_PLANNING' or has_delete_word or has_cancel_plan_word or bool(ctx.get('selectable_delete_plannings'))

        if is_delete_intent and not is_decline_word and not (awaiting_confirmation and is_confirm_word) and not awaiting_upd_confirm and not ctx.get('awaiting_delete_confirmation'):
            from apps.orders.models import RepasPlanifie
            req_plan_id = request.data.get('planning_id')
            target_planning = None

            if req_plan_id:
                if user:
                    try:
                        target_planning = RepasPlanifie.objects.select_related('produit', 'etablissement').get(id=req_plan_id, utilisateur=user)
                    except RepasPlanifie.DoesNotExist:
                        return Response({"detail": "Le repas planifié à supprimer est introuvable ou appartient à un autre compte."}, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({"detail": "Connexion requise pour cette action."}, status=status.HTTP_401_UNAUTHORIZED)

            selectable_delete_plannings = ctx.get('selectable_delete_plannings', [])
            if not target_planning and selectable_delete_plannings and user:
                sel_idx = None
                if any(w in prompt_lower for w in ['premier', '1er', '1ere', 'première', '1']):
                    sel_idx = 0
                elif any(w in prompt_lower for w in ['deuxième', '2ème', '2eme', 'deuxieme', '2']):
                    sel_idx = 1
                elif any(w in prompt_lower for w in ['troisième', '3ème', '3eme', 'troisieme', '3']):
                    sel_idx = 2

                if sel_idx is not None and sel_idx < len(selectable_delete_plannings):
                    chosen_p_id = selectable_delete_plannings[sel_idx].get('id')
                    try:
                        target_planning = RepasPlanifie.objects.select_related('produit', 'etablissement').get(id=chosen_p_id, utilisateur=user)
                        ctx['selectable_delete_plannings'] = None
                    except RepasPlanifie.DoesNotExist:
                        target_planning = None

            if not target_planning and user:
                user_plannings = RepasPlanifie.objects.filter(utilisateur=user).exclude(statut=RepasPlanifie.STATUT_ANNULE).select_related('produit', 'etablissement').order_by('date_planifiee', 'creneau')

                if parsed_target_date is not None:
                    user_plannings = user_plannings.filter(date_planifiee=parsed_target_date)

                matched_p, _ = self._find_matching_product(prompt)
                if matched_p:
                    user_plannings = user_plannings.filter(produit=matched_p)

                cnt = user_plannings.count()
                if cnt == 0:
                    res_data = {
                        "status": "no_planning_found",
                        "intent": "DELETE_PLANNING",
                        "message": "Vous n'avez aucun repas planifié correspondant à cette demande.",
                        "user_text": prompt,
                        "suggested_actions": [
                            {"label": "Voir mon planning", "action": "VIEW_PLANNING"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)
                elif cnt == 1:
                    target_planning = user_plannings.first()
                else:
                    plan_list = list(user_plannings)
                    ctx['selectable_delete_plannings'] = [{"id": p.id, "produit_nom": p.produit.nom, "etablissement_nom": p.etablissement.nom} for p in plan_list]
                    conversation.context_data = ctx
                    conversation.save()

                    options_msg = "Lequel de vos repas planifiés souhaitez-vous supprimer ?\n\n"
                    actions = []
                    for idx, p in enumerate(plan_list[:5], 1):
                        p_date_str = p.date_planifiee.strftime('%d/%m/%Y')
                        options_msg += f"{idx}. {p.produit.nom} chez {p.etablissement.nom} ({p_date_str})\n"
                        actions.append({"label": f"Supprimer Repas {idx}", "action": "DELETE_PLANNING", "planning_id": p.id})

                    res_data = {
                        "status": "disambiguate_delete_planning",
                        "intent": "DELETE_PLANNING",
                        "message": options_msg.strip(),
                        "user_text": prompt,
                        "suggested_actions": actions
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

            if target_planning:
                if target_planning.statut == RepasPlanifie.STATUT_COMMANDE:
                    res_data = {
                        "status": "cannot_delete_converted",
                        "intent": "DELETE_PLANNING",
                        "message": f"Le repas '{target_planning.produit.nom}' a déjà été transformé en commande validée et ne peut pas être supprimé.",
                        "user_text": prompt,
                        "suggested_actions": [
                            {"label": "Voir mon planning", "action": "VIEW_PLANNING"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

                ctx['pending_delete_id'] = target_planning.id
                ctx['awaiting_delete_confirmation'] = True
                conversation.context_data = ctx
                conversation.save()

                p_date = target_planning.date_planifiee
                day_fr = self.DAYS_FR[p_date.weekday()]
                mon_fr = self.MONTHS_FR[p_date.month]
                date_lbl_val = f"{day_fr} {p_date.day} {mon_fr}"
                time_lbl_val = str(target_planning.heure_planifiee)[:5] if target_planning.heure_planifiee else "12h30"

                msg_summary = f"Voulez-vous vraiment supprimer le repas planifié suivant ?\n\n• Plat : {target_planning.produit.nom}\n• Chez : {target_planning.etablissement.nom}\n• Date : {date_lbl_val.lower()} à {time_lbl_val}\n\nCette action retirera ce repas de votre planning."
                res_data = {
                    "status": "confirm_delete_proposal",
                    "intent": "DELETE_PLANNING",
                    "message": msg_summary,
                    "user_text": prompt,
                    "planning_id": target_planning.id,
                    "detected_product": {
                        "id": target_planning.produit.id,
                        "nom": target_planning.produit.nom,
                        "prix": float(target_planning.produit.prix_base),
                        "prix_formate": f"{float(target_planning.produit.prix_base):,.0f} FCFA".replace(",", " "),
                        "etablissement_nom": target_planning.etablissement.nom
                    },
                    "detected_establishment": {
                        "id": target_planning.etablissement.id,
                        "nom": target_planning.etablissement.nom
                    },
                    "detected_datetime": {
                        "date_iso": p_date.strftime('%Y-%m-%d'),
                        "date_label": date_lbl_val,
                        "time_label": time_lbl_val,
                        "creneau": target_planning.creneau
                    },
                    "suggested_actions": [
                        {"label": "Oui, supprimer", "action": "CONFIRM_DELETE_PLANNING", "planning_id": target_planning.id},
                        {"label": "Non", "action": "DECLINE_PLANNING"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=target_planning.produit)

        # -------------------------------------------------------------
        # 11. INTENT = AMBIGUOUS (Ex: "Je veux du burger demain", "Burger demain")
        # -------------------------------------------------------------
        explicit_plan_triggers = ['planifie', 'planifier', 'programme', 'met dans mon planning', 'ajoute au planning', 'finalement planifie']
        is_explicit_planning = any(w in prompt_lower for w in explicit_plan_triggers) or force_action == 'CREATE_PLANNING'

        matched_prod_early, searched_term_early = self._find_matching_product(prompt)
        prompt_unaccent = prompt_lower.replace('é','e').replace('è','e').replace('ê','e').replace('à','a').replace('â','a')
        is_ambiguous_trigger = matched_prod_early is not None or bool(searched_term_early) or any(w in prompt_unaccent for w in ['je veux', 'envie de', 'manger', 'burger', 'poulet', 'riz', 'thieb', 'pizza', 'tacos', 'aujourdhui', 'demain'])

        if not is_explicit_planning and ctx.get('last_intent') != 'CREATE_PLANNING' and not awaiting_confirmation and is_ambiguous_trigger:
            product = matched_prod_early
            searched_term = searched_term_early
            if not product and context_product:
                product = context_product
            term_name = searched_term or (product.nom if product else "ce plat")

            target_term_to_save = searched_term or (product.nom if product else '')
            if target_term_to_save:
                ctx['last_searched_term'] = target_term_to_save
            conversation.context_data = ctx

            amb_prods = search_food(query=target_term_to_save, limit=6)

            res_data = {
                "status": "ambiguous",
                "intent": "AMBIGUOUS",
                "type": "catalog_results",
                "entity": "product",
                "message": f"Voulez-vous que je vous propose des {term_name}s disponibles chez les restaurants AYYOU, ou souhaitez-vous planifier un repas ?",
                "user_text": prompt,
                "matching_products": amb_prods,
                "detected_product": {
                    "id": product.id,
                    "nom": product.nom,
                    "prix": float(product.prix_base),
                    "prix_formate": f"{float(product.prix_base):,.0f} FCFA".replace(",", " "),
                    "image_url": product.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_nom": product.etablissement.nom if product.etablissement else "AYYOU"
                } if product else None,
                "suggested_actions": [
                    {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"},
                    {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=product, matching_products=amb_prods)


        # -------------------------------------------------------------
        # 11.4. INTENT = UPDATE_PLANNING (Modification d'un repas planifié existant)
        # -------------------------------------------------------------
        update_keywords = ['modifie', 'modifier', 'change', 'changer', 'décale', 'décaler', 'déplace', 'déplacer', 'reporter', 'reporte', 'remplace', 'remplacer', 'update']
        is_update_intent = force_action == 'UPDATE_PLANNING' or (
            any(w in prompt_lower for w in update_keywords) and (
                'repas' in prompt_lower or 'planning' in prompt_lower or 'heure' in prompt_lower or 'date' in prompt_lower or 'restaurant' in prompt_lower or 'plat' in prompt_lower or 'demain' in prompt_lower or 'samedi' in prompt_lower or bool(ctx.get('editing_planning_id'))
            )
        ) or bool(ctx.get('editing_planning_id')) or bool(ctx.get('selectable_plannings'))

        if is_update_intent and not is_decline_word and not (awaiting_confirmation and is_confirm_word) and not awaiting_upd_confirm:
            from apps.orders.models import RepasPlanifie
            req_plan_id = request.data.get('planning_id') or ctx.get('editing_planning_id')
            target_planning = None

            if req_plan_id and user:
                try:
                    target_planning = RepasPlanifie.objects.select_related('produit', 'etablissement').get(id=req_plan_id, utilisateur=user)
                except RepasPlanifie.DoesNotExist:
                    target_planning = None

            selectable_plannings = ctx.get('selectable_plannings', [])
            if not target_planning and selectable_plannings and user:
                sel_idx = None
                if any(w in prompt_lower for w in ['premier', '1er', '1ere', 'première', '1']):
                    sel_idx = 0
                elif any(w in prompt_lower for w in ['deuxième', '2ème', '2eme', 'deuxieme', '2']):
                    sel_idx = 1
                elif any(w in prompt_lower for w in ['troisième', '3ème', '3eme', 'troisieme', '3']):
                    sel_idx = 2

                if sel_idx is not None and sel_idx < len(selectable_plannings):
                    chosen_p_id = selectable_plannings[sel_idx].get('id')
                    try:
                        target_planning = RepasPlanifie.objects.select_related('produit', 'etablissement').get(id=chosen_p_id, utilisateur=user)
                        ctx['selectable_plannings'] = None
                    except RepasPlanifie.DoesNotExist:
                        target_planning = None

            if not target_planning and user:
                user_plannings = RepasPlanifie.objects.filter(utilisateur=user).exclude(statut=RepasPlanifie.STATUT_ANNULE).select_related('produit', 'etablissement').order_by('date_planifiee', 'creneau')

                if parsed_target_date is not None:
                    user_plannings = user_plannings.filter(date_planifiee=parsed_target_date)

                matched_p, _ = self._find_matching_product(prompt)
                if matched_p:
                    user_plannings = user_plannings.filter(produit=matched_p)

                cnt = user_plannings.count()
                if cnt == 0:
                    res_data = {
                        "status": "no_planning_found",
                        "intent": "UPDATE_PLANNING",
                        "message": "Vous n'avez aucun repas planifié correspondant à cette demande.",
                        "user_text": prompt,
                        "suggested_actions": [
                            {"label": "Voir mon planning", "action": "VIEW_PLANNING"}
                        ]
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)
                elif cnt == 1:
                    target_planning = user_plannings.first()
                else:
                    plan_list = list(user_plannings)
                    ctx['selectable_plannings'] = [{"id": p.id, "produit_nom": p.produit.nom, "etablissement_nom": p.etablissement.nom} for p in plan_list]
                    conversation.context_data = ctx
                    conversation.save()

                    options_msg = "Lequel de vos repas planifiés souhaitez-vous modifier ?\n\n"
                    actions = []
                    for idx, p in enumerate(plan_list[:5], 1):
                        p_date_str = p.date_planifiee.strftime('%d/%m/%Y')
                        options_msg += f"{idx}. {p.produit.nom} chez {p.etablissement.nom} ({p_date_str})\n"
                        actions.append({"label": f"Repas {idx}", "action": "UPDATE_PLANNING", "planning_id": p.id})

                    res_data = {
                        "status": "disambiguate_planning",
                        "intent": "UPDATE_PLANNING",
                        "message": options_msg.strip(),
                        "user_text": prompt,
                        "suggested_actions": actions
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

            if target_planning:
                ctx['editing_planning_id'] = target_planning.id

                new_date = parsed_target_date or target_planning.date_planifiee
                new_time = parsed_time_label or target_planning.heure_planifiee
                new_creneau = parsed_creneau or target_planning.creneau

                new_prod = target_planning.produit
                new_est = target_planning.etablissement

                matched_p, _ = self._find_matching_product(prompt)
                if matched_p and matched_p.id != target_planning.produit_id:
                    new_prod = matched_p
                    if matched_p.etablissement:
                        new_est = matched_p.etablissement

                from apps.catalog.catalog_service import CatalogSearchService
                all_ests = search_establishments_paginated(limit=100).get("results", [])
                for est_item in all_ests:
                    if est_item['nom'].lower() in prompt_lower:
                        try:
                            found_est = Etablissement.objects.get(id=est_item['id'])
                            new_est = found_est
                            if new_prod and new_prod.etablissement_id and new_prod.etablissement_id != new_est.id:
                                new_prod = None
                        except Etablissement.DoesNotExist:
                            pass
                        break

                if not new_prod:
                    res_data = {
                        "status": "missing_info",
                        "intent": "UPDATE_PLANNING",
                        "message": f"Vous avez sélectionné {new_est.nom}. Quel plat souhaitez-vous choisir dans ce restaurant ?",
                        "user_text": prompt,
                        "detected_establishment": {"id": new_est.id, "nom": new_est.nom},
                        "suggested_actions": []
                    }
                    return self._save_message_and_respond(conversation, prompt, res_data)

                if isinstance(new_date, str):
                    date_iso_val = new_date
                    date_lbl_val = new_date
                else:
                    date_iso_val = new_date.strftime('%Y-%m-%d')
                    day_fr = self.DAYS_FR[new_date.weekday()]
                    mon_fr = self.MONTHS_FR[new_date.month]
                    date_lbl_val = f"{day_fr} {new_date.day} {mon_fr}"

                time_lbl_val = new_time or "12h30"

                pending_upd = {
                    "planning_id": target_planning.id,
                    "product_id": new_prod.id,
                    "product_nom": new_prod.nom,
                    "establishment_id": new_est.id,
                    "establishment_nom": new_est.nom,
                    "date_iso": date_iso_val,
                    "date_label": date_lbl_val,
                    "time_label": time_lbl_val,
                    "creneau": new_creneau
                }
                ctx['pending_update'] = pending_upd
                ctx['awaiting_update_confirmation'] = True
                conversation.context_data = ctx

                msg_summary = f"Voici la modification proposée pour votre repas (n°{target_planning.id}) :\n\n• Plat : {new_prod.nom}\n• Chez : {new_est.nom}\n• Date : {date_lbl_val.lower()} à {time_lbl_val}\n\nVoulez-vous enregistrer ces modifications ?"
                res_data = {
                    "status": "success",
                    "intent": "UPDATE_PLANNING",
                    "message": msg_summary,
                    "user_text": prompt,
                    "detected_product": {
                        "id": new_prod.id,
                        "nom": new_prod.nom,
                        "prix": float(new_prod.prix_base),
                        "prix_formate": f"{float(new_prod.prix_base):,.0f} FCFA".replace(",", " "),
                        "etablissement_nom": new_est.nom
                    },
                    "detected_establishment": {
                        "id": new_est.id,
                        "nom": new_est.nom
                    },
                    "detected_datetime": {
                        "date_iso": date_iso_val,
                        "date_label": date_lbl_val,
                        "time_label": time_lbl_val,
                        "creneau": new_creneau
                    },
                    "suggested_actions": [
                        {"label": "Confirmer les modifications", "action": "CONFIRM_UPDATE_PLANNING"},
                        {"label": "Annuler", "action": "DECLINE_PLANNING"}
                    ]
                }
                return self._save_message_and_respond(conversation, prompt, res_data, product=new_prod)

        # -------------------------------------------------------------
        # 11.5. TRAITEMENT DES SPÉCIFICATIONS DE DATES/HEURES OU DEMANDE EXPLICITE DE PLANIFICATION
        # -------------------------------------------------------------
        if (parsed_target_date is not None or parsed_time_label is not None) or is_explicit_planning:
            options_text = ""
            option_patterns = [r'(avec\s+[^,\.\n]+)', r'(sans\s+[^,\.\n]+)', r'(option[s]?\s+[^,\.\n]+)']
            for pat in option_patterns:
                match = re.search(pat, prompt_lower)
                if match:
                    options_text = match.group(1).capitalize().strip()
                    break

            product, searched_term = self._find_matching_product(prompt)
            if not product and req_product_id:
                try:
                    product = Produit.objects.select_related('etablissement').get(id=req_product_id)
                except Produit.DoesNotExist:
                    product = None
            if not product and context_product:
                product = context_product
            if not product and selected_product:
                if isinstance(selected_product, dict) and selected_product.get('id'):
                    try:
                        product = Produit.objects.select_related('etablissement').get(id=selected_product['id'])
                    except Produit.DoesNotExist:
                        product = None
                elif isinstance(selected_product, Produit):
                    product = selected_product
            if not product and pending_selection and pending_selection.get('product_id'):
                try:
                    product = Produit.objects.select_related('etablissement').get(id=pending_selection['product_id'])
                except Produit.DoesNotExist:
                    product = None
            if not product and last_products:
                p_info = last_products[0]
                p_id = p_info.get('id') if isinstance(p_info, dict) else getattr(p_info, 'id', None)
                if p_id:
                    try:
                        product = Produit.objects.select_related('etablissement').get(id=p_id)
                    except Produit.DoesNotExist:
                        product = None
            if not product and last_results and last_results.get('items'):
                items = last_results['items']
                if items and isinstance(items[0], dict) and items[0].get('id'):
                    try:
                        product = Produit.objects.select_related('etablissement').get(id=items[0]['id'])
                    except Produit.DoesNotExist:
                        product = None

            if not product:
                term_display = searched_term or "ce plat"
                res_data = {
                    "status": "missing_info",
                    "intent": "CREATE_PLANNING",
                    "message": f"Je n'ai trouvé aucun '{term_display}' disponible dans le catalogue AYYOU. Vous pouvez choisir un autre plat parmi nos restaurants ou modifier votre recherche.",
                    "user_text": prompt,
                    "detected_product": None,
                    "detected_establishment": None,
                    "detected_datetime": None,
                    "detected_options": options_text
                }
                return self._save_message_and_respond(conversation, prompt, res_data)

            establishment = product.etablissement
            date_iso = last_dt.get('date_iso')
            date_lbl = last_dt.get('date_label')
            time_lbl = last_dt.get('time_label')
            creneau_val = last_dt.get('creneau')

            if not date_iso or not time_lbl:
                return self._get_missing_info_response(
                    conversation, prompt, product=product,
                    date_iso=date_iso, date_label=date_lbl, time_label=time_lbl
                )

            prix = float(product.prix_base)
            prix_formate = f"{prix:,.0f} FCFA".replace(",", " ")
            image_url = product.image_url or "assets/images/thieboudienne.jpg"

            pending_selection = {
                "product_id": product.id,
                "product_nom": product.nom,
                "establishment_id": establishment.id if establishment else None,
                "establishment_nom": establishment.nom if establishment else "AYYOU",
                "establishment_adresse": establishment.adresse if establishment else "Dakar",
                "prix": prix,
                "prix_formate": prix_formate,
                "image_url": image_url,
                "date_iso": date_iso,
                "date_label": date_lbl,
                "time_label": time_lbl,
                "creneau": creneau_val
            }
            ctx['pending_selection'] = pending_selection
            ctx['awaiting_confirmation'] = True
            ctx['selected_product'] = {
                "id": product.id,
                "nom": product.nom,
                "prix": prix,
                "etablissement_nom": establishment.nom if establishment else "AYYOU"
            }
            conversation.context_data = ctx

            msg_proposal = f"D'accord ! Je vous propose de planifier le repas :\n\n• Plat : {product.nom}\n• Chez : {establishment.nom if establishment else 'AYYOU'}\n• Date : {date_lbl.lower()} à {time_lbl}\n\nVoulez-vous confirmer ?"

            res_data = {
                "status": "success",
                "intent": "CREATE_PLANNING",
                "message": msg_proposal,
                "user_text": prompt,
                "detected_product": {
                    "id": product.id,
                    "nom": product.nom,
                    "prix": prix,
                    "prix_formate": prix_formate,
                    "image_url": image_url,
                    "etablissement_id": establishment.id if establishment else None,
                    "etablissement_nom": establishment.nom if establishment else "AYYOU"
                },
                "detected_establishment": {
                    "id": establishment.id if establishment else None,
                    "nom": establishment.nom if establishment else "AYYOU",
                    "adresse": establishment.adresse if establishment else "Dakar"
                },
                "detected_datetime": {
                    "date_iso": date_iso,
                    "date_label": date_lbl,
                    "time_label": time_lbl,
                    "creneau": creneau_val
                },
                "detected_options": options_text or "Piment à part",
                "suggested_actions": [
                    {"label": "Oui, planifier", "action": "CONFIRM_PLANNING"},
                    {"label": "Non", "action": "DECLINE_PLANNING"}
                ]
            }
            return self._save_message_and_respond(conversation, prompt, res_data, product=product)

        # -------------------------------------------------------------
        # 13. FALLBACK CONVERSATIONNEL (Demande non reconnue -> Ne JAMAIS forcer de planning !)
        # -------------------------------------------------------------
        res_data = {
            "status": "unclear_query",
            "intent": "GENERAL_CONVERSATION",
            "message": "Je n'ai pas bien compris votre demande. Souhaitez-vous rechercher des plats, découvrir des restaurants à Dakar ou planifier un repas ?",
            "user_text": prompt,
            "suggested_actions": [
                {"label": "Découvrir les restaurants", "action": "RESTAURANT_SEARCH"},
                {"label": "Rechercher des plats", "action": "FOOD_SEARCH"}
            ]
        }
        return self._save_message_and_respond(conversation, prompt, res_data)

    def _save_message_and_respond(self, conversation, prompt, res_data, product=None, matching_products=None, matching_establishments=None):
        ctx = dict(conversation.context_data or {})
        if product:
            p_id = product.id if hasattr(product, 'id') else product.get('id')
            if p_id:
                ctx['last_selected_product_id'] = p_id
            if isinstance(product, dict):
                ctx['selected_product'] = product
            elif hasattr(product, 'id'):
                ctx['selected_product'] = {
                    "id": product.id,
                    "nom": product.nom,
                    "prix": float(product.prix_base),
                    "prix_formate": f"{float(product.prix_base):,.0f} FCFA".replace(",", " "),
                    "image_url": product.image_url or "assets/images/thieboudienne.jpg",
                    "etablissement_id": product.etablissement.id if product.etablissement else None,
                    "etablissement_nom": product.etablissement.nom if product.etablissement else "AYYOU"
                }

        m_prods = matching_products or res_data.get('matching_products')
        m_ests = matching_establishments or res_data.get('matching_establishments')

        if m_prods:
            ctx['last_products'] = m_prods
            ctx['last_results'] = {"type": "product_search" if res_data.get('status') != 'restaurant_dishes' else "restaurant_dishes", "items": m_prods}
            if not ctx.get('selected_product') and isinstance(m_prods, list) and len(m_prods) > 0:
                first_p = m_prods[0]
                if isinstance(first_p, dict) and first_p.get('id'):
                    ctx['last_selected_product_id'] = first_p['id']
                    ctx['selected_product'] = first_p
                elif hasattr(first_p, 'id'):
                    ctx['last_selected_product_id'] = first_p.id
        elif m_ests:
            ctx['last_matching_establishments'] = m_ests
            ctx['last_results'] = {"type": "restaurant_search", "items": m_ests}

        if res_data.get('intent'):
            ctx['last_intent'] = res_data['intent']

        conversation.context_data = ctx
        conversation.save()

        res_data['conversation_id'] = conversation.id
        AIMessage.objects.create(conversation=conversation, role=AIMessage.ROLE_USER, content=prompt)
        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.ROLE_ASSISTANT,
            content=res_data.get('message', ''),
            user_text=prompt,
            data_payload=res_data
        )
        return Response(res_data, status=status.HTTP_200_OK)

    def _find_matching_product(self, prompt: str):
        prompt_lower = prompt.lower().strip()
        clean_prompt = re.sub(r'[^\w\s]', ' ', prompt_lower)

        products = list(Produit.objects.select_related('etablissement', 'categorie').filter(
            est_disponible=True
        ))
        if not products:
            return None, ""

        stop_words = {
            'manger', 'veux', 'bon', 'bonne', 'mardi', 'chez', 'dakar', 'avec', 'part',
            'pour', 'demain', 'hier', 'soir', 'midi', 'matin', 'non', 'j', 'ai',
            'dit', 'un', 'une', 'des', 'le', 'la', 'les', 'du', 'de', 'ce', 'cet',
            'cette', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
            'planifier', 'planifie', 'planifié', 'planifiera', 'commande', 'commander',
            'souhaite', 'souhaiterais', 'voudrais', 'aimerais', 'repas', 'plat', 'plats',
            'voir', 'regarder', 'chercher', 'rechercher', 'trouver', 'montre', 'montrer',
            'afficher', 'propose', 'proposer', 'proposent', 'donne', 'donner', 'liste', 'lister',
            'restaurant', 'restaurants', 'aujourd', 'hui', 'aujourdhui', 'moi', 'qui', 'quel', 'quels',
            'quelle', 'quelles', 'avez', 'faites', 'faire', 'servir', 'servez', 'dans', 'en', 'sur',
            'au', 'aux', 'par', 'budget', 'fcfa', 'f', 'cfa', 'francs', 'franc', 'tarif', 'prix',
            'est', 'sont', 'fait', 'combien', 'ou', 'où', 'avoir', 'maximum', 'max', 'maxi',
            'moins', 'plus', 'jusqu', 'jusqua', 'jusqu\'à', 'puis', 'peux', 'peux-tu', 'puis-je',
            'qu', 'est', 'ce', 'que', 'disponible', 'disponibles', 'comme', 'vers', 'autour', 'coût',
            'coûte', 'cout', 'coute', 'jusqu\'a'
        }

        raw_tokens = [t for t in re.split(r'\s+', clean_prompt) if t and t not in stop_words and len(t) > 1 and not t.isdigit()]

        search_terms = set(raw_tokens)
        for token in raw_tokens:
            if token in FOOD_SYNONYMS:
                search_terms.update(FOOD_SYNONYMS[token])

        best_product = None
        best_score = 0
        extracted_term = ""

        # Prioritize tokens that match a food synonym directly
        for token in raw_tokens:
            if token in FOOD_SYNONYMS:
                extracted_term = token
                break

        for p in products:
            p_nom_clean = p.nom.lower()
            p_nom_unaccent = p_nom_clean.replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('â', 'a')
            p_cat_clean = (p.categorie.nom.lower() if p.categorie else "").replace('é', 'e').replace('è', 'e')
            p_desc_clean = (p.description or "").lower().replace('é', 'e').replace('è', 'e')

            score = 0
            for term in search_terms:
                term_clean = term.replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('à', 'a').replace('â', 'a')
                if term in p_nom_clean or term_clean in p_nom_unaccent:
                    score += 100
                elif term in p_cat_clean or term_clean in p_cat_clean:
                    score += 60
                elif term in p_desc_clean or term_clean in p_desc_clean:
                    score += 30

            p_words = [w for w in re.split(r'\s+', p_nom_unaccent) if len(w) > 3 and w in search_terms]
            for w in p_words:
                score += 40

            if score > best_score:
                best_score = score
                best_product = p

        if best_score > 0 and best_product:
            if not extracted_term:
                extracted_term = best_product.nom
            return best_product, extracted_term

        if not extracted_term and raw_tokens:
            for t in raw_tokens:
                if t in FOOD_SYNONYMS:
                    extracted_term = t
                    break
            if not extracted_term and best_score > 0:
                extracted_term = raw_tokens[0]

        if extracted_term in FOOD_SYNONYMS or (best_score > 0 and extracted_term):
            return None, extracted_term

        return None, ""

    def _get_missing_info_response(self, conversation, prompt, product=None, date_iso=None, date_label=None, time_label=None):
        missing_date = not date_iso
        missing_time = not time_label

        if missing_date and missing_time:
            msg = "Bien sûr. Pour quelle date et à quelle heure souhaitez-vous planifier ce repas ?"
        elif missing_date:
            msg = "Pour quelle date souhaitez-vous planifier ce repas ?"
        else:
            msg = "À quelle heure souhaitez-vous planifier ce repas ?"

        p_data = {
            "id": product.id,
            "nom": product.nom,
            "prix": float(product.prix_base),
            "prix_formate": f"{float(product.prix_base):,.0f} FCFA".replace(",", " "),
            "image_url": product.image_url or "assets/images/thieboudienne.jpg",
            "etablissement_id": product.etablissement.id if (product and product.etablissement) else None,
            "etablissement_nom": product.etablissement.nom if (product and product.etablissement) else "AYYOU"
        } if product else None

        e_data = {
            "id": product.etablissement.id if (product and product.etablissement) else None,
            "nom": product.etablissement.nom if (product and product.etablissement) else "AYYOU",
            "adresse": product.etablissement.adresse if (product and product.etablissement) else "Dakar"
        } if product else None

        res_data = {
            "status": "missing_info",
            "intent": "CREATE_PLANNING",
            "message": msg,
            "user_text": prompt,
            "detected_product": p_data,
            "detected_establishment": e_data,
            "detected_datetime": None,
            "suggested_actions": []
        }
        return self._save_message_and_respond(conversation, prompt, res_data, product=product)

    def _parse_date(self, prompt_lower: str):
        today = timezone.now().date()
        target_date = None
        has_date_keyword = False

        if 'demain' in prompt_lower:
            has_date_keyword = True
            target_date = today + datetime.timedelta(days=1)
        elif 'apres-demain' in prompt_lower or 'après demain' in prompt_lower:
            has_date_keyword = True
            target_date = today + datetime.timedelta(days=2)
        elif 'aujourd\'hui' in prompt_lower or 'aujourdhui' in prompt_lower:
            has_date_keyword = True
            target_date = today
        else:
            for day_name, day_idx in self.DAYS_MAP.items():
                if day_name in prompt_lower:
                    has_date_keyword = True
                    current_idx = today.weekday()
                    days_ahead = (day_idx - current_idx) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    target_date = today + datetime.timedelta(days=days_ahead)
                    break

        if not has_date_keyword:
            num_month_pattern = r'\b(\d{1,2})\s*(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|janv|févr|fevr|avr|juil|sept|oct|nov|déc|dec)\b'
            match_nm = re.search(num_month_pattern, prompt_lower)
            if match_nm:
                has_date_keyword = True
                day_val = int(match_nm.group(1))
                try:
                    target_date = datetime.date(today.year, today.month, day_val)
                    if target_date < today:
                        target_date = datetime.date(today.year + 1, today.month, day_val)
                except ValueError:
                    target_date = today
            else:
                num_slash_pattern = r'\b(\d{1,2})[/.-](\d{1,2})\b'
                match_ns = re.search(num_slash_pattern, prompt_lower)
                if match_ns:
                    has_date_keyword = True
                    day_val = int(match_ns.group(1))
                    mon_val = int(match_ns.group(2))
                    try:
                        target_date = datetime.date(today.year, mon_val, day_val)
                        if target_date < today:
                            target_date = datetime.date(today.year + 1, mon_val, day_val)
                    except ValueError:
                        target_date = today

        if not has_date_keyword or target_date is None:
            return None, None

        day_name_fr = self.DAYS_FR[target_date.weekday()]
        month_name_fr = self.MONTHS_FR[target_date.month]
        date_label = f"{day_name_fr} {target_date.day} {month_name_fr}"

        return target_date, date_label

    def _parse_time(self, prompt_lower: str):
        has_time_keyword = False
        time_str = None
        creneau = None

        time_match = re.search(r'\b(\d{1,2})\s*[hH:]\s*(\d{2})?\b', prompt_lower)
        if not time_match:
            time_match = re.search(r'\b(\d{1,2})\s*heures?\b', prompt_lower)
        if not time_match:
            time_match = re.search(r'\bà\s*(\d{1,2})\b', prompt_lower)

        if time_match:
            has_time_keyword = True
            hours = int(time_match.group(1))
            mins = time_match.group(2) if (time_match.lastindex and time_match.lastindex >= 2 and time_match.group(2)) else "00"
            time_str = f"{hours:02d}h{mins}" if hours < 24 else "12h30"
            if hours < 11:
                creneau = "MATIN"
            elif 11 <= hours < 16:
                creneau = "MIDI"
            elif 16 <= hours < 18:
                creneau = "EN_CAS"
            else:
                creneau = "SOIR"
        elif 'soir' in prompt_lower:
            has_time_keyword = True
            time_str = "20h00"
            creneau = "SOIR"
        elif 'midi' in prompt_lower:
            has_time_keyword = True
            time_str = "12h30"
            creneau = "MIDI"
        elif 'matin' in prompt_lower:
            has_time_keyword = True
            time_str = "08h30"
            creneau = "MATIN"

        if not has_time_keyword:
            return None, None

        time_label = f"{time_str}"
        return time_label, creneau


class AIConversationListView(APIView):
    """
    GET /api/ai/conversations/ -> Liste les conversations du client.
    POST /api/ai/conversations/new/ -> Démarre une nouvelle conversation.
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user if (hasattr(request, 'user') and request.user and request.user.is_authenticated) else None
        if user:
            qs = AIConversation.objects.filter(utilisateur=user).prefetch_related('messages')[:30]
        else:
            session_key = request.session.session_key if hasattr(request, 'session') else None
            if not session_key:
                return Response([], status=status.HTTP_200_OK)
            qs = AIConversation.objects.filter(session_key=session_key).prefetch_related('messages')[:30]
        
        serializer = AIConversationSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user if (hasattr(request, 'user') and request.user and request.user.is_authenticated) else None
        session_key = request.session.session_key if hasattr(request, 'session') else None
        titre = request.data.get('titre', 'Nouvelle conversation')
        
        conv = AIConversation.objects.create(
            utilisateur=user,
            session_key=session_key,
            titre=titre,
            context_data={}
        )
        serializer = AIConversationSerializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AIConversationDetailView(APIView):
    """
    GET /api/ai/conversations/<id>/ -> Messages de la conversation.
    DELETE /api/ai/conversations/<id>/ -> Supprime la conversation.
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        user = request.user if (hasattr(request, 'user') and request.user and request.user.is_authenticated) else None
        session_key = request.session.session_key if hasattr(request, 'session') else None

        try:
            conv = AIConversation.objects.prefetch_related('messages').get(id=pk)
        except (AIConversation.DoesNotExist, ValueError):
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if user and conv.utilisateur != user:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)
        elif not user and conv.session_key and conv.session_key != session_key:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AIConversationSerializer(conv)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        user = request.user if (hasattr(request, 'user') and request.user and request.user.is_authenticated) else None
        session_key = request.session.session_key if hasattr(request, 'session') else None

        try:
            conv = AIConversation.objects.get(id=pk)
        except (AIConversation.DoesNotExist, ValueError):
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if user and conv.utilisateur != user:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)
        elif not user and conv.session_key and conv.session_key != session_key:
            return Response({"detail": "Conversation introuvable."}, status=status.HTTP_404_NOT_FOUND)

        conv.delete()
        return Response({"detail": "Conversation supprimée."}, status=status.HTTP_200_OK)

