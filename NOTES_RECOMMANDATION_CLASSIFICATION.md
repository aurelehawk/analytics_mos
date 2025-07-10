# ANALYSE APPROFONDIE - COLONNES DE RECOMMANDATION MANPOWER

## Vue d'ensemble

Cette analyse approfondie examine les colonnes liées à la recommandation Manpower dans le système Analytics MOS, de leur source jusqu'à leur utilisation dans la segmentation des agences.

### Colonnes analysées
- **`Raison recommandation Manpower`** : Texte de justification de la note de recommandation
- **`Sentiment Raison de recommandation Manpower`** : Label de sentiment analysé automatiquement
- **`Score Raison de recommandation Manpower`** : Score numérique de sentiment (0-10)

## 1. SOURCE DES DONNÉES

### 1.1 Fichier d'interview (questionnaire client)
**Localisation** : Fichier Excel d'interview chargé via l'interface Streamlit

**Colonne source** : Plusieurs variantes possibles selon le format du fichier :
```
- "Pouvez-vous me dire pourquoi vous donner cette note de recommandation?"
- "Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?"
- "Pouvez-vous me dire pourquoi vous donner cette note de recommandation?  "
- "Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?  "
```

**Traitement de la source** :
- Nettoyage de l'encodage des noms de colonnes (correction UTF-8)
- Renommage automatique vers `Raison recommandation Manpower`
- Gestion des valeurs vides → remplacement par "Pas de réponse"

### 1.2 Configuration du mapping
**Fichier** : `backend/src/api/controllers/data_controller.py`

**RENAME_MAP** (lignes 202-210) :
```python
RENAME_MAP = {
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation?': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation?  ': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?  ': 'Raison recommandation Manpower',
}
```

**Localisation exacte** : `backend/src/api/controllers/data_controller.py` lignes 202-210

## 2. NETTOYAGE ET TRANSFORMATION

### 2.1 Processus de renommage
**Fichier** : `backend/src/api/controllers/data_controller.py`
**Fonction** : `process_excel_files()` lignes 574-600

**Algorithme** (lignes 574-600) :
1. Recherche exacte du nom de colonne dans RENAME_MAP
2. Si non trouvé, recherche par correspondance partielle (case insensitive)
3. Application du renommage avec logging détaillé
4. Évitement des doublons via un set `processed_columns`

**Code de référence** : lignes 574-600 dans `data_controller.py`

### 2.2 Gestion des colonnes dupliquées
**Problème identifié** : Colonnes `Raison recommandation Manpower.1` créées lors de doublons

**Solution** (`backend/src/api/controllers/data_controller.py` lignes 548-556) :
```python
if 'Raison recommandation Manpower.1' in df_merge.columns:
    if df_merge['Raison recommandation Manpower.1'].isna().all():
        df_merge = df_merge.drop(columns=['Raison recommandation Manpower.1'])
    else:
        df_merge = df_merge.rename(columns={
            'Raison recommandation Manpower.1': 'Sentiment Raison de recommandation Manpower'
        })
```

**Fichier de référence** : `backend/src/api/controllers/data_controller.py` lignes 548-556

### 2.3 Initialisation des colonnes de sentiment
**Colonnes créées automatiquement** (`backend/src/api/controllers/data_controller.py` lignes 558-564) :
```python
if 'Sentiment Raison de recommandation Manpower' not in df_merge.columns:
    df_merge['Sentiment Raison de recommandation Manpower'] = None
    
if 'Score Raison de recommandation Manpower' not in df_merge.columns:
    df_merge['Score Raison de recommandation Manpower'] = None
```

**Fichier de référence** : `backend/src/api/controllers/data_controller.py` lignes 558-564

## 3. ANALYSE DE SENTIMENT

### 3.1 Modèles d'IA utilisés

#### A. TextBlob (sentiment.py) - Analyse rapide
**Fichier** : `backend/src/modules/ai/sentiment.py` lignes 3-15
**Usage** : Analyse basique pour préprocessing ou fallback

