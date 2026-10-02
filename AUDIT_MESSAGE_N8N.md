# AUDIT — TRAÇAGE & ORIGINE DU MESSAGE "ENVOYÉ AUTOMATIQUEMENT PAR N8N"

> [!IMPORTANT]
> **STATUT DE L'AUDIT** : Recherche et traçage effectués à 100%. Aucune modification de code ni suppression de texte n'a été effectuée.

---

## 1. TRAÇAGE DE LA CHAÎNE D'ENVOI (END-TO-END)

```
[ AYYOU Django DB ] 
       │
       ▼ (Événement Admin : Validation/Refus)
[ Django N8nNotificationService ]
       │
       ▼ (Payload JSON pur via HTTP POST Webhook)
[ Webhook n8n (Entrée) ]
       │
       ▼ (Workflow n8n & Node de mise en forme)
[ Node d'envoi (Email / SMTP / WhatsApp) ] ───► Contient la mention "Envoyé par n8n"
       │
       ▼ (API / SMTP)
[ Fournisseur de Messagerie ]
       │
       ▼
[ Destinataire Final (Pro / Livreur / Client) ]
```

---

## 2. ORIGINE EXACTE DU TEXTE

| Source potentielle | Présence du texte | Explication |
| :--- | :---: | :--- |
| **1. Workflow n8n** | **OUI (ORIGINE STRICTE)** | Le texte est rédigé ou inséré directement dans la configuration du **Node d'envoi** (ou un Node *Set / Code*) au sein du workflow n8n. |
| **2. Payload AYYOU (Django)** | **NON** | Django envoie uniquement un objet JSON brut avec des variables métier (`event`, `name`, `email`, `login_url`). Aucun texte de signature n'est transmis par Django. |
| **3. Template Django** | **NON** | Les templates Django (`base_notification.html`) utilisent la mention propre : *"Cet email automatique vous a été envoyé par la plateforme AYYOU."* |
| **4. Fournisseur de messagerie** | **NON** | Le fournisseur (SMTP, SendGrid, Twilio) délivre uniquement le corps du message qu'il reçoit de n8n sans y ajouter cette mention. |
| **5. Interface de test/démo** | **PARTIELLE** | C'est le modèle de message par défaut (default template) souvent utilisé lors de la création initiale des nœuds n8n. |

---

## 3. DÉTAILS DES COMPOSANTS IDENTIFIÉS

### A. Côté Backend AYYOU (Django)
* **Fichier source** : [apps/notifications/n8n_service.py](file:///c:/Users/HP/Desktop/Ayyou-backend/apps/notifications/n8n_service.py)
* **Méthodes d'envoi** : `send_pro_approval_for_etablissement`, `send_pro_approval_for_driver`, `send_pro_rejection_for_etablissement`, `send_pro_rejection_for_driver`.
* **Payload JSON exact transmis par Django** :
  ```json
  {
    "event": "PRO_ACCOUNT_APPROVED",
    "type": "RESTAURANT",
    "user_id": 12,
    "name": "Le Restaurant Teranga",
    "email": "resto@teranga.sn",
    "phone": "+221770000000",
    "login_url": "http://localhost:4200/pro/login"
  }
  ```
  *Note : Comme constaté, ce payload ne contient aucune signature ni mention de n8n.*

### B. Côté n8n (Instance d'Automatisation)
* **Workflow concerné** : Workflow de notification des comptes Pro/Livreurs (ex: `AYYOU - Notifications Validation Compte`).
* **Node concerné** : Le nœud d'envoi de message (node **Send Email** / **Gmail** / **SMTP** / **Twilio** / **WhatsApp**).
* **Champ concerné** : Champ **HTML Body** ou **Text Message** du nœud d'envoi.
* **Contenu du champ dans n8n** :
  ```html
  <p>Bonjour {{ $json.name }}, votre compte a été validé...</p>
  ...
  <footer style="font-size: 11px; color: #888;">
    Ce message a été envoyé automatiquement par n8n.
  </footer>
  ```
* **Fournisseur utilisé** : Le service de transport SMTP ou API configuré dans les Credentials du nœud n8n.

---

## 4. CONCLUSION ET RECOMMANDATIONS DE CORRECTION

1. La mention **"Ce message a été envoyé automatiquement par n8n"** réside **exclusivement dans l'éditeur de workflow de votre instance n8n**.
2. Pour personnaliser ou supprimer cette mention dans le futur (lorsque vous me donnerez l'instruction), il suffira d'éditer le template HTML/Texte du node d'envoi dans l'interface n8n pour le remplacer par une signature officielle AYYOU :
   ```html
   <p>Cet email automatique vous a été envoyé par la plateforme AYYOU.</p>
   ```
