import urllib.request
import json
import re
from decimal import Decimal
from .prompts import SYSTEM_PROMPT
from .tools import (
    search_food,
    search_establishments,
    search_by_budget,
    search_by_category,
    get_product,
    get_establishment
)


class AIService:
    """
    Service d'IA Conseiller Gastronomique AYYOU Dakar.
    Comprenant :
    1. Détection des intentions & fusion de contexte conversationnel
    2. Protection anti-prompt-injection
    3. Exécution d'outils ORM 100% réels sur PostgreSQL
    4. Validation stricte des données (zéro hallucination factuelle)
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
    def extract_intent(cls, message: str, history: list = None) -> dict:
        """
        Extrait une intention structurée à partir du message courant et de l'historique conversationnel.
        """
        intent = {
            "food_query": None,
            "budget_max": None,
            "location": None,
            "type_etablissement": None,
            "category_slug": None,
            "people_count": None
        }

        # 1. Analyser d'abord l'historique récent pour conserver le contexte
        combined_text = ""
        if history and isinstance(history, list):
            for h in history[-4:]:  # 4 derniers messages
                if isinstance(h, dict) and h.get('sender') == 'user':
                    combined_text += " " + h.get('text', '')
        combined_text += " " + message
        c_lower = combined_text.lower()
        m_lower = message.lower()

        # 2. Budget max
        budget_match = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)?', m_lower)
        if budget_match and any(kw in m_lower for kw in ['budget', 'moins de', 'max', 'autour de', 'fcfa', 'francs', 'cfa', 'pour']):
            try:
                intent["budget_max"] = float(budget_match.group(1))
            except ValueError:
                pass

        if not intent["budget_max"]:
            # Vérifier si un budget était spécifié dans l'historique
            h_budget_match = re.search(r'(\d+)\s*(?:fcfa|f|cfa|francs)?', c_lower)
            if h_budget_match and any(kw in c_lower for kw in ['budget', 'moins de', 'max', 'fcfa', 'francs']):
                try:
                    intent["budget_max"] = float(h_budget_match.group(1))
                except ValueError:
                    pass

        # 3. Localisation / Quartier
        for loc in cls.DAKAR_LOCATIONS:
            if loc in m_lower:
                intent["location"] = loc
                break
        if not intent["location"]:
            for loc in cls.DAKAR_LOCATIONS:
                if loc in c_lower:
                    intent["location"] = loc
                    break

        # 4. Catégorie
        if any(w in c_lower for w in ['sénégal', 'senegal', 'sénégalaise', 'senegalaise', 'sénégalais', 'senegalais', 'thieb', 'yassa', 'mafé']):
            intent["category_slug"] = 'senegalais'
        elif any(w in c_lower for w in ['burger', 'tacos', 'pizza', 'fast food']):
            intent["category_slug"] = 'fast-food'

        # 5. Type d'établissement
        if any(w in c_lower for w in ['vendeur', 'domicile', 'fait maison', 'traiteur']):
            intent["type_etablissement"] = 'VENDEUR'
        elif any(w in c_lower for w in ['restaurant', 'resto', 'fast food', 'bistro']):
            intent["type_etablissement"] = 'RESTAURANT'

        # 6. Plat / Mot clé culinaire
        for food in cls.FOOD_KEYWORDS:
            if food in m_lower:
                intent["food_query"] = food
                break
        if not intent["food_query"]:
            for food in cls.FOOD_KEYWORDS:
                if food in c_lower:
                    intent["food_query"] = food
                    break

        # S'il n'y a aucun mot clé connu ET aucune catégorie/budget/lieu -> fallback sur la phrase
        if not intent["food_query"] and not intent["category_slug"] and not intent["budget_max"] and not intent["location"] and len(m_lower.strip()) > 2:
            intent["food_query"] = m_lower.strip()[:30]

        return intent

    @classmethod
    def process_chat_message(cls, message: str, user_name: str = "Client", context: dict = None, history: list = None) -> dict:
        msg_str = message.strip()

        # 1. Vérification Anti-Prompt-Injection
        if cls.check_prompt_injection(msg_str):
            return {
                "status": "success",
                "reply": f"Bonjour {user_name} ! Je suis votre Conseiller Gastronomique AYYOU 🇸🇳. Je suis uniquement là pour vous guider vers les meilleurs plats et restaurants disponibles à Dakar !",
                "cards": [],
                "user_name": user_name
            }

        # 2. Extraction d'intention & contexte conversationnel
        intent = cls.extract_intent(msg_str, history)

        # 3. Exécution des outils ORM 100% réels
        matching_products = search_food(
            query=intent.get("food_query"),
            category_slug=intent.get("category_slug"),
            max_price=intent.get("budget_max"),
            location=intent.get("location"),
            type_etablissement=intent.get("type_etablissement"),
            is_available=True,
            limit=4
        )

        # 4. Construction du contexte réel pour le LLM
        if matching_products:
            db_context_str = "PRODUITS RÉELS DISPONIBLES EN BASE AYYOU (DONNÉES FACTUELLES EXACTES) :\n"
            for p in matching_products:
                db_context_str += f"- ID: {p['id']} | Nom: {p['nom']} | Etablissement: {p['etablissement_nom']} ({p['etablissement_adresse']}) | Prix: {p['prix_formate']} | Disponible: Oui\n"
        else:
            db_context_str = "AUCUN PRODUIT NE CORRESPOND EXACTEMENT DANS LA BASE AYYOU POUR CES CRITÈRES."

        # 5. Appel au modèle LLM local via Ollama API
        ai_reply_text = ""
        prompt_with_context = f"{SYSTEM_PROMPT}\nNom Client: {user_name}\nIntention Détectée: {intent}\nContexte Catalogue Réel:\n{db_context_str}\n\nMessage Client: \"{msg_str}\"\n\nRéponds de manière chaleureuse, naturelle et concise. Ne mentionne que les produits présents dans le contexte ci-dessus."

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
            # Fallback déterministe si Ollama est indisponible ou long
            if matching_products:
                top_p = matching_products[0]
                ai_reply_text = f"Pour régaler vos papilles à Dakar, je vous recommande vivement le {top_p['nom']} de l'établissement {top_p['etablissement_nom']} !"
            else:
                ai_reply_text = f"Désolé {user_name}, je n'ai pas trouvé de plat correspondant exactement à ces critères sur AYYOU. N'hésitez pas à ajuster votre budget ou le quartier !"

        # 6. Sécurité Anti-Hallucination : Si 0 résultat en BDD, vérifier que le texte LLM n'invente rien
        if not matching_products:
            ai_reply_text = f"Je n'ai trouvé aucun plat correspondant exactement à votre recherche sur AYYOU à Dakar. N'hésitez pas à élargir votre budget ou à choisir un autre quartier !"
            recommendation_cards = []
        else:
            recommendation_cards = []
            for p in matching_products[:2]:
                recommendation_cards.append({
                    "produit_id": p["id"],
                    "nom": p["nom"],
                    "etablissement_id": p["etablissement_id"],
                    "etablissement_nom": p["etablissement_nom"],
                    "adresse": p["etablissement_adresse"],
                    "temps_livraison": p["temps_livraison"],
                    "prix_base": p["prix"],
                    "prix_formate": p["prix_formate"],
                    "image_url": p["image_url"],
                    "est_disponible": p["est_disponible"]
                })

        return {
            "status": "success",
            "reply": ai_reply_text,
            "cards": recommendation_cards,
            "intent": intent,
            "user_name": user_name
        }