**Fonction principale** (`sentiment.py` lignes 3-15) :
```python
def analyze_sentiment(text):
    if not text or str(text).strip() == '':
        return 'Pas de réponse', 5
    blob = TextBlob(str(text))
    polarity = blob.sentiment.polarity  # [-1, 1]
    score = int(round((polarity + 1) * 5))  # Mapping sur [0, 10]
```

#### B. CamemBERT (sentiment_camembert.py) - Analyse avancée
**Fichier** : `backend/src/modules/ai/sentiment_camembert.py` lignes 17-280
**Modèle** : `nlptown/bert-base-multilingual-uncased-sentiment`

**Caractéristiques** :
- Spécialisé pour les commentaires clients RH
- Optimisé pour les textes longs français
- Gestion robuste des types de données (arrays, Series, etc.)

**Classe principale** : `CamemBERTSentimentAnalyzer` lignes 17-280
**Factory function** : `get_sentiment_analyzer()` lignes 315-320
**Interface API** : `analyze_sentiment_camembert()` lignes 322-328

### 3.2 Échelle de sentiment (selon ULTIMATE PROMPT)
**Définition** : `backend/src/modules/ai/sentiment_camembert.py` lignes 29-35
```python
sentiment_scale = {
    'very_negative': (0, 2, 'Opinion extrêmement défavorable'),
    'negative': (2, 5, 'Opinion défavorable'),
    'neutral': (5, 7, 'Opinion mitigée ou indifférente'),
    'positive': (7, 8, 'Opinion favorable'),
    'very_positive': (8, 10, 'Opinion très favorable / enthousiaste')
}
```

**Labels de sortie** (mapping lignes 244-251) :
- TRÈS NÉGATIF
- NÉGATIF
- NEUTRE
- POSITIF
- TRÈS POSITIF

### 3.3 Processus d'analyse CamemBERT

#### A. Fonction principale
**Fichier** : `backend/src/api/controllers/data_controller.py`
**Fonction** : `apply_camembert_sentiment_analysis()` lignes 11-89

**Initialisation** : lignes 24-31 (import dynamique et factory)
**Filtrage des textes** : lignes 47-53
**Analyse par batch** : lignes 66-71
**Application résultats** : lignes 77-78

#### B. Pipeline d'analyse
**Étapes détaillées** dans `data_controller.py` :
1. **Initialisation** du modèle CamemBERT (lignes 24-31 - factory pattern)
2. **Filtrage** des textes valides (lignes 47-53 - ≠ '', ≠ 'Pas de réponse')
3. **Analyse par batch** (lignes 66-71 - taille 10) pour éviter les timeouts
4. **Callback de progression** (lignes 64-65) avec logging détaillé
5. **Application des résultats** (lignes 77-78) au DataFrame

#### C. Préprocessing avancé
**Fonction** : `preprocess_text()` dans `sentiment_camembert.py` lignes 68-128

**Gestion robuste des types** (lignes 71-92) :
```python
# Gérer les cas None
if text is None:
    return ""

# Gérer les listes/tuples
if isinstance(text, (list, tuple)):
    if len(text) > 0:
        text = str(text[0])
    else:
        return ""

# Gérer les types pandas/numpy
elif hasattr(text, 'iloc') or hasattr(text, '__array__'):
    # Logique spécialisée pour Series et arrays
```

**Optimisations pour textes longs** (lignes 108-128) :
- Extraction des phrases clés (début, fin, mots émotionnels)
- Limitation à 512 tokens max (BERT constraint)
- Nettoyage de la ponctuation et espaces

#### D. Analyse contextuelle
**Fonction** : `analyze_with_context()` dans `sentiment_camembert.py` lignes 130-174

**Améliorations** (lignes 133-168) :
- Mapping des labels nlptown (1-5 stars) vers échelle 0-10 (lignes 138-145)
- Boost contextuel via mots-clés métier (lignes 150-168)
- Détection de connecteurs de contraste ('mais', 'cependant') (lignes 153-155)
- Neutralisation si polarité mixte détectée (lignes 158-161)

