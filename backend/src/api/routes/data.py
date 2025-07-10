from flask import Blueprint, request, jsonify
from src.api.controllers.data_controller import process_excel_files
import logging

import os
import pandas as pd

data_bp = Blueprint('data', __name__)
logger = logging.getLogger('data_api')

@data_bp.route('/process_excels', methods=['POST'])
def process_excels():
    logger.info('Requête reçue pour /process_excels')
    
    # Vérifier la taille des fichiers
    try:
        # On attend deux fichiers dans le formulaire : 'performance' et 'interview'
        if 'performance' not in request.files or 'interview' not in request.files:
            logger.warning('Fichiers manquants dans la requête')
            return jsonify({'error': 'Les deux fichiers Excel sont requis (performance, interview)'}), 400
        
        performance_file = request.files['performance']
        interview_file = request.files['interview']
        
        # Vérifier que les fichiers ne sont pas vides
        if performance_file.filename == '' or interview_file.filename == '':
            logger.warning('Fichiers vides dans la requête')
            return jsonify({'error': 'Les fichiers ne peuvent pas être vides'}), 400
    
    except Exception as e:
        logger.error(f'Erreur lors de la validation des fichiers: {e}')
        return jsonify({'error': 'Erreur lors de la validation des fichiers'}), 400
    
    # Traitement principal avec gestion des timeouts
    try:
        logger.info('Traitement des fichiers Excel...')
        
        # Import du timeout
        import signal
        import time
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Le traitement a pris trop de temps")
        
        # Démarrer le traitement
        start_time = time.time()
        df_main = process_excel_files(performance_file, interview_file)
        end_time = time.time()
        
        logger.info(f'Traitement terminé en {end_time - start_time:.2f} secondes')
        
        # Conversion des types problématiques pour JSON avant l'aperçu
        df_preview = df_main.head(5).copy()
        
        # Nettoyer les valeurs pour JSON
        for col in df_preview.columns:
            df_preview[col] = df_preview[col].astype(str)
            df_preview[col] = df_preview[col].replace({'nan': '', 'None': '', 'NaT': ''})
        
        # On retourne un aperçu du DataFrame principal (5 premières lignes)
        return jsonify({
            'success': True,
            'message': 'Traitement terminé avec succès',
            'processing_time': f'{end_time - start_time:.2f}s',
            'total_records': len(df_main),
            'preview': df_preview.to_dict(orient='records')
        }), 200
        
    except TimeoutError as e:
        logger.error(f'Timeout lors du traitement: {e}')
        return jsonify({'error': 'Le traitement a pris trop de temps et a été interrompu'}), 504
        
    except Exception as e:
        logger.error(f'Erreur lors du traitement : {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@data_bp.route('/main_data', methods=['GET'])
def get_main_data():
    logger.info('Requête reçue pour /main_data')
    output_path = 'data/output/df_main.csv'
    if not os.path.exists(output_path):
        logger.info('Aucune donnée trouvée (df_main.csv absent)')
        return jsonify({'data': []}), 200
    df = pd.read_csv(output_path, encoding='utf-8-sig', decimal=',', sep=';')
    # Ajout robuste de la colonne de segmentation
    grow_cols = ['var ca mois', 'var ca mois SIRET', 'var ca cum', 'var ca cum SIRET', 'var ETP cum']
    note_cols = ['Note Recommandation Manpower', 'Satisf.Globale']
    q_cols = [f'Q{i}' for i in list(range(5,10)) + list(range(10,22))]
    all_note_cols = note_cols + q_cols
    # Vérifie et crée les colonnes de croissance si absentes
    for col in grow_cols:
        if col not in df.columns:
            df[col] = 0
    # Vérifie et crée les colonnes de notes si absentes
    for col in all_note_cols:
        if col not in df.columns:
            df[col] = float('nan')
    # Vérifie la colonne de sentiment
    sentiment_col = 'Sentiment Raison de recommandation Manpower'
    if sentiment_col not in df.columns:
        df[sentiment_col] = 'NEUTRE'
    # Calculs robustes
    df[grow_cols] = df[grow_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['grow_pos_all'] = df[grow_cols].gt(0).all(axis=1)
    df['grow_nonneg_all'] = df[grow_cols].ge(0).all(axis=1)
    df['grow_any_neg'] = df[grow_cols].lt(0).sum(axis=1)
    df[all_note_cols] = df[all_note_cols].apply(pd.to_numeric, errors='coerce')
    df['score_moy'] = df[all_note_cols].mean(axis=1)
    df['sentiment_cat'] = df[sentiment_col].str.upper().fillna('NEUTRE')
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
    df['segment_agence'] = df.apply(seg, axis=1)
    fmt = request.args.get('format', 'json')
    if fmt == 'csv':
        logger.info('Export CSV demandé (format français avec virgule décimale)')
        # Export CSV avec format français : virgule comme séparateur décimal, point-virgule comme séparateur de colonnes
        csv_content = df.to_csv(index=False, encoding='utf-8-sig', decimal=',', sep=';')
        return (csv_content, 200, {'Content-Type': 'text/csv; charset=utf-8-sig'})
    else:
        logger.info('Export JSON envoyé')
        # Conversion des types problématiques pour JSON
        df_str = df.astype(str)
        return jsonify({'data': df_str.to_dict(orient='records')}), 200 

@data_bp.route('/preview_performance', methods=['POST'])
def preview_performance():
    logger.info('Requête reçue pour /preview_performance')
    if 'performance' not in request.files or 'interview' not in request.files:
        logger.warning('Fichiers manquants dans la requête')
        return jsonify({'error': 'Les deux fichiers Excel sont requis (performance, interview)'}), 400
    
    performance_file = request.files['performance']
    interview_file = request.files['interview']
    
    try:
        logger.info('Nettoyage du DataFrame Performance...')
        import pandas as pd
        
        # Lecture et nettoyage du DataFrame Performance comme dans le controller
        df_performance = pd.read_excel(performance_file)
        
        # Nettoyage SIRET sur 14 caractères, sans décimale
        if 'No Siret' in df_performance.columns:
            df_performance['No Siret'] = df_performance['No Siret'].apply(lambda x: str(x).split('.')[0].zfill(14))
        
        # Ajout de la colonne siret_agence
        if 'No Siret' in df_performance.columns and 'code agence' in df_performance.columns:
            df_performance['siret_agence'] = df_performance['No Siret'].astype(str) + df_performance['code agence'].astype(str)
        
        # Conversion des types problématiques pour JSON
        df_performance = df_performance.astype(str)
        
        logger.info('DataFrame Performance nettoyé avec succès')
        return jsonify({'data': df_performance.to_dict(orient='records')}), 200
    except Exception as e:
        logger.error(f'Erreur lors du nettoyage DataFrame Performance : {e}')
        return jsonify({'error': str(e)}), 500

@data_bp.route('/preview_interview', methods=['POST'])
def preview_interview():
    logger.info('Requête reçue pour /preview_interview')
    if 'performance' not in request.files or 'interview' not in request.files:
        logger.warning('Fichiers manquants dans la requête')
        return jsonify({'error': 'Les deux fichiers Excel sont requis (performance, interview)'}), 400
    
    performance_file = request.files['performance']
    interview_file = request.files['interview']
    
    try:
        logger.info('Nettoyage du DataFrame Interview...')
        import pandas as pd
        from src.modules.ai.sentiment import analyze_sentiment
        
        # Lecture des DataFrames
        df_performance = pd.read_excel(performance_file)
        df_interview = pd.read_excel(interview_file)
        
        # DEBUG : Afficher les colonnes avant renommage pour identifier les problèmes
        logger.info(f'Colonnes originales df_interview: {df_interview.columns.tolist()}')
        
        # Vérifier spécifiquement la colonne Q11
        q11_original = "Q11 - Diriez-vous que l'adéquation entre les candidats proposés par MANPOWER et votre demande est :"
        if q11_original in df_interview.columns:
            non_null_count = df_interview[q11_original].notna().sum()
            logger.info(f'Colonne Q11 trouvée avec {non_null_count} valeurs non-nulles sur {len(df_interview)}')
            logger.info(f'Exemples de valeurs Q11: {df_interview[q11_original].dropna().head(3).tolist()}')
        else:
            logger.warning(f'Colonne Q11 originale non trouvée. Colonnes contenant "Q11": {[col for col in df_interview.columns if "Q11" in str(col)]}')
            logger.warning(f'Colonnes contenant "adéquation": {[col for col in df_interview.columns if "adéquation" in str(col).lower()]}')
        
        # Nettoyage SIRET sur 14 caractères
        if 'No Siret' in df_performance.columns:
            df_performance['No Siret'] = df_performance['No Siret'].apply(lambda x: str(x).split('.')[0].zfill(14))
        if 'SIRET' in df_interview.columns:
            df_interview['SIRET'] = df_interview['SIRET'].apply(lambda x: str(x).split('.')[0].zfill(14))
        
        # Gestion des SIRET vides dans interview
        mask_empty = df_interview['SIRET'].isnull() | (df_interview['SIRET'] == '')
        for idx in df_interview[mask_empty].index:
            code_ag = df_interview.at[idx, 'CODE_AGENC']
            match = df_performance[df_performance['code agence'] == code_ag]
            if not match.empty:
                df_interview.at[idx, 'SIRET'] = match.iloc[0]['No Siret']
        
        # Renommage des colonnes selon le mapping
        rename_map = {
            "Pouvez-vous me dire pourquoi vous donnez cette note de satisfaction ?": "Raison note satisfaction",
            "Quelle est la société de travail temporaire à laquelle vous faites appel le plus souvent (en dehors de Manpower) ?": "Concurrent",
            "Q5 - Amabilité et disponibilité de votre partenaire Manpower": "Q5 - Amabilité et disponibilit",
            "Q6 - Connaissance de votre entreprise, vos besoins, vos attentes, vos objectifs": "Q6 - Connaissance entreprise et objectifs",
            "Q7 - Contribution à votre performance et à l'atteinte de vos objectifs": "Q7 - Contribution objectifs et performances",
            "Q8 - Diriez-vous que votre collaboration avec MANPOWER est :": "Q8 - Qualité de collaboration",
            "Q9 - Conformité du nombre de candidatures proposées par rapport à vos attentes": "Q9 - Conformité nombre de candidatures",
            "Q10 - Qualité et pertinence des profils proposés": "Q10 - Qualité et pertinence profils",
            "Q11 - Diriez-vous que l'adéquation entre les candidats proposés par MANPOWER et votre demande est :": "Q11 - Qualité adéquation candidats",
            "Q12 - Réactivité pour répondre à vos besoins,": "Q12 - Réactivité",
            "Q13 - Efficacité à agir en cas de dysfonctionnements ou de réclamations": "Q13 - Efficacité",
            "Q14 - Diriez-vous que la réactivité de MANPOWER est :": "Q14 - Quailté réactivité",
            "Q15 - Production des contrats, au suivi de leurs prestations, et leur gestion de fins de contrats": "Q15 - Production et suivi des contrats",
            "Q16 - Prestation administrative, c'est-à-dire les relevés d'activités et la facturation": "Q16 - Prestation administrative",
            "Q17 - Diriez-vous que le suivi de mission et la gestion administrative de MANPOWER est :": "Q17 - Qualité presta administrative",
            "Q18 - Proactivité dans la poposition de candidatures spontanées": "Q18 - Proactivité",
            "Q19 - Qualité des informations fournies sur la réglementation du travail temporaire": "Q19 - Qualité informations règlementation TT",
            "Q20 - Actions en matière de prévention sécurité au travail": "Q20 - Actions prévention sécurité",
            "Q21 - Diriez-vous que l'expertise de MANPOWER est :": "Q21 - Qualité expertise",
            "Q21bis - Sur une échelle de 0 à 10, recommanderiez-vous [CONCURRENT PRINCIPAL CITE] pour du TRAVAIL TEMPORAIRE ?": "Note Recommandation concurrent",
            "Recommandation": "Note Recommandation Manpower",
            "Pouvez-vous me dire pourquoi vous donner cette note de recommandation?": "Raison recommandation Manpower"
        }
        
        # ÉTAPE 1 : Supprimer les colonnes déjà renommées qui pourraient créer des conflits
        columns_to_remove = []
        for original_col, renamed_col in rename_map.items():
            if original_col in df_interview.columns and renamed_col in df_interview.columns:
                # Si les deux colonnes existent, supprimer la renommée (souvent vide/incorrecte)
                columns_to_remove.append(renamed_col)
                logger.info(f"Suppression de la colonne conflictuelle '{renamed_col}' (gardant '{original_col}' avec vraies données)")
        
        df_interview = df_interview.drop(columns=columns_to_remove, errors='ignore')
        
        # ÉTAPE 2 : Remplir SEULEMENT les valeurs NaN par 'Pas de réponse' AVANT renommage
        # Ne pas écraser les vraies données !
        for original_col, renamed_col in rename_map.items():
            if original_col in df_interview.columns:
                # Compter les vraies valeurs avant remplissage
                vraies_valeurs_avant = df_interview[original_col].notna().sum()
                
                # Remplir SEULEMENT les NaN
                df_interview[original_col] = df_interview[original_col].fillna('Pas de réponse')
                
                vraies_valeurs_apres = (df_interview[original_col] != 'Pas de réponse').sum()
                logger.info(f'Colonne "{original_col}" - vraies données conservées: {vraies_valeurs_apres}/{vraies_valeurs_avant}')
        
        # ÉTAPE 3 : Renommer les colonnes APRÈS remplissage
        df_interview = df_interview.rename(columns=rename_map)
        
        # DEBUG : Vérifier la colonne Q11 après renommage
        q11_renamed = 'Q11 - Qualité adéquation candidats'
        if q11_renamed in df_interview.columns:
            vraies_donnees_q11 = (df_interview[q11_renamed] != 'Pas de réponse').sum()
            pas_de_reponse_count = (df_interview[q11_renamed] == 'Pas de réponse').sum()
            logger.info(f'Après renommage - Q11 contient {vraies_donnees_q11} vraies réponses et {pas_de_reponse_count} "Pas de réponse"')
            logger.info(f'Exemples Q11 après traitement: {df_interview[q11_renamed].value_counts().head().to_dict()}')
        else:
            logger.error('ERREUR: Colonne Q11 manquante après renommage !')
        
        # Colonnes à analyser pour le sentiment
        sentiment_cols = [
            "Raison note satisfaction",
            "Q8 - Qualité de collaboration", 
            "Q11 - Qualité adéquation candidats",
            "Q14 - Quailté réactivité",
            "Q17 - Qualité presta administrative",
            "Q21 - Qualité expertise",
            "Raison recommandation Manpower"
        ]
        
        # Appliquer l'analyse de sentiment
        for col in sentiment_cols:
            if col in df_interview.columns:
                df_interview[f'Sentiment {col}'] = df_interview[col].apply(lambda x: analyze_sentiment(x)[0] if x != 'Pas de réponse' else 'Pas de réponse')
                df_interview[f'Score {col}'] = df_interview[col].apply(lambda x: analyze_sentiment(x)[1] if x != 'Pas de réponse' else 'Pas de réponse')
        
        # Ajout de la colonne siret_agence
        if 'SIRET' in df_interview.columns and 'CODE_AGENC' in df_interview.columns:
            df_interview['siret_agence'] = df_interview['SIRET'].astype(str) + df_interview['CODE_AGENC'].astype(str)
        
        # Conversion des types problématiques pour JSON
        df_interview = df_interview.astype(str)
        
        logger.info('DataFrame Interview nettoyé avec succès')
        return jsonify({'data': df_interview.to_dict(orient='records')}), 200
    except Exception as e:
        logger.error(f'Erreur lors du nettoyage DataFrame Interview : {e}')
        return jsonify({'error': str(e)}), 500

@data_bp.route('/test', methods=['GET'])
def test_connection():
    """Endpoint de test pour vérifier la connectivité"""
    logger.info('Test de connectivité backend')
    return jsonify({'status': 'ok', 'message': 'Backend is running'}), 200