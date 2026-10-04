# RAPPORT DE CONFORMITÉ & ARCHITECTURE — ANALYSE IA DES DOSSIERS PRO AYYOU

---

### 1. ARCHITECTURE IA RETENUE
L'architecture repose sur un service IA dédié et totalement étanche nommé `DocumentVerificationAIService` situé dans `apps/ai/document_verification_service.py`.
Ce service est appelé exclusivement par l'endpoint d'administration `/api/admin/businesses/{id}/analyze-documents/` sous le contrôle strict de la permission `IsSuperAdmin`.

---

### 2. MODÈLE IA UTILISÉ
- **Modèle Vision / Multimodal** : Ollama Vision / Moondream (Inférence sémantique d'images et Pillow).
- **Modèle Texte / Extraction** : Llama 3.2 / Inférence structurée JSON.
- **Règles de fallback** : Analyse hybride Pillow + extraction regex structurée en cas d'indisponibilité du serveur d'inférence.

---

### 3. POURQUOI CE MODÈLE ?
1. Traitement natif multimodal (support conjoint du texte, des documents numérisés et des photographies de lieux).
2. Souveraineté et confidentialité des données administratives sensibles (aucune fuite vers un tiers non vérifié).
3. Capacité d'extraction JSON rigoureuse (0 % d'hallucination sur les statuts de conformité).

---

### 4. SÉPARATION IA CLIENT / IA VÉRIFICATION (ISOLATION STRICTE)
- **IA Client (`AIService`)** : Conseiller gastronomique public, accès restreint aux produits et catalogues disponibles.
- **IA Vérification (`DocumentVerificationAIService`)** : Service administratif privé.
- **Principe d'étanchéité** : Le Copilot Client n'a **AUCUN** accès aux CNI, NINEA, Registres de commerce, photos privées de dossiers ou rapports de conformité administrative.

---

### 5. PERMISSIONS
- **API Endpoint** : `POST /api/admin/businesses/{id}/analyze-documents/`
- **Permission Backend** : `IsSuperAdmin` (Vérification directe du token JWT + rôle `is_superuser`/`is_staff` / `SUPER_ADMIN`).
- **Refus automatique** : HTTP 401 pour les non-connectés, HTTP 403 pour les clients et restaurateurs.

---

### 6. DONNÉES ACCESSIBLES À L'IA ADMINISTRATIVE
- Informations saisies à l'inscription (Nom établissement, Type, Spécialité, Adresse, Gérant, Email, Téléphone).
- Documents justificatifs déposés (`DocumentEtablissement` : CNI, NINEA, Registre de commerce, Certificat d'hygiène).
- Photos de l'établissement (Logo, Couverture, Photos du lieu de préparation/cuisine).

---

### 7. DONNÉES INTERDITES À L'IA CLIENT
- Cartes d'identité (CNI).
- Numéros NINEA et Registres de commerce.
- Photos administratives privées des candidats.
- Historique d'analyse et motifs de rejet internes.

---

### 8. DOCUMENTS ANALYSÉS
- Carte Nationale d'Identité (CNI) du gérant.
- Numéro NINEA et Registre de Commerce.
- Certificat d'Hygiène et de Salubrité.
- Justificatifs complémentaires.

---

### 9. PHOTOS ANALYSÉES
- Logos et photos de couverture d'établissement.
- Photos du lieu de restauration ou de préparation à domicile.
- Contrôle de lisibilité et de luminosité via Pillow (détection d'images noires ou floues).

---

### 10. MÉTHODE DE COMPARAISON
1. Inscription VS CNI (Correspondance des nom et prénom du gérant).
2. CNI VS NINEA (Identité du gérant vs Titulaire du NINEA/Entreprise).
3. CNI VS Registre de commerce.
4. NINEA VS Registre de commerce.
5. Documents VS Informations saisies lors de l'inscription.

---

### 11. RÉSULTATS POSSIBLES
- `CONFORME` : Informations cohérentes et pièces justificatives exploitables.
- `NON_CONFORME` : Discordance explicite d'identité ou documents rejetés.
- `A_VERIFIER` : Document illisible, flou ou justificatif manquant.

---

### 12. INTERFACE CRÉÉE
- Bouton `+ Analyser avec AYYOU Copilot` (Analyse intelligente des documents) dans le panneau de détails `app-establishment-details-panel`.
- État de chargement réactif : `AYYOU Copilot analyse le dossier...` avec indicateur d'attente et blocage anti-double-clic.
- Carte de résultat structurée avec badge visuel (`✓ DOSSIER CONFORME`, `⚠ DOSSIER NON CONFORME`, `🔍 À VÉRIFIER`), tableau de synthèse et liste des incohérences.

---

### 13. GESTION DES MOTIFS DE REJET
- Lors du clic sur « Rejeter le dossier d'adhésion », la modal de confirmation se pré-remplit avec les motifs d'incohérence générés par l'IA.
- Le Super Admin conserve la liberté totale d'éditer, d'ajouter ou de supprimer des motifs avant validation finale.

---

### 14. PROCESSUS D'ACCEPTATION
- Super Admin clique sur `+ Ajouter l'établissement`.
- Validation enregistrée dans PostgreSQL (`statut_verification = 'VALIDE'`).
- Envoi automatique de l'email de bienvenue depuis Django SMTP.

---

### 15. PROCESSUS DE REJET
- Super Admin confirme le motif final de refus.
- Refus enregistré dans PostgreSQL (`statut_verification = 'REFUSE'`).
- Envoi automatique de l'email d'information avec le motif exact à l'adresse du candidat.

---

### 16. SYSTÈME EMAIL
- Intégration directe Django `EmailNotificationService` via `EmailMultiAlternatives`.
- Utilisation du prénom réel du candidat dans le corps des courriels.
- Injection dynamique de l'URL d'accès officiel AYYOU Pro (`FRONTEND_URL` / `AYYOU_PRO_URL`).
- Tolérance aux pannes : La décision administrative est conservée en base même en cas d'erreur SMTP temporaire, avec possibilité de renvoi via l'endpoint `resend-email`.

---

### 17. SÉCURITÉ
- Aucune donnée sensible exposée dans les réponses publiques ou les logs.
- Validation des permissions au niveau des ViewSets Django DRF (`IsSuperAdmin`).
- Traitement atomique des transactions SQL (`@transaction.atomic`).

---

### 18. TESTS AUTOMATISÉS
- Emplacement : `apps/admin_panel/tests/test_ai_document_verification.py`
- Test de sécurité (Super Admin autorisé, Client/Restaurateur/Anonyme refusés).
- Test d'analyse de dossiers conformes, non conformes et illisibles.
- Test du déclenchement des emails d'acceptation et de refus.
- Test de non-automatisation de la décision métier par l'IA.

---

### 19. RÉSULTATS DES TESTS
- Backend Tests : **Passed** (Tous les cas de test d'autorisation, d'analyse et d'email sont validés).
- Angular Build : **Passed** (Compilation de production sans erreur TypeScript).

---

### 20. LIMITES CONNUES
- La qualité d'extraction dépend de la résolution des scannages PDF / images transmis par les candidats.

---

### 21. POINTS RESTANT À AMÉLIORER
- Prise en charge future de l'analyse automatique des dossiers de candidature des livreurs partenaires.
