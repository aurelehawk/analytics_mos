import pandas as pd
from src.modules.ai.siret_cleaner import clean_siret
from src.modules.ai.sentiment import analyze_sentiment
# sentiment_camembert import will be done dynamically in the function
from src.core.db import db
from src.api.models.data_models import MainData
from sqlalchemy.exc import SQLAlchemyError
import logging
import numpy as np  # Pour gérer les numpy arrays

def apply_camembert_sentiment_analysis(df_main):
    """
    Applique l'analyse de sentiment CamemBERT sur la colonne 'Raison recommandation Manpower'
    et remplit les colonnes 'Sentiment Raison de recommandation Manpower' et 'Score Raison de recommandation Manpower'
    """
    try:
        # Import avec gestion des chemins
        import sys
        import os
        
        # Ajouter le répertoire src au PYTHONPATH 
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Remonter à backend/src depuis backend/src/api/controllers
        src_path = os.path.dirname(os.path.dirname(current_dir))
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            
        from modules.ai.sentiment_camembert import get_sentiment_analyzer
        
        print("🤖 Initialisation de l'analyseur CamemBERT...")
        analyzer = get_sentiment_analyzer()
        
        # Vérifier que les colonnes existent
        if 'Raison recommandation Manpower' not in df_main.columns:
            print("⚠️ Colonne 'Raison recommandation Manpower' non trouvée")
            return df_main
            
        if 'Sentiment Raison de recommandation Manpower' not in df_main.columns:
            df_main['Sentiment Raison de recommandation Manpower'] = None
            print("➕ Colonne 'Sentiment Raison de recommandation Manpower' créée")
            
        if 'Score Raison de recommandation Manpower' not in df_main.columns:
            df_main['Score Raison de recommandation Manpower'] = None
            print("➕ Colonne 'Score Raison de recommandation Manpower' créée")
        
        # Récupérer les textes à analyser
        texts_to_analyze = df_main['Raison recommandation Manpower'].fillna('').astype(str)
        
        # Filtrer les textes non vides (différents de 'Pas de réponse' et non vides)
        valid_texts = texts_to_analyze[
            (texts_to_analyze != '') & 
            (texts_to_analyze != 'Pas de réponse') &
            (texts_to_analyze.notna())
        ]
        
        print(f"📝 Analyse de {len(valid_texts)} textes de recommandation sur {len(df_main)} lignes...")
        
        if len(valid_texts) == 0:
            print("⚠️ Aucun texte valide à analyser")
            return df_main
        
        # Analyse par batch optimisée pour éviter les timeouts
        results = []
        batch_size = 10  # Réduire la taille des batchs pour éviter les timeouts
        
        def progress_callback(progress, processed, total):
            """Callback pour afficher la progression"""
            logging.info(f"🔄 Analyse sentiment: {processed}/{total} ({progress}%)")
        
        # Analyser par petits lots avec progression
        batch_texts = safe_tolist(texts_to_analyze.values, label='texts_to_analyze.values')
        results = analyzer.batch_analyze(batch_texts, batch_size=batch_size, progress_callback=progress_callback)
        
        # Appliquer les résultats au DataFrame
        sentiments, scores = zip(*results) if results else ([], [])
        
        df_main['Sentiment Raison de recommandation Manpower'] = list(sentiments)
        df_main['Score Raison de recommandation Manpower'] = list(scores)
        
        # Statistiques des résultats
        sentiment_counts = pd.Series(sentiments).value_counts()
        print(f"📊 Résultats de l'analyse de sentiment:")
        for sentiment, count in sentiment_counts.items():
            print(f"  • {sentiment}: {count} textes")
        
        # Statistiques des scores
        scores_series = pd.Series(scores)
        print(f"📈 Scores moyens: {scores_series.mean():.1f} (min: {scores_series.min():.1f}, max: {scores_series.max():.1f})")
        
        print("✅ Analyse de sentiment CamemBERT terminée avec succès")
        return df_main
        
    except ImportError as e:
        print(f"❌ Erreur d'import CamemBERT: {e}")
        print("⚠️ Installation des dépendances requise: pip install torch transformers")
        return df_main
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse de sentiment: {e}")
        import traceback
        traceback.print_exc()
        return df_main

def fix_column_encoding(columns):
    """Corrige les problèmes d'encodage dans les noms de colonnes"""
    encoding_fixes = {
        # Caractères mal encodés -> caractères corrects
        'lâ€™': "l'",
        'câ€™': "c'",
        'dâ€™': "d'",
        'sâ€™': "s'",
        'Ã©': 'é',
        'Ã ': 'à',
        'Ã¨': 'è',
        'Ã§': 'ç',
        'Ã¹': 'ù',
        'Ã´': 'ô',
        'Ã¢': 'â',
        'Ã®': 'î',
        'Ã«': 'ë',
        'Ã¯': 'ï',
        'Ã¼': 'ü',
        'proposÃ©s': 'proposés',
        'ConformitÃ©': 'Conformité',
        'QualitÃ©': 'Qualité',
        'AmabilitÃ©': 'Amabilité',
        'RÃ©activitÃ©': 'Réactivité',
        'EfficacitÃ©': 'Efficacité',
        'PrÃ©nom': 'Prénom',
        'enrichi': 'enrichi',
        'adÃ©quation': 'adéquation',
        'rÃ©activitÃ©': 'réactivité',
        'rÃ©glementation': 'réglementation',
        'prÃ©vention': 'prévention',
        'sÃ©curitÃ©': 'sécurité',
        'matiÃ¨re': 'matière',
        'sociÃ©tÃ©': 'société',
        'Ã©chelle': 'échelle',
        'interrogÃ©e': 'interrogée',
        'disponibilitÃ©': 'disponibilité',
        'â€™': "'",
        'â€™': "'",
        '?': ' ?',
    }
    
    fixed_columns = []
    for col in columns:
        fixed_col = str(col)
        for wrong, correct in encoding_fixes.items():
            fixed_col = fixed_col.replace(wrong, correct)
        fixed_columns.append(fixed_col)
    
    return fixed_columns

# Colonnes à conserver côté performance et interview (mapping prompt)
PERFORMANCE_COLS = [
    'Année', 'Mois', 'type entité', 'Code DR', 'DR', 'code agence', 'agence',
    'Ouvert / Fermé', 'No Siret', 'raison sociale', 'Ca Cum A', 'Ca Cum A-1',
    'var ca cum', 'Ca Mois M', 'Ca Mois M-1', 'var ca mois', 'Ca Cum A SIRET',
    'Ca Cum A-1 SIRET', 'var ca cum SIRET', 'ca mois A SIRET', 'ca mois A-1 SIRET', 'var ca mois SIRET', 'ETP Cum A', 'ETP Cum A-1', 'var ETP cum', 'siret_agence'
]
INTERVIEW_COLS = [
    'Campagne d\'appels', 'CODE_AGENC', 'SIRET', 'Satisf.\n\nGlobale',
    'Raison note satisfaction',
    'Sentiment Raison note satisfaction', 'Score Raison note satisfaction',
    'Concurrent OnSite',
    'Q5 - Amabilité et disponibilit',
    'Q6 - Connaissance entreprise et objectifs',
    'Q7 - Contribution à votre performance et à l\'atteinte de vos objectifs',
    'Q8 - Qualité de collaboration',
    'Sentiment Q8 - Qualité de collaboration', 'Score Q8 - Qualité de collaboration',
    'Q9 - Conformité nombre de candidatures',
    'Q10 - Qualité et pertinence profils',
    'Q11 - Diriez-vous que l\'adéquation entre les candidats proposés par MANPOWER et votre demande est :',  # Nom original long !
    'Sentiment Q11 - Qualité adéquation candidats', 'Score Q11 - Qualité adéquation candidats',
    'Q12 - Réactivité pour répondre à vos besoins',
    'Q13 - Efficacité',
    'Q14 - Quailté réactivité',
    'Sentiment Q14 - Quailté réactivité', 'Score Q14 - Quailté réactivité',
    'Q15 - Production et suivi des contrats',
    'Q16 - Prestation administrative, c\'est-à-dire les relevés d\'activités et la facturation',
    'Q17 - Qualité presta administrative',
    'Sentiment Q17 - Qualité presta administrative', 'Score Q17 - Qualité presta administrative',
    'Q18 - Proactivité',
    'Q19 - Qualité informations règlementation TT',
    'Q20 - Actions prévention sécurité',
    'Q21 - Diriez-vous que l\'expertise de MANPOWER est :',
    'Sentiment Q21 - Qualité expertise', 'Score Q21 - Qualité expertise',
    'Q21bis - Sur une échelle de 0 à 10, recommanderiez-vous [CONCURRENT PRINCIPAL CITE] pour du TRAVAIL TEMPORAIRE ? ',
    'Note Recommandation Manpower', 'Raison recommandation Manpower',  # Nom après renommage !
    'Sentiment Raison de recommandation Manpower', 'Score Raison de recommandation Manpower',
    'siret_agence'
]
# Note: SIRET est déjà inclus dans la liste ci-dessus, pas besoin de l'ajouter à nouveau

