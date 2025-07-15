# Analytics MOS v2

## Présentation du projet

Analytics MOS est une plateforme d'analyse avancée - **CORRECTION_COLONNES_DUPLICATAS.md, CORRECTION_FORMAT_DECIMAL.md** : Documentation sur les corrections de données.
- **NOTES_RECOMMANDATION_CLASSIFICATION.md** : Documentation technique complète du pipeline des colonnes de recommandation.
- **NOTE_DF_MERGE.md** : Documentation détaillée du cycle de vie du DataFrame de fusion df_merge.
  
- **MODÈLES IA AVANCÉS** : Le système intègre des modèles d'IA avancés pour l'analyse automatique de sentiment et propose une segmentation intelligente des agences selon leur performance et satisfaction client.

  
- ## Structure du projet
```
analytics_mos_v2/
│
├── backend/                  # Backend API (Flask)
│   ├── src/                  # Code source Python (API, services, modules IA, configs)
│   │   ├── api/              # API REST (routes, contrôleurs, modèles de données)
│   │   │   ├── routes/       # Définition des endpoints Flask
│   │   │   ├── controllers/  # Logique métier et traitement des données
│   │   │   └── models/       # Schémas de données (SQLAlchemy)
│   │   ├── core/             # Initialisation de la base de données, configuration Flask
│   │   ├── modules/ai/       # Modules d'IA :
│   │   │   ├── sentiment.py                  # Analyse de sentiment rapide (TextBlob)
│   │   │   ├── sentiment_camembert.py        # Analyse de sentiment avancée (BERT multilingue)
│   │   │   └── siret_cleaner.py              # Nettoyage des SIRET
│   │   ├── configs/          # Fichiers de configuration Python (development.py, production.py)
│   │   └── utils/            # Fonctions utilitaires diverses (__init__.py)
│   ├── data/
│   │   ├── input/            # Fichiers sources (Excel, CSV bruts)
│   │   └── output/           # Fichiers générés (df_main.csv, exports CSV/Excel)
│   ├── instance/
│   │   └── dev_db.sqlite3    # Base SQLite locale (optionnelle)
│   ├── requirements.txt      # Dépendances backend (pip freeze)
│   ├── main.py               # Point d'entrée Flask (serveur API)
│   └── venv/                 # Environnement virtuel Python (backend)
│
├── frontend/                 # Frontend utilisateur (Streamlit)
│   ├── src/                  # Code source Streamlit (pages, services, utils)
│   │   ├── app/pages/        # Pages de l'application Streamlit
│   │   ├── configs/          # Configurations spécifiques frontend
│   │   ├── core/             # Fonctions cœur de l'app
│   │   ├── services/         # Services d'appel API
│   │   └── utils/            # Fonctions utilitaires
│   ├── requirements.txt      # Dépendances frontend (pip freeze)
│   ├── main.py               # Point d'entrée Streamlit
│   └── venv/                 # Environnement virtuel Python (frontend)
│
├── data/                     # (Optionnel) Données partagées ou exports globaux
│   ├── input/                # Sources brutes globales
│   └── output/               # Exports globaux (CSV, Excel)
│
├── README.md                 # Documentation du projet
│
├── .gitignore                # Fichiers/dossiers à ignorer par git
│
├── CORRECTION_COLONNES_DUPLICATAS.md   # Notes de correction sur les colonnes dupliquées
├── CORRECTION_FORMAT_DECIMAL.md        # Notes sur le format des décimales
├── NOTES_RECOMMANDATION_CLASSIFICATION.md  # Documentation complète des colonnes de recommandation
├── NOTE_DF_MERGE.md                    # Documentation du cycle de vie du DataFrame df_merge

├── NATIONAL MOS.xlsx                   # Fichier Excel de référence nationale
├── Suivi MOS_2025 03 TEST.xlsx         # Fichier Excel de suivi

# D'autres fichiers peuvent inclure :
# - Documentation technique ou fonctionnelle
# - Scripts d'import/export de données
# - Fichiers de configuration supplémentaires
# - Notes de correction ou d'évolution
```

## Documentation technique détaillée

Le projet dispose d'une documentation technique approfondie couvrant tous les aspects du traitement des données :

