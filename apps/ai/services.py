import urllib.request
import json
import re
from decimal import Decimal
import datetime
from django.utils import timezone
from .models import AIChatQuota
from .prompts import SYSTEM_PROMPT
from .tools import (
    search_food,
    search_establishments,
    search_by_budget,
    search_by_category,
    get_product,
    get_establishment,
    get_user_orders,
    get_delivery_status,
    search_by_location,
    get_user_plannings,
    get_planning_by_id,
    update_user_planning,
    cancel_user_planning,
    update_order_delivery_info
)


class AIService:
    """
    Service d'IA Conseiller Gastronomique & Suivi AYYOU Dakar.
    Comprenant :
    1. Détection des intentions (Catalogue, Commandes, Livraisons, Localisation GPS)
    2. Protection anti-prompt-injection
    3. Exécution d'outils ORM 100% réels sur PostgreSQL avec isolation utilisateur
    4. Validation stricte des données et limitation des recherches intelligentes (7 max / 5h)
    """
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    DEFAULT_MODEL = "llama3.2:latest"

    # Liste des quartiers / zones reconnues à Dakar
    DAKAR_LOCATIONS = [
        'plateau', 'parcelles', 'almadies', 'mermoz', 'yoff', 'ngor',
        'ouakam', 'fann', 'point e', 'medina', 'médina', 'grand yoff',
        'pikine', 'guédiawaye', 'guediawaye', 'rufisque', 'sacré cœur',
        'sacre coeur', 'liberté', 'dakar', 'dakar-plateau'
    ]

    # Mots-clés de nourriture
    FOOD_KEYWORDS = [
        'thiéboudienne', 'thieboudienne', 'thieb', 'tieb', 'yassa', 'mafé', 'mafe',
        'pastels', 'dibi', 'poulet', 'poisson', 'riz', 'burger', 'tacos', 'pizza',
        'chawarma', 'grillade', 'dessert', 'jus', 'bissap', 'bouye', 'thiébou yapp'
    ]

    GREETING_PHRASES = [
        'bonjour', 'bonsoir', 'salut', 'coucou', 'hello', 'hi', 'hey', 'merci',
        'super', 'ok', 'd\'accord', 'daccord', 'cool', 'qui es-tu', 'qui es tu',
        'aide-moi', 'aide moi', 'au revoir', 'bye', 'a bientot', 'à bientôt'
    ]

    @classmethod
    def check_prompt_injection(cls, text: str) -> bool:
        """
        Détecte les tentatives de prompt injection et d'accès aux données système.
        """
        t_lower = text.lower()
        injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'forget\s+all\s+rules',
            r'system\s+prompt',
            r'show\s+database',
            r'select\s+\*\s+from',
            r'admin\s+password',
            r'mots?\s+de\s+passe',
            r'utilisateurs?\s+ayyou',
            r'export\s+db',
            r'dump\s+database',
            r'drop\s+table'
        ]
        for pattern in injection_patterns:
            if re.search(pattern, t_lower):
                return True
        return False

    @classmethod
    def is_smart_dish_search(cls, message: str, intent: dict) -> bool:
        """
        Détermine si le message de l'utilisateur correspond réellement à une Recherche Intelligente de Plats.
        Les salutations simples, remerciements et suivis de commande/livraison retournent False.
        """
        m_lower = message.lower().strip()

        # Ne concerne ni les commandes ni les livraisons
        if intent.get("is_order_intent") or intent.get("is_delivery_intent"):
            return False

        # Salutations ou messages très courts conversationnels
        if m_lower in cls.GREETING_PHRASES:
            return False

        # Présence d'un critère explicite de recherche
        if intent.get("budget_max") or intent.get("category_slug") or intent.get("location") or intent.get("type_etablissement"):
            return True

        if intent.get("food_query") and intent.get("food_query").lower() not in cls.GREETING_PHRASES:
            return True

        food_triggers = [
            'cherche', 'trouve', 'recommande', 'plat', 'plats', 'manger', 'repas', 'dîner', 'diner',
            'déjeuner', 'dejeuner', 'faim', 'nourriture', 'resto', 'restaurant', 'menu', 'carte'
        ]
        if any(trig in m_lower for trig in food_triggers):
            return True

        if any(f in m_lower for f in cls.FOOD_KEYWORDS):
            return True

        return False

    DAYS_MAP = {
        'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
        'vendredi': 4, 'samedi': 5, 'dimanche': 6
    }
    DAYS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    MONTHS_FR = ['', 'Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin', 'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.']

    @classmethod
    def _parse_target_date(cls, text: str):
        t_lower = text.lower()
        today = timezone.now().date()
        target_date = None

        if 'demain' in t_lower:
            target_date = today + datetime.timedelta(days=1)
        elif 'apres-demain' in t_lower or 'après demain' in t_lower:
            target_date = today + datetime.timedelta(days=2)
        else:
            for day_name, day_idx in cls.DAYS_MAP.items():
                if day_name in t_lower:
                    current_idx = today.weekday()
                    days_ahead = (day_idx - current_idx) % 7
                    if days_ahead == 0 and ('prochain' in t_lower or 'semaine' in t_lower):
                        days_ahead = 7
                    target_date = today + datetime.timedelta(days=days_ahead)
                    break

        if not target_date:
            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', t_lower)
            if date_match:
                try:
                    target_date = datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                except ValueError:
                    pass

        if target_date:
            day_name_fr = cls.DAYS_FR[target_date.weekday()]
            month_name_fr = cls.MONTHS_FR[target_date.month]
            label = f"{day_name_fr} {target_date.day} {month_name_fr}"
            return target_date, label

        return None, None

    @classmethod
    def _parse_target_creneau(cls, text: str):
        t_lower = text.lower()
        if 'soir' in t_lower or 'dîner' in t_lower or 'diner' in t_lower:
            return 'SOIR', 'Dîner'
        elif 'midi' in t_lower or 'déjeuner' in t_lower or 'dejeuner' in t_lower:
            return 'MIDI', 'Déjeuner'
        elif 'matin' in t_lower or 'petit-déjeuner' in t_lower or 'petit dejeuner' in t_lower:
            return 'MATIN', 'Petit-déjeuner'
        elif 'collation' in t_lower or 'goûter' in t_lower or 'gouter' in t_lower:
            return 'EN_CAS', 'En-cas'
        return None, None

    @classmethod
    def extract_intent(cls, message: str, history: list = None, context: dict = None) -> dict:
        """
        Extrait une intention structurée à partir du message courant, du contexte et de l'historique conversationnel.
        """
        intent = {
            "is_order_intent": False,
            "is_delivery_intent": False,
            "is_planning_query": False,
            "is_action_intent": False,
            "is_catalog_update": False,
            "action_type": None,
            "food_query": None,
            "budget_max": None,
            "location": None,
            "latitude": None,
            "longitude": None,
            "type_etablissement": None,
            "category_slug": None,
            "people_count": None
        }

        # 1. Analyser d'abord l'historique récent pour conserver le contexte
        combined_text = ""
        if history and isinstance(history, list):
            for h in history[-4:]:
                if isinstance(h, dict) and h.get('sender') == 'user':
                    combined_text += " " + str(h.get('text', ''))
        combined_text += " " + message
        c_lower = combined_text.lower()
        m_lower = message.lower().strip()

        # GPS Coords dans le contexte
        if context and isinstance(context, dict):
            if 'latitude' in context and 'longitude' in context:
                try:
                    intent["latitude"] = float(context['latitude'])
                    intent["longitude"] = float(context['longitude'])
                except (ValueError, TypeError):
                    pass

        # Détection d'intentions de LECTURE planning
        if any(w in m_lower for w in ['prochains repas', 'mon planning', 'mes plannings', 'qu\'ai-je planifié', 'quai je planifie', 'repas planifié', 'repas planifies']):
            if not any(w in m_lower for w in ['décale', 'decale', 'déplace', 'deplace', 'modifie', 'change', 'annule', 'supprime']):
                intent["is_planning_query"] = True

        # Détection d'intentions d'ACTION Planning
        if any(w in m_lower for w in ['décale', 'decale', 'déplace', 'deplace', 'modifie mon planning', 'modifie mon repas', 'change la date', 'change l\'heure', 'change le créneau', 'passe mon repas', 'change la quantité', 'change le nombre', 'annule mon repas', 'supprime mon repas', 'annule mon planning']):
            intent["is_action_intent"] = True
            if any(w in m_lower for w in ['annule', 'supprime']):
                intent["action_type"] = "cancel_planning"
            else:
                intent["action_type"] = "update_planning"

        # Détection d'intentions d'ACTION Livraison / Commande
        if any(w in m_lower for w in ['change la date de livraison', 'modifie la date de livraison', 'change mon adresse de livraison', 'modifie l\'adresse de livraison', 'change l\'adresse de ma commande']):
            intent["is_action_intent"] = True
            intent["action_type"] = "update_order_delivery"

        # Détection d'intentions d'ACTION Catalogue
        if any(w in m_lower for w in ['modifie le prix', 'change le prix', 'change le tarif', 'change la disponibilité', 'désactive le plat', 'supprime le plat du menu']):
            intent["is_action_intent"] = True
            intent["is_catalog_update"] = True
            intent["action_type"] = "update_catalog"

        # 2. Détection d'intentions spécifiques (Commandes & Livraisons en LECTURE)
        if not intent["is_action_intent"]:
            if any(w in m_lower for w in ['commande', 'commandes', 'dernier repas', 'dernière commande', 'dernière fois', 'recommander']):
                intent["is_order_intent"] = True

            if any(w in m_lower for w in ['livraison', 'livreur', 'où est ma commande', 'ou est ma commande', 'statut de ma commande', 'en route', 'quand vais-je recevoir']):
                intent["is_delivery_intent"] = True

        # 3. Budget max
        budget_match = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)?', m_lower)
        if budget_match and any(kw in m_lower for kw in ['budget', 'moins de', 'max', 'autour de', 'fcfa', 'francs', 'cfa', 'pour']):
            try:
                intent["budget_max"] = float(budget_match.group(1))
            except ValueError:
                pass

        if not intent["budget_max"]:
            h_budget_match = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)?', c_lower)
            if h_budget_match and any(kw in c_lower for kw in ['budget', 'moins de', 'max', 'fcfa', 'francs']):
                try:
                    intent["budget_max"] = float(h_budget_match.group(1))
                except ValueError:
                    pass

        # 4. Localisation / Quartier
        for loc in cls.DAKAR_LOCATIONS:
            if loc in m_lower:
                intent["location"] = loc
                break
        if not intent["location"]:
            for loc in cls.DAKAR_LOCATIONS:
                if loc in c_lower:
                    intent["location"] = loc
                    break

        # 5. Catégorie
        if any(w in c_lower for w in ['sénégal', 'senegal', 'sénégalaise', 'senegalaise', 'sénégalais', 'senegalais', 'thieb', 'yassa', 'mafé']):
            intent["category_slug"] = 'senegalais'
        elif any(w in c_lower for w in ['burger', 'tacos', 'pizza', 'fast food']):
            intent["category_slug"] = 'fast-food'

        # 6. Type d'établissement
        if any(w in c_lower for w in ['vendeur', 'domicile', 'fait maison', 'traiteur']):
            intent["type_etablissement"] = 'VENDEUR'
        elif any(w in c_lower for w in ['restaurant', 'resto', 'fast food', 'bistro']):
            intent["type_etablissement"] = 'RESTAURANT'

        # 7. Plat / Mot clé culinaire
        for food in cls.FOOD_KEYWORDS:
            if food in m_lower:
                intent["food_query"] = food
                break
        if not intent["food_query"]:
            for food in cls.FOOD_KEYWORDS:
                if food in c_lower:
                    intent["food_query"] = food
                    break

        if not intent["is_order_intent"] and not intent["is_delivery_intent"] and not intent["is_action_intent"] and not intent["is_planning_query"]:
            if not intent["food_query"] and not intent["category_slug"] and not intent["budget_max"] and not intent["location"]:
                if m_lower not in cls.GREETING_PHRASES and len(m_lower) > 2:
                    intent["food_query"] = m_lower[:30]

        return intent

    @classmethod
    def process_chat_message(cls, message: str, user_name: str = "Client", context: dict = None, history: list = None, user=None, request=None) -> dict:
        msg_str = message.strip()
        m_lower = msg_str.lower()
        user_id = user.id if (user and hasattr(user, 'is_authenticated') and user.is_authenticated) else None
        context = context or {}

        # 1. Obtenir le statut du quota pour l'utilisateur/session
        quota = AIChatQuota.get_or_create_quota(request)

        # 2. Vérification Anti-Prompt-Injection
        if cls.check_prompt_injection(msg_str):
            return {
                "status": "success",
                "reply": f"Bonjour {user_name} ! Je suis votre Conseiller Gastronomique AYYOU 🇸🇳. Je suis uniquement là pour vous guider vers les meilleurs plats et vous accompagner sur la plateforme AYYOU !",
                "cards": [],
                "user_name": user_name,
                "quota_used": quota.search_count,
                "quota_max": AIChatQuota.MAX_QUOTA,
                "is_quota_exceeded": quota.is_exceeded()
            }

        # 3. VERIFICATION DE LA CONFIRMATION D'UNE ACTION EN ATTENTE
        confirm_action = request.data.get('confirm_action') if request else context.get('confirm_action', False)
        pending_action = context.get('pending_action') or (request.data.get('pending_action') if request else None)

        is_confirmation_text = any(kw == m_lower or kw in m_lower for kw in ['oui', 'confirme', 'oui, confirme', 'oui confirme', 'd\'accord', 'valide', 'ok', 'confirmer', 'valider'])

        if (confirm_action or (is_confirmation_text and pending_action)) and pending_action:
            action_type = pending_action.get('action_type')
            if action_type == 'update_planning':
                planning_id = pending_action.get('planning_id')
                changes = pending_action.get('changes', {})
                exec_res = update_user_planning(planning_id=planning_id, user_id=user_id, changes_dict=changes)
                if exec_res.get('success'):
                    return {
                        "status": "action_executed",
                        "success": True,
                        "reply": f"Super {user_name} ! {exec_res.get('message')}\nVotre repas planifié a été physiquement mis à jour dans PostgreSQL.",
                        "planning": exec_res.get('planning'),
                        "cards": [],
                        "user_name": user_name
                    }
                else:
                    return {
                        "status": "error",
                        "success": False,
                        "reply": f"Désolé {user_name}, {exec_res.get('message')}",
                        "cards": [],
                        "user_name": user_name
                    }
            elif action_type == 'cancel_planning':
                planning_id = pending_action.get('planning_id')
                exec_res = cancel_user_planning(planning_id=planning_id, user_id=user_id)
                return {
                    "status": "action_executed" if exec_res.get('success') else "error",
                    "success": exec_res.get('success', False),
                    "reply": exec_res.get('message'),
                    "cards": [],
                    "user_name": user_name
                }
            elif action_type == 'update_order_delivery':
                order_id = pending_action.get('order_id')
                exec_res = update_order_delivery_info(order_id_or_number=order_id, user_id=user_id, new_instructions=pending_action.get('instructions'))
                return {
                    "status": "action_executed" if exec_res.get('success') else "error",
                    "success": exec_res.get('success', False),
                    "reply": exec_res.get('message'),
                    "cards": [],
                    "user_name": user_name
                }

        # 4. Extraction d'intention & contexte conversationnel
        intent = cls.extract_intent(msg_str, history, context)
        is_dish_search = cls.is_smart_dish_search(msg_str, intent)

        # 5. TRAITEMENT DES PERMISSIONS CATALOGUE
        if intent["is_catalog_update"]:
            user_role = getattr(user, 'role', 'CLIENT') if user else 'CLIENT'
            is_vendor = (user_role in ['VENDEUR', 'RESTAURANT', 'PRO']) or (user and getattr(user, 'is_staff', False))
            if not is_vendor:
                return {
                    "status": "permission_denied",
                    "reply": f"Refusé : En tant que client AYYOU ({user_name}), vous ne pouvez pas modifier le catalogue d'un établissement. Cette action est réservée au restaurateur ou au vendeur de l'établissement.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }

        # 6. TRAITEMENT DES ACTIONS SUR LE PLANNING
        if intent["is_action_intent"] and intent["action_type"] in ["update_planning", "cancel_planning"]:
            if not user_id:
                return {
                    "status": "success",
                    "reply": "Veuillez vous connecter à votre compte AYYOU pour gérer vos repas planifiés.",
                    "cards": [],
                    "user_name": user_name
                }

            # Récupérer les plannings réels du client dans PostgreSQL
            plannings_res = get_user_plannings(user_id=user_id)
            if not plannings_res.get('success') or plannings_res.get('count', 0) == 0:
                return {
                    "status": "missing_info",
                    "reply": f"Je n'ai trouvé aucun repas planifié actif dans votre compte AYYOU. N'hésitez pas à en créer un nouveau !",
                    "cards": [],
                    "user_name": user_name
                }

            user_plannings = plannings_res['results']

            # Recherche du planning cible à modifier
            target_planning = None
            matched_plannings = []

            # Recherche par jour / date mentionné dans le message
            source_date, source_label = cls._parse_target_date(m_lower)
            source_creneau, source_creneau_label = None, None

            # Extraire la première partie du message (avant "à", "au", "vers") pour la date/créneau source
            source_part = m_lower
            if ' à ' in m_lower:
                source_part = m_lower.split(' à ')[0]
            elif ' au ' in m_lower:
                source_part = m_lower.split(' au ')[0]

            source_creneau, source_creneau_label = cls._parse_target_creneau(source_part)

            # Filtrer par date source si identifiée
            if source_date:
                matched_plannings = [p for p in user_plannings if p['date_planifiee'] == source_date.strftime('%Y-%m-%d')]

            # Si plusieurs plannings sur la même date, affiner avec le créneau source
            if len(matched_plannings) > 1 and source_creneau:
                sub_match = [p for p in matched_plannings if p['creneau'] == source_creneau]
                if sub_match:
                    matched_plannings = sub_match

            # Si aucun trouvé par date, tenter la recherche par nom de plat
            if not matched_plannings:
                for p in user_plannings:
                    if p['nom_produit'].lower() in m_lower or any(w in p['nom_produit'].lower() for w in m_lower.split() if len(w) > 3):
                        matched_plannings.append(p)

            # Fallback si 1 seul planning existe au total dans la base pour cet utilisateur ET aucun plat spécifique n'a été recherché en vain
            clean_words = [re.sub(r"^[a-z]['’]", "", w) for w in m_lower.split()]
            food_words = [w for w in clean_words if len(w) > 3 and w not in ['décale', 'decale', 'déplace', 'deplace', 'repas', 'planning', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche', 'midi', 'soir', 'matin', 'demain', 'pour', 'change', 'changer', 'modifie', 'modifier', 'heure', 'créneau', 'creneau', 'seulement', 'seule']]
            if not matched_plannings and len(user_plannings) == 1 and not food_words:
                matched_plannings = user_plannings

            if len(matched_plannings) == 0:
                return {
                    "status": "missing_info",
                    "reply": "Je n'ai pas trouvé de repas planifié correspondant exactement à cette date ou à ce plat dans votre planning AYYOU.",
                    "cards": [],
                    "user_name": user_name
                }
            elif len(matched_plannings) > 1:
                options_str = "\n".join([f"- #{p['id']} : {p['nom_produit']} ({p['date_planifiee']} - {p['creneau_display']})" for p in matched_plannings])
                return {
                    "status": "disambiguation_required",
                    "reply": f"J'ai trouvé plusieurs repas planifiés pour ces critères :\n{options_str}\n\nLequel souhaitez-vous modifier ?",
                    "cards": [],
                    "user_name": user_name
                }

            target_planning = matched_plannings[0]

            if intent["action_type"] == "cancel_planning":
                action_proposal = {
                    "action_type": "cancel_planning",
                    "planning_id": target_planning["id"],
                    "summary": f"Annulation du repas '{target_planning['nom_produit']}' ({target_planning['date_planifiee']})"
                }
                return {
                    "status": "confirmation_required",
                    "reply": f"J'ai trouvé votre repas planifié :\n• Plat : {target_planning['nom_produit']} ({target_planning['nom_etablissement']})\n• Date : {target_planning['date_planifiee']} — {target_planning['creneau_display']}\n\nVoulez-vous vraiment annuler ce repas planifié ?",
                    "action_proposal": action_proposal,
                    "cards": [],
                    "user_name": user_name
                }

            # Extraction des changements demandés (Nouvelle date, Nouveau créneau, Nombre de personnes)
            target_date, target_date_label = cls._parse_target_date(msg_str)
            target_creneau, target_creneau_label = cls._parse_target_creneau(msg_str)

            # Si la date cible extraite est la même que la date source, chercher la deuxième mention de jour dans le texte
            days_in_msg = [d for d in cls.DAYS_MAP.keys() if d in m_lower]
            if len(days_in_msg) >= 2:
                target_day_name = days_in_msg[1]
                current_idx = timezone.now().date().weekday()
                target_idx = cls.DAYS_MAP[target_day_name]
                days_ahead = (target_idx - current_idx) % 7
                if days_ahead == 0:
                    days_ahead = 7
                t_date = timezone.now().date() + datetime.timedelta(days=days_ahead)
                target_date = t_date
                target_date_label = f"{cls.DAYS_FR[t_date.weekday()]} {t_date.day} {cls.MONTHS_FR[t_date.month]}"

            changes = {}
            if target_date:
                changes["date_planifiee"] = target_date.strftime('%Y-%m-%d')
            if target_creneau:
                changes["creneau"] = target_creneau

            qty_match = re.search(r'(\d+)\s*(?:personnes?|portions?|repas)', m_lower)
            if qty_match:
                changes["quantite"] = int(qty_match.group(1))

            if not changes:
                changes["date_planifiee"] = target_planning["date_planifiee"]

            new_date_str = changes.get("date_planifiee", target_planning["date_planifiee"])
            new_creneau_str = target_creneau_label or target_planning["creneau_display"]

            action_proposal = {
                "action_type": "update_planning",
                "planning_id": target_planning["id"],
                "nom_produit": target_planning["nom_produit"],
                "nom_etablissement": target_planning["nom_etablissement"],
                "current_date": target_planning["date_planifiee"],
                "current_creneau": target_planning["creneau_display"],
                "changes": changes,
                "summary": f"Déplacer '{target_planning['nom_produit']}' du {target_planning['date_planifiee']} ({target_planning['creneau_display']}) au {new_date_str} ({new_creneau_str})"
            }

            return {
                "status": "confirmation_required",
                "reply": f"J'ai trouvé votre repas planifié :\n• Plat : {target_planning['nom_produit']} ({target_planning['nom_etablissement']})\n• Actuel : {target_planning['date_planifiee']} — {target_planning['creneau_display']}\n\nJe peux le déplacer au :\n• Nouveau créneau : {new_date_str} — {new_creneau_str}\n\nVoulez-vous confirmer cette modification ?",
                "action_proposal": action_proposal,
                "cards": [],
                "user_name": user_name
            }

        # 7. TRAITEMENT DE LECTURE DU PLANNING
        if intent["is_planning_query"]:
            if not user_id:
                return {
                    "status": "success",
                    "reply": "Veuillez vous connecter à votre compte AYYOU pour consulter votre planning.",
                    "cards": [],
                    "user_name": user_name
                }
            plannings_res = get_user_plannings(user_id=user_id)
            if not plannings_res.get('success') or plannings_res.get('count', 0) == 0:
                return {
                    "status": "success",
                    "reply": "Vous n'avez aucun repas planifié pour le moment dans votre planning AYYOU.",
                    "cards": [],
                    "user_name": user_name
                }

            pl_items = plannings_res['results']
            items_str = "\n".join([f"- {p['date_planifiee']} ({p['creneau_display']}) : {p['quantite']}x {p['nom_produit']} chez {p['nom_etablissement']} ({p['prix_formate']})" for p in pl_items[:5]])
            return {
                "status": "success",
                "reply": f"Voici vos prochains repas planifiés dans PostgreSQL :\n\n{items_str}",
                "cards": [],
                "user_name": user_name
            }

        # 8. CONTRÔLE DE QUOTA POUR LA RECHERCHE INTELLIGENTE
        if is_dish_search and quota.is_exceeded():
            time_left_str = quota.get_formatted_time_remaining()
            seconds_remaining = quota.get_seconds_remaining()
            reply_limit_msg = (
                "Vous avez atteint votre limite de 7 recherches intelligentes.\n\n"
                "Vous pouvez continuer à rechercher des plats avec la barre de recherche AYYOU.\n\n"
                f"La recherche intelligente sera de nouveau disponible dans {time_left_str}."
            )
            return {
                "status": "quota_exceeded",
                "is_quota_exceeded": True,
                "quota_used": quota.search_count,
                "quota_max": AIChatQuota.MAX_QUOTA,
                "seconds_remaining": seconds_remaining,
                "formatted_time_remaining": time_left_str,
                "reset_at": quota.reset_at.isoformat() if quota.reset_at else None,
                "reply": reply_limit_msg,
                "cards": [],
                "user_name": user_name
            }

        # 9. Traitement des Intentions Spécifiques de Lecture (Commandes & Livraisons)
        if intent["is_order_intent"]:
            if not user_id:
                return {
                    "status": "success",
                    "reply": f"Veuillez vous connecter à votre compte AYYOU pour consulter vos commandes personnelles.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }
            res_orders = get_user_orders(user_id=user_id, limit=5)
            if not res_orders.get("success") or res_orders.get("count", 0) == 0:
                return {
                    "status": "success",
                    "reply": f"Je ne trouve aucune commande correspondant à votre compte AYYOU.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }

            db_context_str = "COMMANDES RÉELLES DU CLIENT CONNECTÉ (DONNÉES FACTUELLES EXACTES) :\n"
            for cmd in res_orders["results"]:
                prods_str = ", ".join([f"{p['quantite']}x {p['nom']}" for p in cmd["produits"]])
                db_context_str += f"- N° Commande: {cmd['numero_commande']} | Statut: {cmd['statut_display']} | Total: {cmd['total_formate']} | Produits: {prods_str}\n"

            matching_products = []
            recommendation_cards = []

        elif intent["is_delivery_intent"]:
            if not user_id:
                return {
                    "status": "success",
                    "reply": f"Veuillez vous connecter à votre compte AYYOU pour suivre l'état de votre livraison.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }
            res_orders = get_user_orders(user_id=user_id, limit=1)
            if not res_orders.get("success") or res_orders.get("count", 0) == 0:
                return {
                    "status": "success",
                    "reply": f"Je ne trouve aucune commande à suivre pour votre compte.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }

            last_order = res_orders["results"][0]
            deliv_res = get_delivery_status(order_id_or_number=last_order["commande_id"], user_id=user_id)
            if not deliv_res.get("success") or deliv_res.get("reason") == "NO_DELIVERY":
                return {
                    "status": "success",
                    "reply": f"Cette commande (N° {last_order['numero_commande']}) n'a pas encore de livraison disponible.",
                    "cards": [],
                    "user_name": user_name,
                    "quota_used": quota.search_count,
                    "quota_max": AIChatQuota.MAX_QUOTA,
                    "is_quota_exceeded": quota.is_exceeded()
                }

            d_info = deliv_res["delivery"]
            livreur_txt = f"Livreur: {d_info['livreur']['nom']}" if d_info.get('livreur') else "Livreur en cours d'attribution"
            db_context_str = f"LIVRAISON RÉELLE EN COURS POUR LA COMMANDE {d_info['numero_commande']} :\n- Statut: {d_info['statut_display']}\n- Adresse: {d_info['adresse_livraison']}\n- {livreur_txt}\n"

            matching_products = []
            recommendation_cards = []

        elif not is_dish_search and msg_str.lower() in cls.GREETING_PHRASES:
            # Salutations conversationnelles simples sans recherche de plats
            return {
                "status": "success",
                "reply": f"Bonjour {user_name} ! 🇸🇳 Je suis votre Conseiller Gastronomique AYYOU. Que souhaitez-vous déguster aujourd'hui à Dakar ?",
                "cards": [],
                "user_name": user_name,
                "quota_used": quota.search_count,
                "quota_max": AIChatQuota.MAX_QUOTA,
                "is_quota_exceeded": quota.is_exceeded()
            }

        else:
            # Recherche Catalogue / Produits
            if intent["latitude"] and intent["longitude"]:
                matching_products = search_by_location(
                    latitude=intent["latitude"],
                    longitude=intent["longitude"],
                    query=intent.get("food_query"),
                    category_slug=intent.get("category_slug"),
                    max_price=intent.get("budget_max"),
                    limit=4
                )
            else:
                matching_products = search_food(
                    query=intent.get("food_query"),
                    category_slug=intent.get("category_slug"),
                    max_price=intent.get("budget_max"),
                    location=intent.get("location"),
                    type_etablissement=intent.get("type_etablissement"),
                    is_available=True,
                    limit=4
                )

            # Consommer une recherche intelligente exécutée avec succès
            if is_dish_search:
                quota.search_count += 1
                quota.save(update_fields=['search_count'])

            if matching_products:
                db_context_str = "PRODUITS RÉELS DISPONIBLES EN BASE AYYOU (DONNÉES FACTUELLES EXACTES) :\n"
                for p in matching_products:
                    db_context_str += f"- ID: {p['id']} | Nom: {p['nom']} | Etablissement: {p['etablissement_nom']} ({p['etablissement_adresse']}) | Prix: {p['prix_formate']} | Disponible: Oui\n"
            else:
                db_context_str = "AUCUN PRODUIT NE CORRESPOND EXACTEMENT DANS LA BASE AYYOU POUR CES CRITÈRES."

            # Cartes pour produits
            recommendation_cards = []
            for p in matching_products[:2]:
                recommendation_cards.append({
                    "produit_id": p["id"],
                    "nom": p["nom"],
                    "etablissement_id": p["etablissement_id"],
                    "etablissement_nom": p["etablissement_nom"],
                    "adresse": p["etablissement_adresse"],
                    "temps_livraison": p.get("temps_livraison"),
                    "prix_base": p["prix"],
                    "prix_formate": p["prix_formate"],
                    "image_url": p["image_url"],
                    "est_disponible": p["est_disponible"]
                })

        # 10. Appel au modèle LLM local via Ollama API
        ai_reply_text = ""
        prompt_with_context = f"{SYSTEM_PROMPT}\nNom Client: {user_name}\nIntention Détectée: {intent}\nContexte Factuel BDD Réel:\n{db_context_str}\n\nMessage Client: \"{msg_str}\"\n\nRéponds de manière chaleureuse, naturelle et concise. Ne mentionne que les données présentes dans le contexte ci-dessus."

        try:
            payload = json.dumps({
                "model": cls.DEFAULT_MODEL,
                "prompt": prompt_with_context,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "max_tokens": 180
                }
            }).encode('utf-8')

            req = urllib.request.Request(cls.OLLAMA_URL, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=6) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                ai_reply_text = resp_data.get('response', '').strip()
        except Exception:
            if intent["is_order_intent"] or intent["is_delivery_intent"]:
                ai_reply_text = f"Voici les informations concernant votre compte : {db_context_str}"
            elif matching_products:
                top_p = matching_products[0]
                ai_reply_text = f"Pour régaler vos papilles à Dakar, je vous recommande vivement le {top_p['nom']} de l'établissement {top_p['etablissement_nom']} !"
            else:
                ai_reply_text = f"Désolé {user_name}, je n'ai pas trouvé de plat correspondant exactement à ces critères sur AYYOU."

        if not intent["is_order_intent"] and not intent["is_delivery_intent"] and not matching_products:
            ai_reply_text = f"Je n'ai trouvé aucun plat correspondant exactement à votre recherche sur AYYOU à Dakar. N'hésitez pas à élargir votre budget ou à utiliser la barre de recherche AYYOU !"
            recommendation_cards = []

        return {
            "status": "success",
            "reply": ai_reply_text,
            "cards": recommendation_cards,
            "intent": intent,
            "user_name": user_name,
            "quota_used": quota.search_count,
            "quota_max": AIChatQuota.MAX_QUOTA,
            "is_quota_exceeded": quota.is_exceeded(),
            "seconds_remaining": quota.get_seconds_remaining(),
            "formatted_time_remaining": quota.get_formatted_time_remaining()
        }

