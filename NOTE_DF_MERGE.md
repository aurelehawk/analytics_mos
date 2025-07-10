# NOTE DF_MERGE - Cycle de vie complet du DataFrame de fusion

## 📋 Vue d'ensemble

`df_merge` est le DataFrame central du système Analytics MOS qui résulte de la fusion entre les données de performance (`df_performance`) et les données d'entretien (`df_interview`). Cette documentation trace le cycle de vie complet de `df_merge` depuis sa création jusqu'à sa transformation en `df_main` pour l'export final.

## 🏗️ Construction initiale de df_merge

### 1. Fusion des DataFrames sources
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 506-513

```python
df_merge = pd.merge(
    df_performance,
    df_interview,
    on='siret_agence',
    how='left',
    suffixes=('', '_interview')
)
```

**Logique**:
- **Type de fusion**: `LEFT JOIN` sur la clé `siret_agence`
- **DataFrames sources**: 
  - `df_performance` (données business/performance)
  - `df_interview` (données questionnaire satisfaction)
- **Suffixes**: Les colonnes en conflit gardent leur nom original dans `df_performance`, les colonnes de `df_interview` reçoivent le suffixe `_interview`
- **Résultat**: Toutes les lignes de `df_performance` sont conservées, avec les données d'entretien ajoutées quand disponibles

### 2. Filtrage temporel critique
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 577-579

```python
df_merge = df_merge[df_merge["Campagne d'appels"] == (df_merge['Année'] - 1)]
```

**Logique**: Ne conserver que les lignes où la campagne d'appels correspond à l'année précédente (cohérence temporelle business).

## 🧹 Processus de nettoyage des colonnes

### 1. Suppression des colonnes duplicatas vides
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 516-542

**Logique**:
```python
for col in df_merge.columns:
    if col.endswith('.1') or col.endswith('.2') or col.endswith('.3'):
        if df_merge[col].isna().all():
            columns_to_drop.append(col)
```

**Critères de suppression**:
- Colonnes avec suffixes numériques (`.1`, `.2`, `.3`)
- Entièrement vides (valeurs NaN ou None uniquement)
- Colonnes sans données utiles après vérification

### 2. Nettoyage spécifique des colonnes de sentiment
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 548-565

**Actions**:
1. **Gestion de 'Raison recommandation Manpower.1'**:
   - Si vide → suppression
   - Si contient des données → renommage en 'Sentiment Raison de recommandation Manpower'

2. **Ajout des colonnes de sentiment manquantes**:
   ```python
   if 'Sentiment Raison de recommandation Manpower' not in df_merge.columns:
       df_merge['Sentiment Raison de recommandation Manpower'] = None
   
   if 'Score Raison de recommandation Manpower' not in df_merge.columns:
       df_merge['Score Raison de recommandation Manpower'] = None
   ```

## 🔄 Processus de renommage des colonnes

### 1. Application du mapping RENAME_MAP
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 583-626

**Méthode de renommage**:
1. **Correspondance exacte** d'abord
2. **Correspondance partielle** si échec
3. **Recherche spéciale pour les colonnes Q** (ex: Q11, Q12, etc.)

**Exemples de transformations**:
- `'Q11 - Diriez-vous que l'adéquation...'` → `'Q11 - Qualité adéquation candidats'`
- `'Q12 - Réactivité pour répondre à vos besoins'` → `'Q12 - Réactivité'`
- Colonnes longues avec formulations complètes → noms courts standardisés

### 2. Validation des renommages
**Contrôles qualité**:
- Vérification de la présence des colonnes après renommage
- Logs détaillés des renommages réussis/échoués
- Attention spéciale aux colonnes critiques (Q11, Q12, etc.)

## 🎯 Gestion spéciale de la colonne "Concurrent OnSite"

### 1. Positionnement stratégique
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 645-695

**Objectif**: Garantir que "Concurrent OnSite" soit positionnée juste après "No Siret" dans l'ordre des colonnes.

**Processus**:
1. Détection de la colonne concurrent (nom exact ou variantes)
2. Création d'un merge spécifique pour le positionnement
3. Réorganisation des colonnes avec insertion à la position correcte

## 📊 Construction du DataFrame final (df_main)

### 1. Sélection des colonnes finales
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 722-780

**Constitution de FINAL_COLS**:
```python
FINAL_COLS = PERFORMANCE_COLS + actual_interview_cols
```

**Colonnes interview dynamiques**:
- Détection automatique des colonnes présentes après renommage
- Exclusion des anciens noms non renommés
- Ajout des colonnes de sentiment créées

### 2. Validation stricte des colonnes
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 800-830

**Contrôles spéciaux**:
- **Validation Q12**: Vérification que les valeurs sont des notes numériques ou "Pas de réponse"
- **Vérification de présence**: Chaque colonne doit exister dans `df_merge`
- **Construction de final_cols_checked**: Liste finale validée

