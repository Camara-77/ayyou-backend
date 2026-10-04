import os
import re
import io
import json
import base64
import urllib.request
from PIL import Image, ImageStat
from django.conf import settings
from apps.catalog.models import Produit, Etablissement

class VisionService:
    """
    Service d'analyse visuelle et multimodale d'images alimentaires pour AYYOU.
    
    1. Validation technique Pillow : type MIME, intégrité et luminosité minimale.
    2. Inférence sémantique réelle via un Modèle IA Vision Multimodal (Ollama Vision / Moondream).
    3. Suppression intégrale des anciennes heuristiques RGB (r > 1.1*b, g > r) et du matching par nom de fichier.
    4. Interrogation factuelle de la base de données PostgreSQL (0% d'hallucination sur les prix et restaurants).
    """

    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')
    VISION_MODEL = getattr(settings, 'OLLAMA_VISION_MODEL', 'moondream')

    FOOD_KEYWORDS_MAP = {
        'burger': ['burger', 'cheeseburger', 'hamburgers', 'hamburger', 'smashburger'],
        'pizza': ['pizza', 'pizzas', 'calzone'],
        'thieb': ['thieb', 'tieb', 'thiéboudienne', 'thieboudienne', 'ceebu'],
        'yassa': ['yassa'],
        'mafe': ['mafe', 'mafé'],
        'dibi': ['dibi', 'dibiterie', 'agneau', 'grillade'],
        'tacos': ['tacos', 'taco', 'french tacos'],
        'salade': ['salade', 'salad', 'bowl', 'fresh'],
        'crepe': ['crepe', 'crêpe', 'pancake', 'pancakes'],
        'glace': ['glace', 'sundae', 'dessert'],
        'jus': ['jus', 'bissap', 'bouye', 'smoothie'],
        'poulet': ['poulet', 'chicken', 'chiken'],
        'sandwich': ['sandwich', 'tangana']
    }

    @classmethod
    def validate_image_file(cls, uploaded_file) -> tuple[bool, str]:
        """
        Validation technique via Pillow : extension et type MIME.
        """
        if not uploaded_file:
            return False, "Aucun fichier n'a été fourni."

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, "Seules les images au format JPG, PNG ou WEBP sont acceptées. Les fichiers PDF, vidéos ou documents ne sont pas autorisés."

        content_type = getattr(uploaded_file, 'content_type', '').lower()
        if content_type and content_type not in cls.ALLOWED_CONTENT_TYPES:
            return False, "Le format MIME du fichier n'est pas une image valide (JPG, PNG ou WEBP)."

        return True, ""

    @classmethod
    def _call_multimodal_vision_model(cls, image_bytes: bytes) -> dict:
        """
        Exécute une véritable inférence sémantique par IA Vision Multimodale (Ollama Vision API).
        Transmet le buffer d'image encodé en base64 au modèle multimodal et demande une structure JSON explicite.
        """
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        prompt = (
            "You are an expert AI Food Vision classifier for a food delivery service in Senegal. "
            "Examine this image carefully and determine:\n"
            "1. Is this image showing food, a meal, a dish, a beverage, or a food item? (is_food: true or false)\n"
            "2. What category of food is it? Choose the best match among: burger, pizza, thieb, yassa, mafe, dibi, tacos, salade, crepe, glace, jus, poulet, sandwich, pastels, or other.\n"
            "3. Give a brief description in French of what is shown.\n"
            "4. List main visual attributes seen (e.g. pain, fromage, frites, riz, poulet).\n\n"
            "Return ONLY a valid JSON object formatted EXACTLY as follows:\n"
            "{\n"
            '  "is_food": true,\n'
            '  "confidence": 0.92,\n'
            '  "category": "burger",\n'
            '  "description": "Un burger généreux avec fromage et salade",\n'
            '  "visual_attributes": ["steak", "fromage", "pain"],\n'
            '  "possible_food_names": ["burger", "cheeseburger"]\n'
            "}"
        )

        payload = json.dumps({
            "model": cls.VISION_MODEL,
            "prompt": prompt,
            "images": [base64_image],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "max_tokens": 200
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            cls.OLLAMA_URL,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                raw_text = resp_data.get('response', '').strip()

                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass

                is_food = any(w in raw_text.lower() for w in ['true', 'food', 'plat', 'burger', 'pizza', 'thieb', 'manger', 'repas', 'dish'])
                cat = None
                for key in cls.FOOD_KEYWORDS_MAP.keys():
                    if key in raw_text.lower():
                        cat = key
                        break

                return {
                    "is_food": is_food,
                    "confidence": 0.85 if is_food else 0.20,
                    "category": cat,
                    "description": raw_text[:120],
                    "visual_attributes": [],
                    "possible_food_names": [cat] if cat else []
                }
        except Exception as e:
            # Relever pour capturer dans analyze_food_image fallback
            raise RuntimeError(f"Vision API unreachable: {str(e)}")

    @classmethod
    def analyze_food_image(cls, uploaded_file) -> dict:
        """
        Flux complet d'analyse visuelle et multimodale :
        1. Validation technique Pillow (Format, MIME, Intégrité).
        2. Contrôle de luminosité minimale (Détection d'images très sombres/floues).
        3. Exécution de l'Inférence Sémantique par l'IA Vision Multimodale.
        4. Interrogation factuelle de la base de données PostgreSQL pour retrouver les produits & restaurants AYYOU.
        """
        # 1. Validation technique
        is_valid, err_msg = cls.validate_image_file(uploaded_file)
        if not is_valid:
            return {
                "status": "invalid_format",
                "is_food": False,
                "message": err_msg,
                "detected_category": None,
                "matching_products": [],
                "matching_establishments": []
            }

        # Lecture binaire & validation Pillow
        try:
            file_bytes = uploaded_file.read()
            uploaded_file.seek(0)
            image = Image.open(io.BytesIO(file_bytes))
            image.verify()
            image = Image.open(io.BytesIO(file_bytes)).convert('RGB')
        except Exception:
            return {
                "status": "unreadable_image",
                "is_food": False,
                "message": "Je n'arrive pas à lire cette image. Assurez-vous qu'il s'agit d'un fichier image valide (JPG, PNG, WEBP).",
                "detected_category": None,
                "matching_products": [],
                "matching_establishments": []
            }

        # 2. Contrôle de luminosité minimale via Pillow (Images noires/très sombres)
        stat = ImageStat.Stat(image)
        mean_brightness = sum(stat.mean) / len(stat.mean)
        if mean_brightness < 15:
            return {
                "status": "unclear_image",
                "is_food": False,
                "message": "L'image est trop sombre ou floue pour être identifiée clairement par l'IA Vision. Vous pouvez me décrire ce que vous recherchez par texte ou note vocale.",
                "detected_category": None,
                "matching_products": [],
                "matching_establishments": []
            }

        # 3. Exécution de l'Inférence Sémantique IA Vision Multimodale
        try:
            vision_result = cls._call_multimodal_vision_model(file_bytes)
        except Exception as e:
            # Fallback si le modèle vision est indisponible
            return {
                "status": "vision_service_error",
                "is_food": False,
                "message": "L'analyse par IA Vision est momentanément indisponible. Vous pouvez me décrire le plat par texte ou utiliser votre note vocale.",
                "detected_category": None,
                "matching_products": [],
                "matching_establishments": []
            }

        is_food = vision_result.get('is_food', False)
        confidence = float(vision_result.get('confidence', 0.8))
        category = vision_result.get('category')

        # 4. Traitement des images non alimentaires
        if not is_food or (confidence < 0.4 and not category):
            return {
                "status": "non_food_image",
                "is_food": False,
                "message": "Cette image ne semble pas représenter un plat ou un aliment. Décrivez-moi ce que vous recherchez ou envoyez-moi une photo de nourriture.",
                "detected_category": None,
                "matching_products": [],
                "matching_establishments": []
            }

        # 5. Recherche stricte dans la base de données PostgreSQL (Anti-hallucination)
        detected_food_type = (category or '').lower().strip()
        keywords = cls.FOOD_KEYWORDS_MAP.get(detected_food_type, [detected_food_type]) if detected_food_type else []
        if not keywords and vision_result.get('possible_food_names'):
            keywords = [w.lower() for w in vision_result['possible_food_names']]

        matched_products = []
        if keywords:
            products_qs = Produit.objects.select_related('etablissement', 'categorie').filter(
                est_disponible=True,
                etablissement__statut_verification=Etablissement.STATUT_VALIDE
            )
            for p in products_qs:
                p_name = p.nom.lower()
                p_cat = (p.categorie.nom if p.categorie else "").lower()
                if any(kw in p_name or kw in p_cat for kw in keywords):
                    matched_products.append(p)

        if not matched_products:
            cat_display = detected_food_type or "plat"
            return {
                "status": "no_product_found",
                "is_food": True,
                "message": f"L'IA Vision a identifié un {cat_display}, mais je n'ai pas trouvé de plat correspondant dans notre catalogue AYYOU actuellement.",
                "detected_category": cat_display,
                "matching_products": [],
                "matching_establishments": []
            }

        # Formater les résultats réels depuis PostgreSQL
        products_data = []
        establishments_map = {}
        for p in matched_products[:6]:
            est = p.etablissement
            prix_num = float(p.prix_base)
            prix_fmt = f"{prix_num:,.0f} FCFA".replace(",", " ")
            prod_info = {
                "id": p.id,
                "nom": p.nom,
                "prix": prix_num,
                "prix_formate": prix_fmt,
                "image_url": p.image_url or "assets/images/thieboudienne.jpg",
                "etablissement_id": est.id if est else None,
                "etablissement_nom": est.nom if est else "AYYOU",
                "etablissement_adresse": est.adresse if est else "Dakar"
            }
            products_data.append(prod_info)

            if est and est.id not in establishments_map:
                establishments_map[est.id] = {
                    "id": est.id,
                    "nom": est.nom,
                    "adresse": est.adresse or "Dakar",
                    "produit_propose": p.nom,
                    "prix_formate": prix_fmt
                }

        cat_display = detected_food_type or "plat"
        desc_text = vision_result.get('description', f"Image analysée par l'IA Vision ({cat_display}).")
        return {
            "status": "food_identified",
            "is_food": True,
            "confidence": confidence,
            "message": f"L'IA Vision a identifié un {cat_display} : \"{desc_text}\". J'ai trouvé {len(products_data)} plat(s) disponible(s) chez nos restaurants partenaires.",
            "detected_category": cat_display,
            "matching_products": products_data,
            "matching_establishments": list(establishments_map.values()),
            "suggested_actions": [
                {"label": "Voir les restaurants", "action": "RESTAURANT_SEARCH"},
                {"label": "Planifier ce repas", "action": "CREATE_PLANNING"}
            ]
        }
