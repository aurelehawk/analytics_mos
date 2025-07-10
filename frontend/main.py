import streamlit as st
import requests
import pandas as pd
import numpy as np
from io import StringIO, BytesIO
import sys
import os

# Ajouter le chemin vers les modules backend
backend_modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', 'src', 'modules', 'ai')
if backend_modules_path not in sys.path:
    sys.path.insert(0, backend_modules_path)

try:
    from siret_cleaner import clean_siret
except ImportError:
    # Fonction de fallback si le module n'est pas disponible
    def clean_siret(siret):
        """Fonction de nettoyage SIRET simplifiée"""
        if pd.isna(siret) or siret == '':
            return ''
        return str(siret).strip().replace(' ', '').replace('-', '')[:14]

API_URL = 'http://localhost:4000'

# Fonctions globales pour formater les DataFrames pour Excel français
def format_dataframe_for_french_excel(df):
    """Formate le DataFrame pour Excel français avec virgules décimales"""
    df_formatted = df.copy()
    
    # Identifier les colonnes numériques
    numeric_cols = df_formatted.select_dtypes(include=[np.number, 'float64', 'int64']).columns.tolist()
    
    # Exclure les colonnes qui doivent rester entières
    exclude_cols = ['Année', 'Mois', 'No Siret', 'SIRET', 'code agence', 'CODE_AGENC', 'Longueur']
    numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
    
    return df_formatted, numeric_cols