### 3.4 Logging et monitoring
**Localisation** : `backend/src/api/controllers/data_controller.py` lignes 79-87

**Statistiques générées** :
- Nombre de textes analysés vs total (ligne 55)
- Distribution des sentiments (counts par label) (lignes 80-83)
- Scores moyens, min, max (lignes 85-86)
- Progression en temps réel (batchs de 10) (callback lignes 64-65)

## 4. STOCKAGE ET PERSISTANCE

### 4.1 DataFrame principal (df_main.csv)
**Localisation** : `data/output/df_main.csv`
**Format** : CSV français (`;` séparateur, `,` décimal)
**Encodage** : UTF-8 with BOM

### 4.2 Base de données SQLite
**Fichier** : `backend/instance/dev_db.sqlite3`
**Modèle** : `MainData` dans `backend/src/api/models/data_models.py`

**Colonnes correspondantes** (`data_models.py` lignes 70-74) :
```python
class MainData(db.Model):
    # ...
    raison_recommandation_manpower = Column('Raison recommandation Manpower', String)
    sentiment_raison_de_recommandation_manpower = Column('Sentiment Raison de recommandation Manpower', String)
    score_raison_de_recommandation_manpower = Column('Score Raison de recommandation Manpower', Integer)
```

**Fonction d'insertion** : `safe_get()` dans `data_controller.py` lignes 931-947
- Gestion des valeurs Series/scalaires
- Gestion des numpy arrays
- Valeurs par défaut pour NaN/None

## 5. UTILISATION DANS LA SEGMENTATION

### 5.1 Calcul du segment d'agence
**Fichier** : `backend/src/api/routes/data.py`
**Fonction** : `get_main_data()` (lignes 105-123)

### 5.2 Variables de segmentation
**Fichier** : `backend/src/api/routes/data.py` lignes 101-103
```python
sentiment_col = 'Sentiment Raison de recommandation Manpower'
df['sentiment_cat'] = df[sentiment_col].str.upper().fillna('NEUTRE')
```

### 5.3 Logique de classification
**Fonction** : `seg(row)` dans `backend/src/api/routes/data.py` lignes 105-116

```python
def seg(row):
    try:
        if row.grow_pos_all and row.score_moy >=9 and row.sentiment_cat=='POSITIF':
            return 'Top Performer'
        if row.grow_nonneg_all and row.score_moy >=7 and row.sentiment_cat in ['POSITIF','NEUTRE']:
            return 'High Performer'
        if row.score_moy >=5 and row.grow_any_neg<=1:
            return 'Stable / Surveillé'
        return 'À améliorer'
    except Exception:
        return 'À améliorer'
```

**Impact du sentiment** :
- **Top Performer** : Exige sentiment `POSITIF` (ligne 107)
- **High Performer** : Accepte `POSITIF` ou `NEUTRE` (ligne 109)
- **Autres segments** : Pas de contrainte de sentiment

## 6. API ET INTERFACES

### 6.1 Endpoints REST
**Fichier** : `backend/src/api/routes/data.py`

#### A. Traitement principal
**Fichiers et lignes** :
- **POST** `/process_excels` : `data.py` lignes 20-78 (Analyse complète avec sentiment)
- **GET** `/main_data` : `data.py` lignes 80-133 (Récupération avec calcul de segment)

#### B. Aperçus
**Fichiers et lignes** :
- **POST** `/preview_performance` : `data.py` lignes 135-179 (Aperçu fichier performance)
- **POST** `/preview_interview` : `data.py` lignes 181-265 (Aperçu fichier interview inclut sentiment)

### 6.2 Interface utilisateur (Streamlit)
**Fichier** : `frontend/main.py`

**Affichage des métriques** (lignes 356-357) :
```python
df.get('Raison recommandation Manpower', pd.Series()).notna().sum() if 'Raison recommandation Manpower' in df.columns else 0,
df.get('Note Recommandation Manpower', pd.Series()).notna().sum() if 'Note Recommandation Manpower' in df.columns else 0,
```