### 3. Construction robuste de df_main
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 830-835

```python
df_main = df_merge[final_cols_checked]
```

## 🔧 Patches et récupérations de données

### 1. Patch Q12 - Récupération depuis df_interview
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 836-854

**Objectif**: Récupérer Q12 directement depuis `df_interview` via mapping `siret_agence` si problème dans la fusion.

### 2. Patch DR - Récupération depuis df_performance
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 855-867

**Objectif**: Récupérer la colonne DR directement depuis `df_performance` via mapping `siret_agence`.

## 🤖 Traitement d'analyse de sentiment

### Application de CamemBERT
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 902-905

```python
df_main = apply_camembert_sentiment_analysis(df_main)
```

**Colonnes traitées**:
- `'Raison recommandation Manpower'` → génère sentiment et score
- Autres colonnes textuelles configurées pour l'analyse

## 💾 Export et sauvegarde

### 1. Export CSV
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 907-909

```python
df_main.to_csv(output_path, index=False, encoding='utf-8-sig', decimal=',', sep=';')
```

**Format**: CSV français (virgule comme séparateur décimal, point-virgule comme séparateur de champ)

### 2. Sauvegarde en base SQLite
**Localisation**: `backend/src/api/controllers/data_controller.py` - Lignes 920-1035

**Processus**:
1. Suppression des anciennes données
2. Fonction `safe_get()` pour gérer les valeurs Series/scalaires
3. Mapping vers le modèle `MainData` SQLAlchemy
4. Insertion en base avec gestion d'erreurs

## 🔍 Points critiques et transformations clés

### 1. Gestion des colonnes dupliquées
- **Problème**: Fusion peut créer des colonnes avec suffixes (.1, .2)
- **Solution**: Détection et suppression automatique des colonnes vides
- **Validation**: Vérification du contenu avant suppression

### 2. Mapping de colonnes dynamique
- **Défi**: Noms de colonnes variables entre les fichiers Excel
- **Approche**: Système de mapping flexible avec fallbacks
- **Robustesse**: Recherche par pattern si correspondance exacte échoue

### 3. Cohérence temporelle
- **Règle business**: Campagne d'appels = Année - 1
- **Impact**: Filtrage strict pour garantir la cohérence des données
- **Validation**: Logs de contrôle avant/après filtrage

### 4. Ordre des colonnes
- **Requirement**: "Concurrent OnSite" doit être après "No Siret"
- **Implémentation**: Réorganisation forcée dans `FINAL_COLS` et `df_merge`
- **Validation**: Vérification des positions après réorganisation

## 📈 Métriques et monitoring

### Logs de contrôle qualité
**Points de contrôle**:
- Shape du DataFrame à chaque étape
- Nombre de colonnes renommées
- Colonnes manquantes vs présentes
- Exemples de données après transformations

### Validation des données critiques
**Colonnes surveillées**:
- Q11, Q12 : Validation du format des réponses
- Colonnes de sentiment : Vérification de la présence
- siret_agence : Clé de fusion critique

## 🚀 Recommandations pour la maintenance

### 1. Monitoring des renommages
- Surveiller les logs de renommage pour détecter les échecs
- Mettre à jour `RENAME_MAP` si nouveaux formats de colonnes
- Tester la robustesse avec différents fichiers Excel

### 2. Validation des fusions
- Vérifier le taux de match sur `siret_agence`
- Contrôler la cohérence temporelle des données
- Surveiller les colonnes dupliquées/orphelines

### 3. Optimisation des performances
- Considérer l'indexation sur `siret_agence` pour les gros volumes
- Optimiser les opérations de nettoyage pour les DataFrames volumineux
- Évaluer la parallélisation des analyses de sentiment

## 📚 Références techniques

### Fichiers impliqués
- **Principal**: `backend/src/api/controllers/data_controller.py` (lignes 506-1058)
- **Configuration**: `RENAME_MAP` (début du fichier)
- **Modèle**: `backend/src/api/models/data_models.py` (classe MainData)
- **Sentiment**: `backend/src/modules/ai/sentiment_camembert.py`

### Points d'entrée API
- **Endpoint**: `/api/data/import_and_process` 
- **Fichier**: `backend/src/api/routes/data.py`
- **Méthode**: POST avec upload de fichiers Excel

### Artefacts produits
- **CSV final**: `data/output/df_main.csv`
- **Base SQLite**: `backend/instance/dev_db.sqlite3` (table main_data)
- **Logs**: Sortie console avec marqueurs `[LOG-ALIGN]` et debug

---

*Documentation générée le 7 janvier 2025 - Version 1.0*
*Auteur: Analyse automatique du cycle de vie df_merge*
