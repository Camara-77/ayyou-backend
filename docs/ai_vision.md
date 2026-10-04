# Documentation Technique — IA Vision Multimodale AYYOU

Ce document décrit l'architecture, le fonctionnement, la configuration et la sécurité du service d'Analyse IA Visuelle & Multimodale d'images d'AYYOU (`apps/ai/vision_service.py`).

---

## 1. Modèle & Moteur Vision
- **Modèle Vision Principal** : `moondream` (Inférence multimodale locale via l'API Ollama `http://127.0.0.1:11434/api/generate`).
- **Description** : Modèle vision open-source compact (1.6B paramètres) optimisé pour l'analyse visuelle zéro-shot, la description sémantique de nourriture et la classification de plats.
- **Support des formats** : JPG, JPEG, PNG, WEBP (validation MIME et extension stricte).

---

## 2. Architecture du Flux Vision

```
[ UTILISATEUR ] (Photo de plat importée ou collée via Ctrl+V)
       │
       ▼
[ ANGULAR FRONTEND ] ──(FormData: image)──> [ POST /api/ai/vision-analyze/ ]
                                                      │
                                                      ▼
                                            [ AIVisionAnalyzeView ]
                                                      │
                                                      ▼
                                         [ VisionService.analyze_food_image() ]
                                                      │
       ┌──────────────────────────────────────────────┴──────────────────────────────┐
       │ 1. Pillow : Validation MIME, intégrité & contrôle luminosité (black < 15)   │
       │ 2. Encodage Base64 du buffer binaire de l'image                             │
       │ 3. Inférence Ollama Vision API (moondream)                                  │
       └──────────────────────────────────────────────┬──────────────────────────────┘
                                                      │ (JSON sémantique)
                                                      ▼
                                       [ PostgreSQL Catalogue AYYOU ]
                                (Produit.objects.filter(est_disponible=True))
                                                      │
                                                      ▼
                                       [ Réponse JSON Enrichie ]
                      (Cartes de plats/restaurants réels + Actions suggérées)
```

---

## 3. Format du Payload et de la Réponse

### Requête vers le Modèle Vision
- **Endpoint** : `POST http://127.0.0.1:11434/api/generate`
- **Body Payload** :
```json
{
  "model": "moondream",
  "prompt": "You are an expert AI Food Vision classifier...",
  "images": ["<base64_encoded_image_string>"],
  "stream": false,
  "options": {
    "temperature": 0.1,
    "max_tokens": 200
  }
}
```

### Réponse Structurée par l'IA Vision
```json
{
  "is_food": true,
  "confidence": 0.92,
  "category": "burger",
  "description": "Un burger généreux avec fromage et salade",
  "visual_attributes": ["steak", "fromage", "pain"],
  "possible_food_names": ["burger", "cheeseburger"]
}
```

---

## 4. Rôle de Pillow vs IA Vision

- **Pillow (PIL)** : Conservé **exclusivement** pour la validation technique (MIME, intégrité du fichier image, dimensions et détection des images complètement noires/sombre `mean_brightness < 15`).
- **Modèle IA Vision** : Assure **100% de la compréhension sémantique**, de la classification et de la description visuelle du plat.
- **Suppression intégrale des anciennes heuristiques RGB** (`r > 1.1*b`, `g > r`) et de l'analyse basée sur le nom du fichier.

---

## 5. Garanties Anti-Hallucination & Sécurité

1. **Source de Vérité PostgreSQL** : Le modèle Vision qualifie uniquement la catégorie et la description. Les prix, les restaurants partenaires et la disponibilité proviennent exclusivement des tables `Produit` et `Etablissement` de PostgreSQL.
2. **Gestion des Images Non-Alimentaires** : Si l'IA détecte `is_food: false`, le service renvoie `status: "non_food_image"` sans interroger la base de données.
3. **Fallback Sécurisé** : En cas d'indisponibilité du service Vision local, un message d'erreur clair informe l'utilisateur d'utiliser la saisie texte ou la note vocale sans bloquer l'application.
4. **Sécurité des Fichiers** : Aucune image temporaire sensible n'est conservée indéfiniment sur disque ; les buffers binaires sont traités en mémoire vive.

---

## 6. Tests & Validation

- **Suite de tests Django** : `python manage.py test apps.ai.tests.test_planning_ai apps.ai.tests.test_actionable_ai`
- **Build Angular Production** : `npx ng build --configuration production`