**Colonnes de recommandation affichées** (ligne 372) :
```python
['Note Recommandation Manpower', 'Raison recommandation Manpower']
```

**Localisation exacte** : `frontend/main.py` lignes 356-357 et 372

## 7. FORMATS D'EXPORT

### 7.1 CSV français
- Séparateur : `;` (point-virgule)
- Décimal : `,` (virgule)
- Encodage : UTF-8 with BOM
- Headers : Noms de colonnes originaux

### 7.2 JSON API
- Conversion automatique en string pour compatibilité
- Gestion des types complexes (numpy, pandas)

## 8. GESTION D'ERREURS ET ROBUSTESSE

### 8.1 Gestion des cas edge
- Textes vides ou None
- Arrays/Series au lieu de strings
- Caractères d'encodage corrompus
- Timeouts d'analyse IA

### 8.2 Fallbacks
- TextBlob si CamemBERT échoue
- Valeurs par défaut (NEUTRE, 5.0)
- Logging détaillé des erreurs

### 8.3 Validation des données
- Vérification de présence des colonnes
- Contrôle de cohérence des types
- Statistiques de validation post-traitement

## 9. OPTIMISATIONS PERFORMANCES

### 9.1 Analyse par batch
**Localisation** : `backend/src/modules/ai/sentiment_camembert.py` lignes 260-286
- Taille : 10 textes par batch (ligne 66 dans `data_controller.py`)
- Callback de progression (lignes 275-277)
- Gestion mémoire optimisée

### 9.2 Cache et réutilisation
**Fichiers de référence** :
- Instance globale d'analyseur (`_analyzer_instance`) : `sentiment_camembert.py` ligne 313
- Factory pattern : `get_sentiment_analyzer()` lignes 315-320
- Préprocessing optimisé : `preprocess_text()` lignes 68-128

### 9.3 Timeout management
**Localisation** : `sentiment_camembert.py` lignes 108-128 et `data.py` lignes 55-70
- Limitation des textes très longs
- Extraction de phrases clés
- Gestion des timeouts via signal handlers (`data.py` lignes 55-70)

## 10. ÉVOLUTIONS ET AMÉLIORATIONS POSSIBLES

### 10.1 Modèles d'IA
- Migration vers CamemBERT français natif
- Fine-tuning sur corpus métier RH
- Modèles spécialisés satisfaction client

### 10.2 Performance
- Cache Redis pour résultats d'analyse
- Parallélisation GPU (CUDA)
- API asynchrone pour traitement long

### 10.3 Fonctionnalités
- Analyse de sujets (topic modeling)
- Détection d'entités nommées
- Analyse comparative temporelle

## RÉFÉRENCES COMPLÈTES DES FICHIERS ET LIGNES

### Fichiers principaux analysés

#### 1. `backend/src/api/controllers/data_controller.py` (1058 lignes)
- **Lignes 11-89** : `apply_camembert_sentiment_analysis()` - Fonction principale d'analyse de sentiment
- **Lignes 24-31** : Initialisation dynamique du modèle CamemBERT
- **Lignes 47-53** : Filtrage des textes valides pour l'analyse
- **Lignes 64-65** : Callback de progression pour monitoring
- **Lignes 66-71** : Analyse par batch (taille 10)
- **Lignes 77-78** : Application des résultats au DataFrame
- **Lignes 79-87** : Logging des statistiques d'analyse
- **Lignes 202-210** : `RENAME_MAP` - Configuration du mapping des colonnes
- **Lignes 548-556** : Gestion des colonnes dupliquées `Raison recommandation Manpower.1`
- **Lignes 558-564** : Initialisation automatique des colonnes de sentiment
- **Lignes 574-600** : Processus de renommage dans `process_excel_files()`
- **Lignes 931-947** : Fonction `safe_get()` pour insertion en base
- **Lignes 997-998** : Mapping vers colonnes de la base SQLite