def apply_french_formatting_to_worksheet(writer, sheet_name, df, numeric_cols):
    """Applique le formatage français (virgules décimales) à une feuille Excel"""
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Formats français pour différents types de nombres
    formats = {
        'currency': workbook.add_format({
            'num_format': '#,##0.00 €',
            'font_name': 'Arial',
            'font_size': 10
        }),
        'decimal': workbook.add_format({
            'num_format': '#,##0.00',
            'font_name': 'Arial',
            'font_size': 10
        }),
        'percentage': workbook.add_format({
            'num_format': '0.00%',
            'font_name': 'Arial',
            'font_size': 10
        })
    }
    
    # Appliquer le formatage aux colonnes numériques
    for i, col in enumerate(df.columns):
        if col in numeric_cols:
            col_letter = chr(65 + i) if i < 26 else chr(65 + i//26 - 1) + chr(65 + i%26)  # A, B, C, etc. puis AA, AB...
            
            # Choisir le format selon le type de colonne
            if any(keyword in col.lower() for keyword in ['ca', 'chiffre', 'euro', '€']):  # Colonnes de chiffre d'affaires
                worksheet.set_column(f'{col_letter}:{col_letter}', 15, formats['currency'])
            elif any(keyword in col.lower() for keyword in ['score', 'note']) and not any(exclude in col.lower() for exclude in ['siret', 'agence']):  # Colonnes de score (0-1)
                worksheet.set_column(f'{col_letter}:{col_letter}', 10, formats['percentage'])
            else:  # Autres colonnes numériques
                worksheet.set_column(f'{col_letter}:{col_letter}', 12, formats['decimal'])

st.set_page_config(page_title="Analytics MOS", layout="wide")
st.title("Analytics MOS - Interface Utilisateur")

st.header("1. Upload des fichiers Excel")
col1, col2 = st.columns(2)
with col1:
    perf_file = st.file_uploader("Fichier de performance (Suivi MOS)", type=["xlsx"], key="perf")
with col2:
    interview_file = st.file_uploader("Fichier d'interview (NATIONAL MOS)", type=["xlsx"], key="interview")

if st.button("Lancer le traitement"):
    if not perf_file or not interview_file:
        st.error("Veuillez uploader les deux fichiers Excel.")
    else:
        files = {
            'performance': (perf_file.name, perf_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            'interview': (interview_file.name, interview_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        
        # Créer une barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Connexion au backend...")
            progress_bar.progress(10)
            
            # Test de connectivité d'abord
            test_resp = requests.get(f"{API_URL}/test", timeout=5)
            if test_resp.status_code != 200:
                st.error("❌ Backend non accessible. Vérifiez que le serveur backend est démarré.")
                st.stop()
            
            status_text.text("📤 Envoi des fichiers...")
            progress_bar.progress(20)
            
            # Traitement principal avec timeout étendu
            resp = requests.post(
                f"{API_URL}/process_excels", 
                files=files,
                timeout=300  # 5 minutes de timeout
            )
            
            progress_bar.progress(90)
            status_text.text("📊 Réception des données...")
            
            if resp.status_code == 200:
                response_data = resp.json()
                preview = response_data.get('preview', [])
                
                progress_bar.progress(100)
                status_text.text("✅ Traitement terminé avec succès !")
                
                # Afficher les informations de traitement
                if 'processing_time' in response_data:
                    st.info(f"⏱️ Temps de traitement: {response_data['processing_time']}")
                if 'total_records' in response_data:
                    st.info(f"📊 Nombre total d'enregistrements: {response_data['total_records']}")
                
                st.success("Traitement terminé ! Aperçu des données :")
                df_preview = pd.DataFrame(preview)
                st.dataframe(df_preview, use_container_width=True)
                
            elif resp.status_code == 504:
                progress_bar.progress(100)
                status_text.text("⚠️ Timeout détecté")
                st.warning("Le traitement a pris plus de temps que prévu. Cela peut arriver avec de gros fichiers ou l'analyse de sentiment.")
                st.info("💡 Conseils pour résoudre ce problème:")
                st.write("- Vérifiez que les fichiers ne sont pas trop volumineux")
                st.write("- Redémarrez le backend si nécessaire")
                st.write("- Réessayez le traitement")
                
            else:
                progress_bar.progress(100)
                status_text.text("❌ Erreur de traitement")
                error_msg = "Erreur inconnue"
                try:
                    error_data = resp.json()
                    error_msg = error_data.get('error', resp.text)
                except:
                    error_msg = f"HTTP {resp.status_code}: {resp.text}"
                st.error(f"Erreur backend: {error_msg}")
                
        except requests.exceptions.Timeout:
            progress_bar.progress(100)
            status_text.text("⏰ Timeout de connexion")
            st.error("⏰ Le traitement a expiré. Cela peut arriver avec de gros fichiers.")
            st.info("💡 Solutions suggérées:")
            st.write("- Vérifiez que le backend fonctionne: http://localhost:4000/test")
            st.write("- Redémarrez le backend si nécessaire")
            st.write("- Réduisez la taille des fichiers si possible")
            
        except requests.exceptions.ConnectionError:
            progress_bar.progress(100)
            status_text.text("🔌 Erreur de connexion")
            st.error("🔌 Impossible de se connecter au backend.")
            st.info("💡 Vérifications:")
            st.write("- Le backend est-il démarré ? (python main.py dans le dossier backend)")
            st.write("- Le port 4000 est-il disponible ?")
            st.write("- Test de connectivité: http://localhost:4000/test")
            
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("❌ Erreur inattendue")
            st.error(f"Erreur inattendue : {e}")
            st.info("💡 Redémarrez le backend et réessayez.")
            
        # Nettoyer l'affichage après un délai
        import time
        time.sleep(2)
        progress_bar.empty()
        status_text.empty()

# Section pour visualiser les DataFrames avant fusion
st.header("2. Prévisualisation des DataFrames nettoyés")
st.info("📊 Visualisez les données après nettoyage et avant fusion pour vérifier la qualité des traitements")

# Sous-section pour afficher les DataFrames individuellement
if perf_file and interview_file:
    col_prev1, col_prev2 = st.columns(2)
    
    with col_prev1:
        if st.button("🔍 Voir DataFrame Performance nettoyé"):
            with st.spinner("Récupération du DataFrame Performance nettoyé..."):
                try:
                    # Envoyer les fichiers au backend pour obtenir le DataFrame nettoyé
                    files = {
                        'performance': (perf_file.name, perf_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        'interview': (interview_file.name, interview_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    }
                    resp = requests.post(f"{API_URL}/preview_performance", files=files)
                    if resp.status_code == 200:
                        data = resp.json()
                        df_perf = pd.DataFrame(data['data'])
                        
                        st.subheader("📈 DataFrame Performance (après nettoyage backend)")
                        st.write(f"**Dimensions :** {df_perf.shape[0]} lignes × {df_perf.shape[1]} colonnes")
                        st.write("**Colonnes disponibles :**")
                        st.write(df_perf.columns.tolist())
                        st.write("**Aperçu des données :**")
                        st.dataframe(df_perf.head(10), use_container_width=True)
                        
                        # Informations supplémentaires
                        if 'Année' in df_perf.columns:
                            years = df_perf['Année'].unique()
                            st.write(f"**Années présentes :** {sorted([y for y in years if pd.notna(y)])}")
                        if 'siret_agence' in df_perf.columns:
                            st.write(f"**Nombre de SIRET_AGENCE uniques :** {df_perf['siret_agence'].nunique()}")
                    else:
                        st.error(f"Erreur backend: {resp.json().get('error', resp.text)}")
                except Exception as e:
                    st.error(f"Erreur lors de la récupération du DataFrame Performance : {e}")
    
    with col_prev2:
        if st.button("🔍 Voir DataFrame Interview nettoyé"):
            with st.spinner("Récupération du DataFrame Interview nettoyé..."):
                try:
                    # Envoyer les fichiers au backend pour obtenir le DataFrame nettoyé
                    files = {
                        'performance': (perf_file.name, perf_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        'interview': (interview_file.name, interview_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    }
                    resp = requests.post(f"{API_URL}/preview_interview", files=files)
                    if resp.status_code == 200:
                        data = resp.json()
                        df_interview = pd.DataFrame(data['data'])
                        
                        st.subheader("💬 DataFrame Interview (après nettoyage backend)")
                        st.write(f"**Dimensions :** {df_interview.shape[0]} lignes × {df_interview.shape[1]} colonnes")
                        st.write("**Colonnes disponibles :**")
                        st.write(df_interview.columns.tolist())
                        st.write("**Aperçu des données :**")
                        st.dataframe(df_interview.head(10), use_container_width=True)
                        
                        # Informations supplémentaires
                        if 'Année' in df_interview.columns:
                            years = df_interview['Année'].unique()
                            st.write(f"**Années présentes :** {sorted([y for y in years if pd.notna(y)])}")
                        if 'siret_agence' in df_interview.columns:
                            st.write(f"**Nombre de SIRET_AGENCE uniques :** {df_interview['siret_agence'].nunique()}")
                        if 'Q11 - Qualité adéquation candidats' in df_interview.columns:
                            q11_count = df_interview['Q11 - Qualité adéquation candidats'].notna().sum()
                            st.write(f"**Réponses Q11 disponibles :** {q11_count}")
                    else:
                        st.error(f"Erreur backend: {resp.json().get('error', resp.text)}")
                except Exception as e:
                    st.error(f"Erreur lors de la récupération du DataFrame Interview : {e}")

# Section principale : DataFrames fusionnés
st.header("3. DataFrames fusionnés et exports")
st.info("📥 Visualisez et exportez les données fusionnées après traitement complet")

col3, col4, col5 = st.columns(3)

with col3:
    if st.button("👁️ Aperçu données principales"):
        with st.spinner("Récupération des données principales..."):
            try:
                resp = requests.get(f"{API_URL}/main_data")
                if resp.status_code == 200:
                    data = resp.json().get('data', [])
                    if data:
                        df = pd.DataFrame(data)
                        # Nettoyage strict : suppression des colonnes dupliquées (même nom exact) et des lignes dupliquées
                        df = df.loc[:, ~df.columns.duplicated(keep='first')]
                        df = df.T.drop_duplicates().T
                        df = df.drop_duplicates()
                        st.subheader("📊 Aperçu du DataFrame principal")
                        st.write(f"**Dimensions :** {df.shape[0]} lignes × {df.shape[1]} colonnes")
                        st.dataframe(df.head(), use_container_width=True)
                    else:
                        st.warning("Aucune donnée disponible.")
                else:
                    st.error(f"Erreur backend: {resp.text}")
            except Exception as e:
                st.error(f"Erreur lors de la récupération des données : {e}")

with col4:
    if st.button("📄 Télécharger en CSV"):
        with st.spinner("Export CSV en cours..."):
            try:
                resp = requests.get(f"{API_URL}/main_data")
                if resp.status_code == 200:
                    data = resp.json().get('data', [])
                    if data:
                        df = pd.DataFrame(data)
                        # Nettoyage strict : suppression des colonnes dupliquées (même nom exact) et des lignes dupliquées
                        df = df.loc[:, ~df.columns.duplicated(keep='first')]
                        df = df.T.drop_duplicates().T
                        df = df.drop_duplicates()
                        csv_data = df.to_csv(index=False, decimal=',', sep=';')
                        st.download_button(
                            label="⬇️ Télécharger le fichier CSV",
                            data=csv_data,
                            file_name="analytics_mos_dataframe_principal.csv",
                            mime="text/csv"
                        )
                        st.success("✅ Fichier CSV généré avec format français (virgules décimales) !")
                    else:
                        st.warning("Aucune donnée disponible pour l'export.")
                else:
                    st.error(f"Erreur backend: {resp.text}")
            except Exception as e:
                st.error(f"Erreur lors de la génération du fichier CSV : {e}")

with col5:
    if st.button("📋 Télécharger en XLSX"):
        with st.spinner("Export XLSX en cours..."):
            try:
                resp = requests.get(f"{API_URL}/main_data")
                if resp.status_code == 200:
                    data = resp.json().get('data', [])
                    if data:
                        df = pd.DataFrame(data)
                        # Nettoyage strict : suppression des colonnes dupliquées (même nom exact) et des lignes dupliquées
                        df = df.loc[:, ~df.columns.duplicated(keep='first')]
                        df = df.T.drop_duplicates().T
                        df = df.drop_duplicates()
                        df_formatted, numeric_cols = format_dataframe_for_french_excel(df)
                        buffer = BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_formatted.to_excel(writer, sheet_name='DataFrame_Principal', index=False)
                            apply_french_formatting_to_worksheet(writer, 'DataFrame_Principal', df_formatted, numeric_cols)
                            
                            # Feuille avec statistiques
                            stats_data = {
                                'Métrique': [
                                    'Nombre total de lignes',
                                    'Nombre total de colonnes',
                                    'Lignes avec Q11 renseigné',
                                    'Lignes avec Raison recommandation',
                                    'Lignes avec Note Recommandation',
                                    'Années présentes',
                                    'SIRET uniques'
                                ],
                                'Valeur': [
                                    len(df),
                                    len(df.columns),
                                    df.get('Q11 - Qualité adéquation candidats', pd.Series()).notna().sum() if 'Q11 - Qualité adéquation candidats' in df.columns else 0,
                                    df.get('Raison recommandation Manpower', pd.Series()).notna().sum() if 'Raison recommandation Manpower' in df.columns else 0,
                                    df.get('Note Recommandation Manpower', pd.Series()).notna().sum() if 'Note Recommandation Manpower' in df.columns else 0,
                                    ', '.join(map(str, sorted(df['Année'].unique()))) if 'Année' in df.columns else 'N/A',
                                    df['No Siret'].nunique() if 'No Siret' in df.columns else 0
                                ]
                            }
                            stats_df = pd.DataFrame(stats_data)
                            # Nettoyage stats : suppression doublons lignes/colonnes
                            stats_df = stats_df.drop_duplicates()
                            stats_df = stats_df.loc[:, ~stats_df.columns.duplicated()]
                            stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
                            
                            # Feuille avec les colonnes importantes seulement
                            important_cols = ['Année', 'No Siret', 'code agence', 'agence', 'raison sociale',
                                            'Q7 - Contribution objectifs et performances', 'Q11 - Qualité adéquation candidats', 
                                            'Q12 - Réactivité', 'Q16 - Prestation administrative', 'Q21 - Qualité expertise',
                                            'Note Recommandation Manpower', 'Raison recommandation Manpower']
                            
                            available_important_cols = [col for col in important_cols if col in df.columns]
                            if available_important_cols:
                                df_important = df[available_important_cols]
                                # Nettoyage important : suppression doublons lignes/colonnes
                                df_important = df_important.drop_duplicates()
                                df_important = df_important.loc[:, ~df_important.columns.duplicated()]
                                df_important_formatted, important_numeric_cols = format_dataframe_for_french_excel(df_important)
                                df_important_formatted.to_excel(writer, sheet_name='Colonnes_Principales', index=False)
                                apply_french_formatting_to_worksheet(writer, 'Colonnes_Principales', df_important_formatted, important_numeric_cols)
                            
                            # Feuille avec analyse sentiment si disponible
                            sentiment_cols = [col for col in df.columns if 'Sentiment' in col or 'Score' in col]
                            if sentiment_cols:
                                base_cols = ['No Siret', 'code agence', 'agence']
                                available_base_cols = [col for col in base_cols if col in df.columns]
                                df_sentiment = df[available_base_cols + sentiment_cols]
                                # Nettoyage sentiment : suppression doublons lignes/colonnes
                                df_sentiment = df_sentiment.drop_duplicates()
                                df_sentiment = df_sentiment.loc[:, ~df_sentiment.columns.duplicated()]
                                df_sentiment_formatted, sentiment_numeric_cols = format_dataframe_for_french_excel(df_sentiment)
                                df_sentiment_formatted.to_excel(writer, sheet_name='Analyse_Sentiment', index=False)
                                apply_french_formatting_to_worksheet(writer, 'Analyse_Sentiment', df_sentiment_formatted, sentiment_numeric_cols)
                        
                        buffer.seek(0)
                        
                        st.download_button(
                            label="⬇️ Télécharger le fichier XLSX",
                            data=buffer.getvalue(),
                            file_name="analytics_mos_dataframe_principal.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success("✅ Fichier XLSX généré avec formatage français (virgules décimales) !")
                        st.info("📋 Le fichier contient 4 feuilles :\n"
                               "• **DataFrame_Principal** : Toutes les données\n"
                               "• **Statistiques** : Métriques et résumé\n"
                               "• **Colonnes_Principales** : Colonnes critiques seulement\n"
                               "• **Analyse_Sentiment** : Colonnes de sentiment (si disponibles)")
                        
                    else:
                        st.warning("Aucune donnée disponible pour l'export. Veuillez d'abord traiter les fichiers.")
                else:
                    st.error(f"Erreur backend: {resp.text}")
            except Exception as e:
                st.error(f"Erreur lors de la génération du fichier XLSX : {e}")

# Footer
st.markdown("---")
st.markdown("**Analytics MOS v2** - Interface utilisateur pour l'analyse des données MOS")
st.markdown("🔧 Format décimal : **Virgule française** pour tous les exports CSV et XLSX")