# Mapping des colonnes à renommer côté interview (prompt)
RENAME_MAP = {
    'Pouvez-vous me dire pourquoi vous donnez cette note de satisfaction ?': 'Raison note satisfaction',
    'Quelle est LA société de travail temporaire à laquelle vous faites appel le plus souvent (en dehors de Manpower) ? ': 'Concurrent OnSite',
    'Q5 - Amabilité et disponibilité de votre partenaire Manpower': 'Q5 - Amabilité et disponibilit',
    'Q6 - Connaissance de votre entreprise, vos besoins, vos attentes, vos objectifs': 'Q6 - Connaissance entreprise et objectifs',
    'Q7 - Contribution à votre performance et à l\'atteinte de vos objectifs': 'Q7 - Contribution objectifs et performances',
    'Q8 - Diriez-vous que votre collaboration avec MANPOWER est :': 'Q8 - Qualité de collaboration',
    'Q9 - Conformité du nombre de candidatures proposées par rapport à vos attentes': 'Q9 - Conformité nombre de candidatures',
    'Q10 - Qualité et pertinence des profils proposés': 'Q10 - Qualité et pertinence profils',
    'Q11 - Diriez-vous que l\'adéquation entre les candidats proposés par MANPOWER et votre demande est :': 'Q11 - Qualité adéquation candidats',
    'Q12 - Réactivité pour répondre à vos besoins,': 'Q12 - Réactivité',
    'Q13 - Efficacité à agir en cas de dysfonctionnements ou de réclamations': 'Q13 - Efficacité',
    'Q14 - Diriez-vous que la réactivité de MANPOWER est :': 'Q14 - Quailté réactivité',
    'Q15 - Production des contrats, au suivi de leurs prestations, et leur gestion de fins de contrats': 'Q15 - Production et suivi des contrats',
    'Q16 - Prestation administrative, c\'est-à-dire les relevés d\'activités et la facturation': 'Q16 - Prestation administrative',
    'Q17 - Diriez-vous que le suivi de mission et la gestion administrative de MANPOWER est :': 'Q17 - Qualité presta administrative',
    'Q18 - Proactivité dans la poposition de candidatures spontanées': 'Q18 - Proactivité',
    'Q19 - Qualité des informations fournies sur la réglementation du travail temporaire': 'Q19 - Qualité informations règlementation TT',
    'Q20 - Actions en matière de prévention sécurité au travail': 'Q20 - Actions prévention sécurité',
    'Q21 - Diriez-vous que l\'expertise de MANPOWER est :': 'Q21 - Qualité expertise',
    'Q21bis - Sur une échelle de 0 à 10, recommanderiez-vous [CONCURRENT PRINCIPAL CITE] pour du TRAVAIL TEMPORAIRE ?': 'Note Recommandation concurrent',
    'Recommandation': 'Note Recommandation Manpower',
    # Toutes les variantes possibles pour la colonne recommandation
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation?': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation?  ': 'Raison recommandation Manpower',
    'Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?  ': 'Raison recommandation Manpower',
}

# Champs textuels à analyser pour le sentiment
SENTIMENT_FIELDS = [
    'Raison note satisfaction',
    'Q8 - Qualité de collaboration',
    'Q11 - Qualité adéquation candidats',
    'Q14 - Quailté réactivité',
    'Q17 - Qualité presta administrative',
    'Q21 - Qualité expertise',
    'Raison recommandation Manpower',
]

# Champs pour stocker le label et le score
SENTIMENT_LABELS = {
    'Raison note satisfaction': ('Sentiment Raison note satisfaction', 'Score raison note de satisfaction'),
    'Q8 - Qualité de collaboration': ('Sentiment Q8', 'Score Sentiment Q8'),
    'Q11 - Qualité adéquation candidats': ('Sentiment Q11', 'Score Sentiment Q11'),
    'Q14 - Quailté réactivité': ('Sentiment Q14', 'Score Sentiment Q14'),
    'Q17 - Qualité presta administrative': ('Sentiment Q17', 'Score Sentiment Q17'),
    'Q21 - Qualité expertise': ('Sentiment Q21', 'Score Sentiment Q21'),
    'Raison recommandation Manpower': ('Sentiment raison recommandation Manpower', 'Score sentiment recommandation Manpower'),
}