#### 2. `backend/src/modules/ai/sentiment_camembert.py` (328 lignes)
- **Lignes 17-280** : Classe `CamemBERTSentimentAnalyzer`
- **Lignes 29-35** : Définition de l'échelle de sentiment
- **Lignes 37-44** : Mots-clés contextuels pour ajustement
- **Lignes 46-66** : `setup_model()` - Initialisation du modèle BERT
- **Lignes 68-128** : `preprocess_text()` - Préprocessing avancé
- **Lignes 71-92** : Gestion robuste des types de données
- **Lignes 108-128** : Optimisations pour textes longs
- **Lignes 130-174** : `analyze_with_context()` - Analyse contextuelle
- **Lignes 138-145** : Mapping labels nlptown vers échelle 0-10
- **Lignes 150-168** : Boost contextuel via mots-clés
- **Lignes 153-155** : Détection connecteurs de contraste
- **Lignes 176-259** : `analyze_sentiment_advanced()` - Méthode principale
- **Lignes 244-251** : Mapping vers labels finaux
- **Lignes 260-286** : `batch_analyze()` - Analyse par batch
- **Lignes 313** : Instance globale `_analyzer_instance`
- **Lignes 315-320** : Factory `get_sentiment_analyzer()`
- **Lignes 322-328** : Interface API `analyze_sentiment_camembert()`

#### 3. `backend/src/modules/ai/sentiment.py` (15 lignes)
- **Lignes 3-15** : Fonction `analyze_sentiment()` - Analyse TextBlob (fallback)

#### 4. `backend/src/api/routes/data.py` (312 lignes)
- **Lignes 20-78** : Route POST `/process_excels` - Traitement principal
- **Lignes 55-70** : Gestion des timeouts
- **Lignes 80-133** : Route GET `/main_data` - Récupération avec segmentation
- **Lignes 101-103** : Variables de segmentation du sentiment
- **Lignes 105-116** : Fonction `seg(row)` - Logique de classification
- **Lignes 107** : Contrainte sentiment POSITIF pour Top Performer
- **Lignes 109** : Contrainte sentiment POSITIF/NEUTRE pour High Performer
- **Lignes 135-179** : Route POST `/preview_performance`
- **Lignes 181-265** : Route POST `/preview_interview`

#### 5. `backend/src/api/models/data_models.py` (83 lignes)
- **Lignes 70-74** : Colonnes de recommandation dans modèle `MainData`
- **Ligne 70** : `raison_recommandation_manpower`
- **Ligne 73** : `sentiment_raison_de_recommandation_manpower`
- **Ligne 74** : `score_raison_de_recommandation_manpower`

#### 6. `frontend/main.py` (lignes estimées 400+)
- **Lignes 356-357** : Affichage métriques de recommandation
- **Ligne 372** : Colonnes de recommandation dans l'interface

### Fichiers de données
- **`data/output/df_main.csv`** : DataFrame principal avec sentiment analysé
- **`backend/instance/dev_db.sqlite3`** : Base SQLite avec colonnes de recommandation

### Fichiers de configuration
- **`ULTIMATE PROMPT ANALYTICS MOS.txt`** : Spécifications métier originales
- **`requirements.txt`** : Dépendances (transformers, torch, textblob)

### Localisation des résultats
- **CSV français** : Format `;` séparateur, `,` décimal, UTF-8 BOM
- **API JSON** : Conversion automatique en string pour compatibilité
- **Base SQLite** : Stockage persistant avec gestion des types complexes

## CONCLUSION

Les colonnes de recommandation Manpower constituent un élément central du système Analytics MOS, avec un pipeline complet de traitement depuis la source jusqu'à la segmentation. Le système implémente une analyse de sentiment avancée robuste avec CamemBERT, gère efficacement les cas edge, et intègre les résultats dans une logique métier de classification des agences.

L'architecture modulaire permet une évolution facile vers des modèles plus avancés tout en maintenant la compatibilité avec l'existant.