### 📊 [NOTES_RECOMMANDATION_CLASSIFICATION.md](./NOTES_RECOMMANDATION_CLASSIFICATION.md)
Documentation complète du pipeline des colonnes de recommandation Manpower :
- **Cycle de vie complet** : de la source Excel jusqu'à l'export final
- **Analyse de sentiment** : TextBlob et CamemBERT avec échelles détaillées
- **Nettoyage et transformation** : renommage, déduplication, validation
- **Utilisation dans la segmentation** : impact sur la classification des agences
- **Références précises** : tous les fichiers et numéros de lignes concernés

### 🔄 [NOTE_DF_MERGE.md](./NOTE_DF_MERGE.md)
Documentation détaillée du DataFrame central de fusion :
- **Construction initiale** : fusion LEFT JOIN entre performance et interview
- **Processus de nettoyage** : gestion des colonnes dupliquées et vides
- **Renommage systématique** : application du RENAME_MAP avec fallbacks
- **Transformation en df_main** : sélection, validation et export
- **Points critiques** : gestion des cas edge et recommandations maintenance

Ces documentations techniques facilitent la maintenance, le debugging et l'évolution future du système.

### Explications clés
- **backend/src/api/** : Toutes les routes API, contrôleurs, modèles de données (SQLAlchemy).
- **backend/src/modules/ai/** : Scripts d'IA utilisés :
    - `sentiment.py` : analyse de sentiment rapide (TextBlob)
    - `sentiment_camembert.py` : analyse de sentiment avancée (BERT multilingue)
    - `siret_cleaner.py` : nettoyage des SIRET
- **backend/data/output/df_main.csv** : DataFrame principal enrichi, utilisé pour l'analyse et l'export.
- **frontend/src/app/pages/** : Pages Streamlit pour l'interface utilisateur.
- **venv/** : Chaque partie a son propre environnement virtuel pour isoler les dépendances.
- **requirements.txt** : Liste exhaustive des packages nécessaires à chaque partie (backend et frontend).
- **README.md** : Toutes les instructions, démarche, et logique métier du projet.
- **CORRECTION_COLONNES_DUPLICATAS.md, CORRECTION_FORMAT_DECIMAL.md** : Documentation sur les corrections de données.
- **ULTIMATE PROMPT ANALYTICS MOS.txt** : Prompt de référence pour l'analyse de sentiment et la segmentation.
- **NATIONAL MOS.xlsx, Suivi MOS_2025 03 TEST.xlsx** : Fichiers Excel de référence et de suivi.

## Installation

### Prérequis
- Python 3.10+ recommandé
- pip

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # (Windows) ou source venv/bin/activate (Linux/Mac)
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
python -m venv venv
venv\Scripts\activate  # (Windows) ou source venv/bin/activate (Linux/Mac)
pip install -r requirements.txt
```

## Lancement

### Backend (API Flask)
```bash
cd backend
venv\Scripts\python.exe main.py
```

### Frontend (Streamlit)
```bash
cd frontend
venv\Scripts\streamlit run main.py
```

## Exemple d'utilisation
1. **Upload** : Importez les fichiers Excel de performance et d'interview via l'interface Streamlit.
2. **Nettoyage & Fusion** : Le backend traite, fusionne et enrichit les données (sentiment, croissance, etc.).
3. **Visualisation** : Explorez les DataFrames, filtrez, consultez les segments d'agence.
4. **Export** : Téléchargez les résultats en CSV ou Excel, incluant la colonne `segment_agence`.

## Modèles IA appliqués

Le projet utilise deux modèles d'intelligence artificielle pour l'analyse automatique du **sentiment** dans les réponses textuelles des clients :

1. **TextBlob (PatternAnalyzer)**
   - Utilisé pour une analyse rapide et légère du sentiment sur des textes courts ou pour des besoins de prétraitement.
   - Fonctionne en français et en anglais, mais avec une précision limitée sur le français.
   - Appliqué sur certaines colonnes d'interview pour obtenir un label de sentiment (very_negative, negative, neutral, positive, very_positive) et un score associé.

2. **nlptown/bert-base-multilingual-uncased-sentiment** (modèle BERT multilingue, utilisé via la classe `CamemBERTSentimentAnalyzer`)
   - Modèle avancé basé sur BERT, optimisé pour le français et d'autres langues.
   - Utilisé pour l'analyse de sentiment approfondie sur les justifications textuelles longues (ex : "Raison recommandation Manpower").
   - Produit un label de sentiment (TRÈS NÉGATIF, NÉGATIF, NEUTRE, POSITIF, TRÈS POSITIF) et un score sur 10, avec prise en compte du contexte métier.
   - Intégré dans le pipeline principal pour enrichir le DataFrame principal et les exports.

**Usage dans le pipeline :**
- Les deux modèles sont utilisés à différents moments du traitement pour garantir robustesse et précision.
- Les résultats de l'analyse de sentiment sont ajoutés comme colonnes dédiées dans le DataFrame principal, visibles dans l'interface Streamlit et dans les exports CSV/Excel.

Aucun autre modèle IA n'est utilisé dans ce projet pour l'analyse ou la segmentation.

## Objectifs de l'analyse

- **Segmenter les agences** selon leur performance, la satisfaction client et la dynamique de croissance
- Identifier les points forts et axes d'amélioration pour chaque agence
- Fournir des exports et des visualisations claires pour le pilotage opérationnel
- Automatiser le scoring et la catégorisation des retours clients

## Démarche générale

1. **Collecte et fusion des données** : Import des fichiers de performance et d'interview, nettoyage, harmonisation des colonnes, gestion des doublons.
2. **Enrichissement** : Application des modèles IA pour le sentiment, calcul de scores, création de variables de croissance.
3. **Calcul des segments** : Attribution d'un segment à chaque agence selon des règles métiers (voir ci-dessous).
4. **Visualisation et export** : Interface Streamlit pour explorer les données, filtrer, et exporter en CSV/Excel.

## Logique de calcul des segments (`segment_agence`)

Chaque agence est classée dans un segment selon :
- **Croissance** : Toutes les variables de croissance doivent être positives ou non négatives
- **Score moyen** : Calculé sur les notes de recommandation et les questions Q5 à Q21
- **Sentiment** : Catégorie de sentiment extraite automatiquement

**Règles d'attribution :**
- `Top Performer` : Croissance strictement positive, score moyen ≥ 9, sentiment POSITIF
- `High Performer` : Croissance non négative, score moyen ≥ 7, sentiment POSITIF ou NEUTRE
- `Stable / Surveillé` : Score moyen ≥ 5, au plus 1 variable de croissance négative
- `À améliorer` : Sinon

Ces segments permettent de prioriser les actions et d'orienter les recommandations pour chaque agence.

## Base de données
- Une base SQLite locale (`backend/instance/dev_db.sqlite3`) peut être utilisée pour stocker des informations intermédiaires ou des historiques de traitements.
- Le fichier principal de travail reste le CSV `backend/data/output/df_main.csv`.

## Conseils pour la contribution et maintenance

### Développement
- Forkez le dépôt, créez une branche pour vos modifications.
- Respectez la structure des dossiers et l'organisation du code.
- Ajoutez des tests ou des exemples si vous proposez de nouvelles fonctionnalités.
- Documentez vos changements dans le README ou via des commentaires.

### Maintenance et debugging
- **Consultez la documentation technique** : `NOTES_RECOMMANDATION_CLASSIFICATION.md` et `NOTE_DF_MERGE.md` contiennent toutes les références précises pour comprendre et modifier le code.
- **Surveillez les logs** : Le système produit des logs détaillés avec marqueurs `[LOG-ALIGN]` pour tracer les transformations.
- **Testez avec différents fichiers Excel** : Le système de renommage automatique doit être robuste face aux variations de format.
- **Vérifiez les analyses de sentiment** : Les modèles IA peuvent nécessiter un ajustement selon l'évolution du vocabulaire métier.

### Évolutions recommandées
- **Performance** : Considérer la parallélisation pour les gros volumes de données
- **Modèles IA** : Évaluer des modèles plus récents ou spécialisés pour l'analyse de sentiment RH
- **Interface** : Ajouter des tableaux de bord interactifs pour le monitoring en temps réel

## Contacts & Liens utiles
- Pour toute question, ouvrez une issue sur le dépôt ou contactez l'équipe projet.
- **Documentation technique** : Consultez `NOTES_RECOMMANDATION_CLASSIFICATION.md` et `NOTE_DF_MERGE.md` pour les détails techniques
- Documentation Streamlit : https://docs.streamlit.io/
- Documentation Flask : https://flask.palletsprojects.com/
- Documentation pandas : https://pandas.pydata.org/
- Modèle CamemBERT : https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment

---

*README mis à jour le 10 juillet 2025 - Version 2.1*  
*Inclut la documentation technique complète des pipelines de données*

Pour toute question ou contribution, consultez d'abord la documentation technique détaillée, puis contactez l'équipe projet ou ouvrez une issue sur le dépôt. 