def process_excel_files(file1, file2):
    """
    Traite les fichiers Excel en détectant automatiquement lequel est performance vs interview
    """
    # Lecture des deux fichiers
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)
    
    # Correction de l'encodage des noms de colonnes
    df1.columns = fix_column_encoding(df1.columns)
    df2.columns = fix_column_encoding(df2.columns)
    
    # Auto-détection : le fichier interview contient les colonnes Q, le fichier performance contient "Année"
    cols1 = safe_tolist(df1.columns, label='df1.columns')
    cols2 = safe_tolist(df2.columns, label='df2.columns')
    
    # Détection fichier interview : contient des colonnes commençant par "Q" et "Satisf" et "SIRET"
    interview_indicators = ['Q5', 'Q7', 'Q8', 'Q11', 'Satisf', 'SIRET', 'CODE_AGENC', 'Campagne']
    is_file1_interview = sum(1 for indicator in interview_indicators if any(indicator in str(col) for col in cols1)) >= 3
    is_file2_interview = sum(1 for indicator in interview_indicators if any(indicator in str(col) for col in cols2)) >= 3
    
    # Détection fichier performance : contient "Année" et "Ca Cum A" et "No Siret"
    performance_indicators = ['Année', 'Ca Cum A', 'No Siret', 'code agence', 'raison sociale']
    is_file1_performance = sum(1 for indicator in performance_indicators if any(indicator in str(col) for col in cols1)) >= 3
    is_file2_performance = sum(1 for indicator in performance_indicators if any(indicator in str(col) for col in cols2)) >= 3
    
    print(f"🔍 Indicateurs interview file1: {sum(1 for indicator in interview_indicators if any(indicator in str(col) for col in cols1))}/8")
    print(f"🔍 Indicateurs interview file2: {sum(1 for indicator in interview_indicators if any(indicator in str(col) for col in cols2))}/8")
    print(f"🔍 Indicateurs performance file1: {sum(1 for indicator in performance_indicators if any(indicator in str(col) for col in cols1))}/5")
    print(f"🔍 Indicateurs performance file2: {sum(1 for indicator in performance_indicators if any(indicator in str(col) for col in cols2))}/5")
    
    # Attribution automatique des rôles
    if is_file1_interview and is_file2_performance:
        print("🔄 Auto-détection: file1 = INTERVIEW, file2 = PERFORMANCE")
        df_interview = df1
        df_performance = df2
    elif is_file2_interview and is_file1_performance:
        print("🔄 Auto-détection: file1 = PERFORMANCE, file2 = INTERVIEW")
        df_performance = df1
        df_interview = df2
    else:
        # Fallback sur l'ordre d'origine si auto-détection échoue
        print("⚠️  Auto-détection échouée, utilisation ordre d'origine")
        df_performance = df1
        df_interview = df2
    
    print(f"📊 FICHIER PERFORMANCE: {df_performance.shape[1]} colonnes, {df_performance.shape[0]} lignes")
    print(f"📋 FICHIER INTERVIEW: {df_interview.shape[1]} colonnes, {df_interview.shape[0]} lignes")
    
    # Debug: afficher toutes les colonnes Q du fichier interview
    q_columns = [col for col in df_interview.columns if str(col).startswith('Q')]
    print(f"🔍 Colonnes Q trouvées: {q_columns}")
    
    # Debug: chercher spécifiquement Q11
    q11_candidates = [col for col in df_interview.columns if 'Q11' in str(col)]
    print(f"🎯 Colonnes contenant Q11: {q11_candidates}")
    
    if q11_candidates:
        actual_q11_col = q11_candidates[0]  # Prendre la première trouvée
        print(f"✅ Q11 trouvée: '{actual_q11_col}'")
        print(f"🎯 Échantillon Q11: {safe_tolist(df_interview[actual_q11_col].dropna().head(3), label='Q11')}")
    else:
        print("❌ Aucune colonne Q11 trouvée !")
        print("📋 Toutes les colonnes interview:")
        for i, col in enumerate(df_interview.columns, 1):
            print(f"   {i:2d}. {col}")

    # Nettoyage SIRET sur 14 caractères, sans décimale, AVANT création de siret_agence
    if 'No Siret' in df_performance.columns:
        df_performance['No Siret'] = df_performance['No Siret'].apply(lambda x: str(x).split('.')[0].zfill(14))
    if 'SIRET' in df_interview.columns:
        df_interview['SIRET'] = df_interview['SIRET'].apply(lambda x: str(x).split('.')[0].zfill(14))

    # Gestion des SIRET vides dans interview (seulement si la colonne SIRET existe)
    if 'SIRET' in df_interview.columns:
        mask_empty = df_interview['SIRET'].isnull() | (df_interview['SIRET'] == '')
        for idx in df_interview[mask_empty].index:
            code_ag = df_interview.at[idx, 'CODE_AGENC']
            match = df_performance[df_performance['code agence'] == code_ag]
            if not match.empty:
                df_interview.at[idx, 'SIRET'] = match.iloc[0]['No Siret']
    else:
        print("⚠️ ATTENTION: Colonne 'SIRET' non trouvée dans le fichier interview")
        print(f"📋 Colonnes disponibles: {safe_tolist(df_interview.columns, label='df_interview.columns')}")
        # Si SIRET n'existe pas, on peut essayer de la créer à partir de CODE_AGENC
        if 'CODE_AGENC' in df_interview.columns and 'code agence' in df_performance.columns:
            print("🔧 Tentative de création de la colonne SIRET à partir de CODE_AGENC...")
            df_interview['SIRET'] = ''
            for idx in df_interview.index:
                code_ag = df_interview.at[idx, 'CODE_AGENC']
                match = df_performance[df_performance['code agence'] == code_ag]
                if not match.empty:
                    df_interview.at[idx, 'SIRET'] = match.iloc[0]['No Siret']
            print(f"✅ Colonne SIRET créée avec {df_interview['SIRET'].notna().sum()} valeurs remplies")

    # --- TRAITEMENT AVANT FUSION ---
    # Correction robuste du nom de la colonne Q12 - Réactivité (avec ou sans virgule)
    q12_candidates = [col for col in df_interview.columns if 'Q12' in str(col) and 'Réactivit' in str(col)]
    actual_q12_col = None
    if q12_candidates:
        # On cherche la première colonne Q12 qui ne contient PAS de valeurs de type DR
        for candidate in q12_candidates:
            sample_values = safe_tolist(df_interview[candidate].dropna().astype(str).head(10), label='Q12')
            # Critère : au moins 7/10 valeurs doivent être numériques ou 'Pas de réponse'
            def is_valid_q12(val):
                return val.replace('.', '', 1).isdigit() or val.strip().lower() == 'pas de réponse'
            valid_count = sum(is_valid_q12(v) for v in sample_values)
            dr_count = sum('D.R.' in v for v in sample_values)
            if valid_count >= 7 and dr_count == 0:
                actual_q12_col = candidate
                if actual_q12_col != 'Q12 - Réactivité pour répondre à vos besoins':
                    df_interview = df_interview.rename(columns={actual_q12_col: 'Q12 - Réactivité pour répondre à vos besoins'})
                    print(f"✅ Colonne Q12 renommée de '{actual_q12_col}' vers 'Q12 - Réactivité pour répondre à vos besoins'")
                break
            else:
                print(f"❌ Colonne Q12 candidate '{candidate}' rejetée : valeurs détectées = {sample_values}")
        if not actual_q12_col:
            print("❌ Aucune colonne Q12 valide trouvée (notes ou 'Pas de réponse'). Vérifiez le fichier source !")
    else:
        print("❌ Colonne Q12 - Réactivité non trouvée dans df_interview !")
    # Correction du mapping RENAME_MAP pour accepter les deux variantes (avec et sans virgule)
    if 'Q12 - Réactivité pour répondre à vos besoins' not in RENAME_MAP:
        RENAME_MAP['Q12 - Réactivité pour répondre à vos besoins'] = 'Q12 - Réactivité'
    
    # Remplissage des valeurs manquantes par 'Pas de réponse' pour les colonnes interview importantes
    important_interview_cols = [
        'Satisf.\n\nGlobale',
        'Raison note satisfaction', 
        'Quelle est LA société de travail temporaire à laquelle vous faites appel le plus souvent (en dehors de Manpower) ? ',
        'Q7 - Contribution à votre performance et à l\'atteinte de vos objectifs',
        actual_q11_col,  # Utiliser le nom exact trouvé
        'Q12 - Réactivité pour répondre à vos besoins',
        'Q16 - Prestation administrative, c\'est-à-dire les relevés d\'activités et la facturation',
        'Q21 - Diriez-vous que l\'expertise de MANPOWER est :',
        'Q21bis - Sur une échelle de 0 à 10, recommanderiez-vous [CONCURRENT PRINCIPAL CITE] pour du TRAVAIL TEMPORAIRE ? ',
        'Pouvez-vous me dire pourquoi vous donner cette note de recommandation?  '
    ]
    
    # Filtrer pour ne garder que les colonnes qui existent réellement
    important_interview_cols = [col for col in important_interview_cols if col and col in df_interview.columns]
    
    for col in important_interview_cols:
        if col in df_interview.columns:
            # Compter les vraies valeurs avant remplissage
            vraies_valeurs_avant = df_interview[col].notna().sum()
            # Remplir SEULEMENT les NaN
            df_interview[col] = df_interview[col].fillna('Pas de réponse')
            vraies_valeurs_apres = (df_interview[col] != 'Pas de réponse').sum()
            print(f"Colonne '{col[:50]}...' - vraies données conservées: {vraies_valeurs_apres}/{vraies_valeurs_avant}")
    
    # Vérification post-remplissage pour la colonne Q11
    if actual_q11_col and actual_q11_col in df_interview.columns:
        q11_col = df_interview[actual_q11_col]
        vraies_donnees_q11 = (q11_col != 'Pas de réponse').sum()
        print(f"✅ Q11 contient {vraies_donnees_q11} vraies réponses")
        print(f"📊 Exemples Q11: {safe_tolist(q11_col.value_counts().head(), label='Q11')}")
    else:
        print("❌ ERREUR: Colonne Q11 manquante après remplissage !")

    # Colonnes à analyser pour le sentiment (utiliser les noms réels trouvés)
    sentiment_patterns = {
        'Raison satisfaction': 'pourquoi vous donnez cette note de satisfaction',
        'Q8 collaboration': 'Q8',
        'Q11 adéquation': actual_q11_col,  # Utiliser le nom exact de Q11
        'Q14 réactivité': 'Q14',
        'Q17 administrative': 'Q17',
        'Q21 expertise': 'Q21',
        'Raison recommandation': 'pourquoi vous donner cette note de recommandation'
    }
    
    # Trouver les colonnes réelles pour l'analyse sentiment
    sentiment_cols_to_process = []
    for pattern_name, pattern in sentiment_patterns.items():
        if pattern == actual_q11_col and actual_q11_col:
            # Cas spécial pour Q11
            sentiment_cols_to_process.append(actual_q11_col)
            print(f"✅ Sentiment {pattern_name}: {actual_q11_col}")
        elif pattern:
            matching_cols = [col for col in df_interview.columns if pattern.lower() in str(col).lower()]
            if matching_cols:
                sentiment_cols_to_process.append(matching_cols[0])
                print(f"✅ Sentiment {pattern_name}: {matching_cols[0]}")
            else:
                print(f"❌ Sentiment {pattern_name}: non trouvée (pattern: {pattern})")
    
    print(f"🎭 Colonnes sélectionnées pour analyse sentiment: {len(sentiment_cols_to_process)}")
    
    # Créer les colonnes sentiment/score VIDES (analyse sera faite sur df_main avec CamemBERT)
    for col in sentiment_cols_to_process:
        if col in df_interview.columns:
            df_interview[f'Sentiment {col}'] = None  # Laisser vide pour analyse ultérieure
            df_interview[f'Score {col}'] = None      # Laisser vide pour analyse ultérieure
            print(f"📝 Colonnes sentiment créées (vides): Sentiment {col[:30]}..., Score {col[:30]}...")

    # Ajout de la colonne siret_agence dans chaque DataFrame source
    if 'No Siret' in df_performance.columns and 'code agence' in df_performance.columns:
        df_performance['siret_agence'] = df_performance['No Siret'].astype(str) + df_performance['code agence'].astype(str)
        print("✅ siret_agence créée pour df_performance")
    else:
        print("❌ Impossible de créer siret_agence pour df_performance - colonnes manquantes")
        
    if 'SIRET' in df_interview.columns and 'CODE_AGENC' in df_interview.columns:
        df_interview['siret_agence'] = df_interview['SIRET'].astype(str) + df_interview['CODE_AGENC'].astype(str)
        print("✅ siret_agence créée pour df_interview")
    else:
        print("❌ Impossible de créer siret_agence pour df_interview")
        print(f"📋 Colonnes SIRET présente: {'SIRET' in df_interview.columns}")
        print(f"📋 Colonne CODE_AGENC présente: {'CODE_AGENC' in df_interview.columns}")
        if 'SIRET' not in df_interview.columns:
            print("🔧 Tentative de création alternative de siret_agence...")
            # Si on a réussi à créer SIRET plus haut, essayons à nouveau
            if 'SIRET' in df_interview.columns and 'CODE_AGENC' in df_interview.columns:
                df_interview['siret_agence'] = df_interview['SIRET'].astype(str) + df_interview['CODE_AGENC'].astype(str)
                print("✅ siret_agence créée après correction SIRET")
            else:
                print("❌ Impossible de créer siret_agence même après tentative de correction")
                raise Exception("Colonne SIRET manquante dans le fichier interview - impossible de continuer le traitement")

    # DEBUG : Afficher infos clés avant fusion
    print('df_performance shape:', df_performance.shape)
    print('df_interview shape:', df_interview.shape)
    print('Exemples siret_agence performance:', safe_tolist(df_performance['siret_agence'].head(), label='siret_agence performance'))
    print('Exemples siret_agence interview:', safe_tolist(df_interview['siret_agence'].head(), label='siret_agence interview'))
    print('Année unique performance:', df_performance['Année'].unique() if 'Année' in df_performance.columns else 'N/A')
    print("Campagne d'appels unique interview:", df_interview["Campagne d'appels"].unique() if "Campagne d'appels" in df_interview.columns else 'N/A')
    
    # VISUALISATION : Affichage du DataFrame df_interview dans le terminal
    print('\n' + '='*80)
    print('VISUALISATION DU DATAFRAME df_interview')
    print('='*80)
    print(f'Colonnes ({len(df_interview.columns)}):')
    print(safe_tolist(df_interview.columns, label='df_interview.columns'))
    print('\nPremières lignes du DataFrame:')
    print(df_interview.head(10).to_string())
    print('\nInfo générale du DataFrame:')
    print(df_interview.info())
    print('='*80 + '\n')

    # Forcer les types Année et Campagne d'appels en int si possible
    if 'Année' in df_performance.columns:
        df_performance['Année'] = pd.to_numeric(df_performance['Année'], errors='coerce').astype('Int64')
    if "Campagne d'appels" in df_interview.columns:
        df_interview["Campagne d'appels"] = pd.to_numeric(df_interview["Campagne d'appels"], errors='coerce').astype('Int64')

    # DEBUG : Vérifier spécifiquement la colonne Q11 avant fusion
    print(f"\n=== DEBUG Q11 AVANT FUSION ===")
    if 'Q11 - Qualité adéquation candidats' in df_interview.columns:
        q11_col = df_interview['Q11 - Qualité adéquation candidats']
        print(f"Q11 présente dans df_interview: OUI")
        print(f"Valeurs non-null: {q11_col.notna().sum()}/{len(q11_col)}")
        print(f"Valeurs uniques: {q11_col.value_counts().head()}")
        print(f"Exemples: {safe_tolist(q11_col.head(5), label='Q11')}")
    else:
        print(f"Q11 présente dans df_interview: NON")
        q11_candidates = [col for col in df_interview.columns if 'Q11' in str(col) or 'adéquation' in str(col).lower()]
        print(f"Colonnes contenant Q11 ou adéquation: {q11_candidates}")

    # Fusion principale sur la clé enrichie siret_agence uniquement
    df_merge = pd.merge(
        df_performance,
        df_interview,
        on='siret_agence',
        how='left',
        suffixes=('', '_interview')
    )
    print('df_merge shape après merge:', df_merge.shape)
    print('Exemples Année/ Campagne d\'appels après merge:', df_merge[['Année', "Campagne d'appels"]].head().to_dict())
    
    # NETTOYAGE DES COLONNES DUPLICATAS VIDES
    print(f"\n=== NETTOYAGE DES COLONNES DUPLICATAS ===")
    columns_to_drop = []
    
    # Identifier les colonnes avec suffixes numériques (.1, .2, etc.) qui sont vides
    for col in df_merge.columns:
        if col.endswith('.1') or col.endswith('.2') or col.endswith('.3'):
            # Vérifier si la colonne est entièrement vide (NaN ou None)
            if df_merge[col].isna().all():
                columns_to_drop.append(col)
                print(f"🗑️ Colonne duplicata vide détectée : '{col}'")
            else:
                # Vérifier si elle contient seulement des valeurs inutiles
                non_null_values = df_merge[col].dropna()
                if len(non_null_values) == 0:
                    columns_to_drop.append(col)
                    print(f"🗑️ Colonne duplicata sans données utiles : '{col}'")
                else:
                    print(f"⚠️ Colonne duplicata avec données : '{col}' ({len(non_null_values)} valeurs)")
    
    # Supprimer les colonnes duplicatas vides
    if columns_to_drop:
        df_merge = df_merge.drop(columns=columns_to_drop)
        print(f"✅ {len(columns_to_drop)} colonnes duplicatas supprimées : {columns_to_drop}")
        print(f"📊 Nouvelle shape après nettoyage : {df_merge.shape}")
    else:
        print("✅ Aucune colonne duplicata vide trouvée")
    
    # NETTOYAGE SPÉCIFIQUE DES COLONNES DE SENTIMENT
    print(f"\n=== NETTOYAGE COLONNES SENTIMENT ===")
    
    # Supprimer la colonne vide 'Raison recommandation Manpower.1' si elle existe et est vide
    if 'Raison recommandation Manpower.1' in df_merge.columns:
        if df_merge['Raison recommandation Manpower.1'].isna().all():
            df_merge = df_merge.drop(columns=['Raison recommandation Manpower.1'])
            print("🗑️ Colonne 'Raison recommandation Manpower.1' supprimée (entièrement vide)")
        else:
            # Si elle contient des données, la renommer
            df_merge = df_merge.rename(columns={'Raison recommandation Manpower.1': 'Sentiment Raison de recommandation Manpower'})
            print("🔄 Colonne 'Raison recommandation Manpower.1' renommée en 'Sentiment Raison de recommandation Manpower'")
    
    # Ajouter la colonne sentiment si elle n'existe pas déjà
    if 'Sentiment Raison de recommandation Manpower' not in df_merge.columns:
        df_merge['Sentiment Raison de recommandation Manpower'] = None  # Sera remplie par l'analyse de sentiment
        print("➕ Colonne 'Sentiment Raison de recommandation Manpower' ajoutée")
    
    # Ajouter la colonne score sentiment si elle n'existe pas déjà
    if 'Score Raison de recommandation Manpower' not in df_merge.columns:
        df_merge['Score Raison de recommandation Manpower'] = None  # Sera remplie par l'analyse de sentiment
        print("➕ Colonne 'Score Raison de recommandation Manpower' ajoutée")
    
    # DEBUG : Vérifier Q11 après fusion
    print(f"\n=== DEBUG Q11 APRÈS FUSION ===")
    if 'Q11 - Qualité adéquation candidats' in df_merge.columns:
        q11_merge = df_merge['Q11 - Qualité adéquation candidats']
        print(f"Q11 présente dans df_merge: OUI")
        print(f"Valeurs non-null: {q11_merge.notna().sum()}/{len(q11_merge)}")
        print(f"Exemples après fusion: {safe_tolist(q11_merge.head(5), label='Q11 fusion')}")
    else:
        print(f"Q11 présente dans df_merge: NON")
        q11_candidates = [col for col in df_merge.columns if 'Q11' in str(col) or 'adéquation' in str(col).lower()]
        print(f"Colonnes contenant Q11 ou adéquation dans df_merge: {q11_candidates}")
        print(f"Toutes les colonnes df_merge ({len(df_merge.columns)}): {safe_tolist(df_merge.columns, label='df_merge.columns')}")

    # Filtrer pour ne garder que les lignes où Campagne d'appels = Année - 1
    df_merge = df_merge[df_merge["Campagne d'appels"] == (df_merge['Année'] - 1)]
    print('df_merge shape après filtre année:', df_merge.shape)
    print('Exemples lignes après filtre:', df_merge.head().to_dict())

    # RENOMMAGE DES COLONNES selon RENAME_MAP
    print(f"\n=== RENOMMAGE DES COLONNES ===")
    columns_to_rename = {}
    processed_columns = set()  # Pour éviter les doublons
    
    for old_name, new_name in RENAME_MAP.items():
        # Chercher la colonne qui correspond exactement d'abord
        if old_name in df_merge.columns and old_name not in processed_columns:
            columns_to_rename[old_name] = new_name
            processed_columns.add(old_name)
            print(f"✅ Renommage exact: '{old_name[:60]}...' -> '{new_name}'")
        else:
            # Chercher par correspondance partielle
            matching_cols = [col for col in df_merge.columns 
                           if col not in processed_columns and 
                           (old_name.lower() in str(col).lower() or str(col).lower() in old_name.lower())]
            if matching_cols:
                actual_col = matching_cols[0]
                columns_to_rename[actual_col] = new_name
                processed_columns.add(actual_col)
                print(f"✅ Renommage: '{actual_col[:60]}...' -> '{new_name}'")
            else:
                # Recherche plus flexible pour les colonnes Q
                if old_name.startswith('Q') and ' - ' in old_name:
                    q_num = old_name.split(' - ')[0]  # Ex: 'Q11'
                    matching_q_cols = [col for col in df_merge.columns 
                                     if col not in processed_columns and q_num in str(col)]
                    if matching_q_cols:
                        actual_col = matching_q_cols[0]
                        columns_to_rename[actual_col] = new_name
                        processed_columns.add(actual_col)
                        print(f"✅ Renommage Q: '{actual_col[:60]}...' -> '{new_name}'")
                    else:
                        print(f"❌ Colonne non trouvée pour renommage: '{old_name}'")
                else:
                    print(f"❌ Colonne non trouvée pour renommage: '{old_name}'")
    
    # Appliquer le renommage
    if columns_to_rename:
        df_merge = df_merge.rename(columns=columns_to_rename)
        print(f"📝 {len(columns_to_rename)} colonnes renommées avec succès")
        
        # Vérifier spécifiquement Q11 après renommage
        q11_renamed_cols = [col for col in df_merge.columns if 'Q11' in str(col)]
        print(f"🎯 Colonnes Q11 après renommage: {q11_renamed_cols}")
    else:
        print("⚠️  Aucune colonne n'a été renommée")

    # === LOGGING BALISÉ POUR RENOMMAGE ET FUSION ===
    print("\n[LOG-ALIGN] Colonnes df_interview AVANT renommage :", safe_tolist(df_interview.columns, label='df_interview.columns'))
    if actual_q12_col:
        q12_col_data = df_interview['Q12 - Réactivité pour répondre à vos besoins']
        # Si plusieurs colonnes (DataFrame), prendre la première
        if hasattr(q12_col_data, 'columns'):
            print(f"[LOG-ALIGN] ⚠️ Plusieurs colonnes nommées 'Q12 - Réactivité pour répondre à vos besoins', on prend la première.")
            q12_col_data = q12_col_data.iloc[:, 0]
        print(f"[LOG-ALIGN] Exemples Q12 : {safe_tolist(q12_col_data.dropna().astype(str).head(5), label='Q12')}")
    print("[LOG-ALIGN] Colonnes df_interview APRÈS renommage :", safe_tolist(df_interview.columns, label='df_interview.columns'))
    print("[LOG-ALIGN] Colonnes df_merge après fusion :", safe_tolist(df_merge.columns, label='df_merge.columns'))
    print("[LOG-ALIGN] Colonnes df_merge après mapping RENAME_MAP :", safe_tolist(df_merge.columns, label='df_merge.columns'))
    # Les logs sur final_cols_checked sont UNIQUEMENT après sa création effective, plus aucun accès prématuré

    # Filtrage strict des colonnes selon le prompt
    # Construire INTERVIEW_COLS dynamiquement basé sur les colonnes réellement présentes
    
    # === MERGE SUPPLÉMENTAIRE POUR AJOUTER "Concurrent OnSite" AU BON ENDROIT ===
    print(f"\n=== AJOUT DE 'Concurrent OnSite' APRÈS 'No Siret' ===")
    
    # Vérifier si la colonne "Concurrent OnSite" existe dans df_merge
    concurrent_col = None
    if 'Concurrent OnSite' in df_merge.columns:
        concurrent_col = 'Concurrent OnSite'
    else:
        # Chercher d'autres variantes possibles
        concurrent_candidates = [col for col in df_merge.columns 
                               if 'société de travail temporaire' in str(col).lower() 
                               or 'concurrent' in str(col).lower()]
        if concurrent_candidates:
            concurrent_col = concurrent_candidates[0]
            print(f"📝 Colonne concurrent trouvée: '{concurrent_col}'")
    
    if concurrent_col:
        print(f"✅ Colonne 'Concurrent OnSite' disponible: {concurrent_col}")
        
        # Créer un DataFrame temporaire avec seulement siret_agence et Concurrent OnSite
        df_concurrent = df_merge[['siret_agence', concurrent_col]].copy()
        df_concurrent = df_concurrent.rename(columns={concurrent_col: 'Concurrent OnSite'})
        
        # Créer df_main_base sans la colonne concurrent pour éviter les doublons
        cols_without_concurrent = [col for col in df_merge.columns if col != concurrent_col]
        df_main_base = df_merge[cols_without_concurrent].copy()
        
        # Merger pour garantir que Concurrent OnSite est bien présente
        df_merge_with_concurrent = pd.merge(
            df_main_base,
            df_concurrent,
            on='siret_agence',
            how='left'
        )
        
        # Réorganiser les colonnes pour mettre "Concurrent OnSite" juste après "No Siret"
        cols = list(df_merge_with_concurrent.columns)
        
        # Trouver l'index de "No Siret"
        no_siret_idx = cols.index('No Siret') if 'No Siret' in cols else -1
        
        if no_siret_idx >= 0:
            # Retirer "Concurrent OnSite" de sa position actuelle
            if 'Concurrent OnSite' in cols:
                cols.remove('Concurrent OnSite')
            
            # L'insérer juste après "No Siret"
            cols.insert(no_siret_idx + 1, 'Concurrent OnSite')
            
            # Réorganiser le DataFrame
            df_merge = df_merge_with_concurrent[cols]
            print(f"✅ 'Concurrent OnSite' repositionnée juste après 'No Siret'")
            
            # Vérifier le résultat
            siret_idx = df_merge.columns.get_loc('No Siret')
            concurrent_idx = df_merge.columns.get_loc('Concurrent OnSite')
            print(f"📍 Position 'No Siret': {siret_idx}, Position 'Concurrent OnSite': {concurrent_idx}")
            
            if concurrent_idx == siret_idx + 1:
                print("✅ Positionnement correct vérifié")
            else:
                print(f"⚠️ Positionnement incorrect: attendu {siret_idx + 1}, obtenu {concurrent_idx}")
        else:
            print("❌ Colonne 'No Siret' non trouvée, impossible de positionner 'Concurrent OnSite'")
            df_merge = df_merge_with_concurrent
    else:
        print("❌ Aucune colonne concurrent trouvée dans df_merge")
        # Afficher les colonnes disponibles pour debug
        print(f"📋 Colonnes disponibles: {safe_tolist(df_merge.columns, label='df_merge.columns')}")
    
    print(f"📊 Shape après merge concurrent: {df_merge.shape}")
    
    # Colonnes d'interview à rechercher (utiliser les noms renommés de RENAME_MAP)
    interview_patterns = {
        'Campagne d\'appels': 'Campagne',
        'CODE_AGENC': 'CODE_AGENC',
        'SIRET': 'SIRET',
        'Satisf. Globale': 'Satisf',
        'Raison note satisfaction': 'Raison note satisfaction',  # Nom renommé
        'Concurrent OnSite': 'Concurrent OnSite',  # Nom renommé
        'Q5 - Amabilité et disponibilit': 'Q5 - Amabilité et disponibilit',  # Nom renommé
        'Q6 - Connaissance entreprise et objectifs': 'Q6 - Connaissance entreprise et objectifs',  # Nom renommé
        'Q7 - Contribution objectifs et performances': 'Q7 - Contribution objectifs et performances',  # Nom renommé
        'Q8 - Qualité de collaboration': 'Q8 - Qualité de collaboration',  # Nom renommé
        'Q9 - Conformité nombre de candidatures': 'Q9 - Conformité nombre de candidatures',  # Nom renommé
        'Q10 - Qualité et pertinence profils': 'Q10 - Qualité et pertinence profils',  # Nom renommé
        'Q11 - Qualité adéquation candidats': 'Q11 - Qualité adéquation candidats',  # Nom renommé
        'Q12 - Réactivité': 'Q12 - Réactivité',  # Nom renommé
        'Q13 - Efficacité': 'Q13 - Efficacité',  # Nom renommé
        'Q14 - Quailté réactivité': 'Q14 - Quailté réactivité',  # Nom renommé
        'Q15 - Production et suivi des contrats': 'Q15 - Production et suivi des contrats',  # Nom renommé
        'Q16 - Prestation administrative': 'Q16 - Prestation administrative',  # Nom renommé
        'Q17 - Qualité presta administrative': 'Q17 - Qualité presta administrative',  # Nom renommé
        'Q18 - Proactivité': 'Q18 - Proactivité',  # Nom renommé
        'Q19 - Qualité informations règlementation TT': 'Q19 - Qualité informations règlementation TT',  # Nom renommé
        'Q20 - Actions prévention sécurité': 'Q20 - Actions prévention sécurité',  # Nom renommé
        'Q21 - Qualité expertise': 'Q21 - Qualité expertise',  # Nom renommé
        'Note Recommandation concurrent': 'Note Recommandation concurrent',  # Nom renommé
        'Note Recommandation Manpower': 'Note Recommandation Manpower',  # Nom renommé
        'Raison recommandation Manpower': 'Raison recommandation Manpower',  # Nom renommé
        'siret_agence': 'siret_agence'
    }
    
    # Construire la liste des colonnes interview réellement trouvées
    actual_interview_cols = []
    for expected_name, search_pattern in interview_patterns.items():
        # Recherche exacte d'abord (après renommage)
        if expected_name in df_merge.columns:
            actual_interview_cols.append(expected_name)
            if 'Q11' in expected_name:
                print(f"✅ Q11 trouvée exactement: '{expected_name}'")
        else:
            # Recherche par pattern si pas trouvé exactement
            matching_cols = [col for col in df_merge.columns if search_pattern.lower() in str(col).lower()]
            if matching_cols:
                actual_interview_cols.append(matching_cols[0])
                if 'Q11' in expected_name:
                    print(f"✅ Q11 trouvée par pattern: '{matching_cols[0]}'")
            elif 'Q11' in expected_name:
                print(f"❌ Q11 non trouvée avec nom attendu '{expected_name}' ni pattern '{search_pattern}'")
                # Debug supplémentaire pour Q11
                q11_debug = [col for col in df_merge.columns if 'Q11' in str(col) or 'adéquation' in str(col).lower()]
                print(f"🔍 Debug Q11 - colonnes contenant Q11 ou adéquation: {q11_debug}")
    
    # Ajouter aussi les colonnes de sentiment créées (UNIQUEMENT les noms renommés courts)
    # Exclure les anciens noms longs qui contiennent "Diriez-vous" ou "Pouvez-vous me dire pourquoi vous donnez"
    sentiment_cols_in_merge = []
    for col in df_merge.columns:
        if ('Sentiment' in str(col) or 'Score' in str(col)):
            # Exclure les anciens noms longs non renommés
            if not ('Diriez-vous que' in str(col) or 'Pouvez-vous me dire pourquoi vous donnez' in str(col) or 'Pouvez-vous me dire pourquoi vous donner cette note de recommandation ?' in str(col)):
                sentiment_cols_in_merge.append(col)
            else:
                print(f"🗑️  Exclusion ancienne colonne: {col[:80]}...")
    
    actual_interview_cols.extend(sentiment_cols_in_merge)
    print(f"🎭 Colonnes sentiment/score conservées: {len(sentiment_cols_in_merge)}")
    
    print(f"🔍 Colonnes interview réellement trouvées: {len(actual_interview_cols)}")
    print(f"📋 Liste: {actual_interview_cols}")
    
    FINAL_COLS = PERFORMANCE_COLS + actual_interview_cols
    
    # Retirer les doublons et ne garder que les colonnes présentes
    FINAL_COLS = list(dict.fromkeys(FINAL_COLS))  # Supprime les doublons en gardant l'ordre
    
    # === GARANTIR QUE "Concurrent OnSite" EST JUSTE APRÈS "No Siret" DANS FINAL_COLS ===
    if 'Concurrent OnSite' in df_merge.columns and 'No Siret' in FINAL_COLS:
        print(f"🔧 Repositionnement de 'Concurrent OnSite' dans FINAL_COLS...")
        
        # Retirer "Concurrent OnSite" de sa position actuelle dans FINAL_COLS
        if 'Concurrent OnSite' in FINAL_COLS:
            FINAL_COLS.remove('Concurrent OnSite')
        
        # Trouver l'index de "No Siret" et insérer "Concurrent OnSite" juste après
        no_siret_idx = FINAL_COLS.index('No Siret')
        FINAL_COLS.insert(no_siret_idx + 1, 'Concurrent OnSite')
        print(f"✅ 'Concurrent OnSite' repositionnée dans FINAL_COLS à l'index {no_siret_idx + 1}")
    
    # === CONSTRUCTION ROBUSTE DE df_main ===
    final_cols_checked = []  # Toujours initialisée AVANT tout log
    for col in FINAL_COLS:
        if col in df_merge.columns:
            # Vérification spécifique pour Q12 : doit contenir des notes ou 'Pas de réponse'
            if col == 'Q12 - Réactivité':
                sample = safe_tolist(df_merge[col].dropna().astype(str).head(10), label=col)
                def is_valid_q12(val):
                    return val.replace('.', '', 1).isdigit() or val.strip().lower() == 'pas de réponse'
                valid_count = sum(is_valid_q12(v) for v in sample)
                dr_count = sum('D.R.' in v for v in sample)
                if valid_count >= 7 and dr_count == 0:
                    final_cols_checked.append(col)
                else:
                    print(f"❌ Colonne Q12 - Réactivité rejetée dans df_main : valeurs détectées = {sample}")
            else:
                final_cols_checked.append(col)
        else:
            print(f"⚠️ Colonne absente dans df_merge : {col}")
    if not final_cols_checked:
        raise Exception("Aucune colonne valide trouvée pour df_main : vérifiez le mapping et la fusion !")
    # Construction stricte de df_main avec les colonnes validées et dans l'ordre exact
    df_main = df_merge[final_cols_checked]
    # === PATCH: Récupération robuste de Q12 - Réactivité depuis df_interview via siret_agence ===
    try:
        # Détection de la bonne colonne Q12 dans df_interview
        q12_candidates = [col for col in df_interview.columns if 'Q12' in str(col) and 'Réactivit' in str(col)]
        actual_q12_col = None
        for candidate in q12_candidates:
            sample = df_interview[candidate].dropna().astype(str).head(10).tolist()
            valid_count = sum(
                v.replace('.', '', 1).isdigit() or v.lower().strip() == "pas de réponse"
                for v in sample
            )
            if valid_count / max(1, len(sample)) > 0.7:
                actual_q12_col = candidate
                break
        if actual_q12_col is not None and 'siret_agence' in df_interview.columns:
            q12_map = df_interview.set_index('siret_agence')[actual_q12_col].to_dict()
            df_main['Q12 - Réactivité (depuis interview)'] = df_main['siret_agence'].map(q12_map)
            print("[PATCH Q12] Colonne 'Q12 - Réactivité (depuis interview)' ajoutée à df_main via siret_agence.")
            print(f"[PATCH Q12] Exemples: {df_main[['siret_agence', 'Q12 - Réactivité (depuis interview)'].head(5)]}")
        else:
            print("[PATCH Q12] Impossible de trouver une colonne Q12 valide ou la colonne siret_agence dans df_interview.")
    except Exception as e:
        print(f"[PATCH Q12] Erreur lors de la récupération de Q12 depuis df_interview: {e}")
    # === PATCH: Récupération robuste de DR depuis df_performance via siret_agence ===
    try:
        if 'DR' in df_performance.columns and 'siret_agence' in df_performance.columns:
            dr_map = df_performance.set_index('siret_agence')['DR'].to_dict()
            df_main['DR (depuis performance)'] = df_main['siret_agence'].map(dr_map)
            print("[PATCH DR] Colonne 'DR (depuis performance)' ajoutée à df_main via siret_agence.")
            print(f"[PATCH DR] Exemples: {df_main[['siret_agence', 'DR (depuis performance)'].head(5)]}")
        else:
            print("[PATCH DR] Impossible de trouver la colonne DR ou siret_agence dans df_performance.")
    except Exception as e:
        print(f"[PATCH DR] Erreur lors de la récupération de DR depuis df_performance: {e}")
    # === LOGGING BALISÉ POUR RENOMMAGE ET FUSION (après construction effective) ===
    if 'final_cols_checked' in locals() and final_cols_checked:
        print("[LOG-ALIGN] Colonnes finales validées pour df_main :", final_cols_checked)
        # Q12 dans df_merge
        if 'Q12 - Réactivité' in df_merge.columns:
            q12_col_data_merge = df_merge['Q12 - Réactivité']
            if hasattr(q12_col_data_merge, 'columns'):
                print(f"[LOG-ALIGN] ⚠️ Plusieurs colonnes nommées 'Q12 - Réactivité' dans df_merge, on prend la première.")
                q12_col_data_merge = q12_col_data_merge.iloc[:, 0]
            print(f"[LOG-ALIGN] Exemples Q12 dans df_merge : {safe_tolist(q12_col_data_merge.dropna().astype(str).head(5), label='Q12')}")
        # Q12 dans df_main
        if 'Q12 - Réactivité' in df_main.columns:
            q12_col_data_main = df_main['Q12 - Réactivité']
            if hasattr(q12_col_data_main, 'columns'):
                print(f"[LOG-ALIGN] ⚠️ Plusieurs colonnes nommées 'Q12 - Réactivité' dans df_main, on prend la première.")
                q12_col_data_main = q12_col_data_main.iloc[:, 0]
            print(f"[LOG-ALIGN] Exemples Q12 dans df_main : {safe_tolist(q12_col_data_main.dropna().astype(str).head(5), label='Q12')}")
    
    # SUPPRESSION DU REMPLISSAGE POST-FUSION : les données interview ont déjà été nettoyées avant fusion
    # Le fillna post-fusion n'est nécessaire que pour les lignes sans match d'interview (left join)
    # mais ces lignes auront des NaN sur TOUTES les colonnes interview, pas besoin de remplir individuellement
    print(f"Taille df_main après filtrage colonnes: {df_main.shape}")
    print(f"Colonnes présentes dans df_main: {safe_tolist(df_main.columns, label='df_main.columns')}")
    
    # DEBUG spécifique pour Q11 - utiliser les colonnes réellement trouvées
    q11_cols_in_main = [col for col in df_main.columns if 'Q11' in str(col)]
    if q11_cols_in_main:
        q11_col_name = q11_cols_in_main[0]
        q11_values = df_main[q11_col_name]
        non_pas_de_reponse = q11_values[q11_values != 'Pas de réponse']
        print(f"✅ Q11 trouvée dans df_main avec {len(non_pas_de_reponse)} vraies réponses sur {len(q11_values)}")
        print(f"Exemples de vraies réponses Q11: {safe_tolist(non_pas_de_reponse.head(5), label='Q11')}")
        print(f"Distribution des valeurs Q11: {q11_values.value_counts().head()}")
    else:
        print("ERREUR: Colonne Q11 manquante dans df_main !")
        print(f"Colonnes contenant 'Q11': {[col for col in df_main.columns if 'Q11' in col]}")
    
    # Sauvegarde du DataFrame principal au format CSV dans data/output
    output_path = 'data/output/df_main.csv'
    
    # ANALYSE DE SENTIMENT AVANCÉE AVEC CAMEMBERT sur le DataFrame principal
    print(f"\n🤖 === ANALYSE DE SENTIMENT AVANCÉE AVEC CAMEMBERT ===")
    df_main = apply_camembert_sentiment_analysis(df_main)
    print("✅ Analyse CamemBERT terminée avec succès")
    
    # Export CSV avec virgule comme séparateur décimal (format français)
    df_main.to_csv(output_path, index=False, encoding='utf-8-sig', decimal=',', sep=';')
    print(f"💾 DataFrame principal sauvegardé : {output_path} (séparateur décimal: virgule)")
    
    # NETTOYAGE FINAL des colonnes dupliquées avant sauvegarde en base
    print(f"\n=== NETTOYAGE FINAL AVANT SAUVEGARDE ===")
    duplicate_cols = df_main.columns[df_main.columns.duplicated()]
    if len(duplicate_cols) > 0:
        print(f"⚠️ Colonnes dupliquées détectées: {safe_tolist(duplicate_cols, label='duplicate_cols')}")
        # Supprimer les colonnes dupliquées en gardant la première occurrence
        df_main = df_main.loc[:, ~df_main.columns.duplicated()]
        print(f"✅ Colonnes dupliquées supprimées. Nouvelle shape: {df_main.shape}")
    else:
        print("✅ Aucune colonne dupliquée détectée")

    # Sauvegarde dans la base SQLite
    try:
        # On supprime les anciennes données
        db.session.query(MainData).delete()
        db.session.commit()
        
        # Fonction helper pour gérer les valeurs Series/scalaires
        def safe_get(row, col_name, default_value=''):
            """Récupère une valeur en gérant les cas Series et scalaires"""
            try:
                value = row.get(col_name, default_value)
                # Si c'est une Series pandas, prendre la première valeur non-null
                if hasattr(value, 'iloc') and hasattr(value, 'dropna'):
                    non_null_values = value.dropna()
                    return non_null_values.iloc[0] if len(non_null_values) > 0 else default_value
                # Si c'est un numpy array, prendre le premier élément
                elif hasattr(value, '__len__') and hasattr(value, 'item') and len(value) > 0:
                    return value.item() if hasattr(value, 'item') else str(value)
                # Si c'est None ou NaN, retourner la valeur par défaut
                elif value is None or (hasattr(value, 'isna') and value.isna()):
                    return default_value
                # Valeur scalaire normale
                return value
            except Exception as e:
                print(f"⚠️ Erreur safe_get pour colonne '{col_name}': {e}")
                return default_value
        
        # On insère les nouvelles données avec les noms de colonnes mis à jour
        for _, row in df_main.iterrows():
            db_row = MainData(
                no_siret=safe_get(row, 'No Siret', ''),
                code_agence=safe_get(row, 'code agence', ''),
                siret_agence=safe_get(row, 'siret_agence', ''),
                siret_interview=safe_get(row, 'SIRET', ''),
                code_agenc=safe_get(row, 'CODE_AGENC', ''),
                campagne_appels=safe_get(row, "Campagne d'appels", ''),
                satisf_globale=safe_get(row, 'Satisf.\n\nGlobale', ''),
                raison_note_satisfaction=safe_get(row, 'Raison note satisfaction', ''),
                sentiment_raison_note_satisfaction=safe_get(row, 'Sentiment Raison note satisfaction', ''),
                score_raison_note_satisfaction=safe_get(row, 'Score raison note de satisfaction', 0),
                concurrent=safe_get(row, 'Concurrent OnSite', ''),
                q5_amabilite_disponibilite=safe_get(row, 'Q5 - Amabilité et disponibilit', ''),
                q6_connaissance_entreprise=safe_get(row, 'Q6 - Connaissance entreprise et objectifs', ''),
                q7_contribution_objectifs=safe_get(row, 'Q7 - Contribution à votre performance et à l\'atteinte de vos objectifs', ''),
                q8_qualite_collaboration=safe_get(row, 'Q8 - Qualité de collaboration', ''),
                sentiment_q8_qualite_collaboration=safe_get(row, 'Sentiment Q8 - Qualité de collaboration', ''),
                score_q8_qualite_collaboration=safe_get(row, 'Score Q8 - Qualité de collaboration', 0),
                q9_conformite_candidatures=safe_get(row, 'Q9 - Conformité nombre de candidatures', ''),
                q10_qualite_pertinence_profils=safe_get(row, 'Q10 - Qualité et pertinence profils', ''),
                q11_qualite_adequation_candidats=safe_get(row, 'Q11 - Diriez-vous que l\'adéquation entre les candidats proposés par MANPOWER et votre demande est :', ''),
                sentiment_q11_qualite_adequation_candidats=safe_get(row, 'Sentiment Q11 - Qualité adéquation candidats', ''),
                score_q11_qualite_adequation_candidats=safe_get(row, 'Score Q11 - Qualité adéquation candidats', 0),
                q12_reactivite=safe_get(row, 'Q12 - Réactivité pour répondre à vos besoins', ''),
                q13_efficacite=safe_get(row, 'Q13 - Efficacité', ''),
                q14_qualite_reactivite=safe_get(row, 'Q14 - Quailté réactivité', ''),
                sentiment_q14_qualite_reactivite=safe_get(row, 'Sentiment Q14 - Quailté réactivité', ''),
                score_q14_qualite_reactivite=safe_get(row, 'Score Q14 - Quailté réactivité', 0),
                q15_production_suivi_contrats=safe_get(row, 'Q15 - Production et suivi des contrats', ''),
                q16_prestation_administrative=safe_get(row, 'Q16 - Prestation administrative, c\'est-à-dire les relevés d\'activités et la facturation', ''),
                q17_qualite_presta_administrative=safe_get(row, 'Q17 - Qualité presta administrative', ''),
                sentiment_q17_qualite_presta_administrative=safe_get(row, 'Sentiment Q17 - Qualité presta administrative', ''),
                score_q17_qualite_presta_administrative=safe_get(row, 'Score Q17 - Qualité presta administrative', 0),
                q18_proactivite=safe_get(row, 'Q18 - Proactivité', ''),
                q19_qualite_infos_reglementation=safe_get(row, 'Q19 - Qualité informations règlementation TT', ''),
                q20_actions_prevention_securite=safe_get(row, 'Q20 - Actions prévention sécurité', ''),
                q21_qualite_expertise=safe_get(row, 'Q21 - Diriez-vous que l\'expertise de MANPOWER est :', ''),
                sentiment_q21_qualite_expertise=safe_get(row, 'Sentiment Q21 - Qualité expertise', ''),
                score_q21_qualite_expertise=safe_get(row, 'Score Q21 - Qualité expertise', 0),
                note_recommandation_concurrent=safe_get(row, 'Q21bis - Sur une échelle de 0 à 10, recommanderiez-vous [CONCURRENT PRINCIPAL CITE] pour du TRAVAIL TEMPORAIRE ? ', 0),
                note_recommandation_manpower=safe_get(row, 'Note Recommandation Manpower', 0),
                raison_recommandation_manpower=safe_get(row, 'Raison recommandation Manpower', ''),
                # Colonne sentiment renommée (utilise le bon nom)
                sentiment_raison_de_recommandation_manpower=safe_get(row, 'Sentiment Raison de recommandation Manpower', ''),
                score_raison_de_recommandation_manpower=safe_get(row, 'Score Raison de recommandation Manpower', 0),
                # Colonnes performance
                annee=safe_get(row, 'Année', 0),
                mois=safe_get(row, 'Mois', 0),
                type_entite=safe_get(row, 'type entité', ''),
                code_dr=safe_get(row, 'Code DR', ''),
                dr=safe_get(row, 'DR', ''),
                agence=safe_get(row, 'agence', ''),
                ouvert_ferme=safe_get(row, 'Ouvert / Fermé', ''),
                raison_sociale=safe_get(row, 'raison sociale', ''),
                ca_cum_a=safe_get(row, 'Ca Cum A', 0.0),
                ca_cum_a_1=safe_get(row, 'Ca Cum A-1', 0.0),
                var_ca_cum=safe_get(row, 'var ca cum', 0.0),
                ca_mois_m=safe_get(row, 'Ca Mois M', 0.0),
                ca_mois_m_1=safe_get(row, 'Ca Mois M-1', 0.0),
                var_ca_mois=safe_get(row, 'var ca mois', 0.0),
                ca_cum_a_siret=safe_get(row, 'Ca Cum A SIRET', 0.0),
                ca_cum_a_1_siret=safe_get(row, 'Ca Cum A-1 SIRET', 0.0),
                var_ca_cum_siret=safe_get(row, 'var ca cum SIRET', 0.0),
                ca_mois_a_siret=safe_get(row, 'ca mois A SIRET', 0.0),
                ca_mois_a_1_siret=safe_get(row, 'ca mois A-1 SIRET', 0.0),
                var_ca_mois_siret=safe_get(row, 'var ca mois SIRET', 0.0),
                # Colonnes ETP ajoutées
                etp_cum_a=safe_get(row, 'ETP Cum A', 0.0),
                etp_cum_a_1=safe_get(row, 'ETP Cum A-1', 0.0),
                var_etp_cum=safe_get(row, 'var ETP cum', 0.0)
            )
            db.session.add(db_row)
        db.session.commit()
        print(f"✅ Sauvegarde réussie : {len(df_main)} lignes insérées en base avec Q11 renommée")
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la sauvegarde en base : {str(e)}")
        raise Exception(f'Erreur lors de la sauvegarde en base : {str(e)}')

    return df_main

# Utilitaire robuste pour .tolist()
def safe_tolist(obj, label=None):
    import pandas as pd
    import numpy as np
    # DataFrame : prendre la première colonne
    if isinstance(obj, pd.DataFrame):
        if label:
            print(f"[LOG-ALIGN] ⚠️ Plusieurs colonnes pour '{label}', on prend la première.")
        obj = obj.iloc[:, 0]
    # Méthode moderne pandas
    if hasattr(obj, 'to_list'):
        return obj.to_list()
    # Numpy array
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Iterable (list, tuple, set...)
    if isinstance(obj, (list, tuple, set)):
        return list(obj)
    # Fallback universel
    try:
        return list(obj)
    except Exception:
        return [str(obj)]