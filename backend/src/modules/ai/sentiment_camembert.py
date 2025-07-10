#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse de sentiment avancé avec CamemBERT
Optimisé pour les commentaires clients longs sur les services RH
"""

import logging
import re
import pandas as pd
from typing import Tuple, List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import warnings
warnings.filterwarnings("ignore")

class CamemBERTSentimentAnalyzer:
    """
    Analyseur de sentiment spécialisé pour les commentaires clients RH
    Utilise CamemBERT pour une analyse précise du français
    """
    
    def __init__(self):
        # Utilisation d'un modèle plus stable avec tokenizer compatible
        self.model_name = "nlptown/bert-base-multilingual-uncased-sentiment"  
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.max_length = 512  
        self.setup_model()
        
        # Échelle de sentiment selon ULTIMATE PROMPT
        self.sentiment_scale = {
            'very_negative': (0, 2, 'Opinion extrêmement défavorable'),
            'negative': (2, 5, 'Opinion défavorable'),
            'neutral': (5, 7, 'Opinion mitigée ou indifférente'),
            'positive': (7, 8, 'Opinion favorable'),
            'very_positive': (8, 10, 'Opinion très favorable / enthousiaste')
        }
        
        # Mots-clés contextuels pour ajuster l'analyse
        self.context_keywords = {
            'very_negative': ['catastrophique', 'inacceptable', 'désastreux', 'horrible', 'nul', 'très mauvais'],
            'negative': ['mauvais', 'décevant', 'insuffisant', 'problème', 'insatisfait', 'mécontentement'],
            'neutral': ['moyen', 'correct', 'acceptable', 'normal', 'standard', 'convenable'],
            'positive': ['bon', 'satisfait', 'content', 'bien', 'apprécie', 'recommande'],
            'very_positive': ['excellent', 'parfait', 'formidable', 'exceptionnel', 'remarquable', 'fantastique']
        }
    
    def setup_model(self):
        """Initialise le modèle CamemBERT"""
        try:
            logging.info("🤖 Initialisation du modèle de sentiment multilingue...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Configuration pipeline optimisée
            device = 0 if torch.cuda.is_available() else -1
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=device,
                max_length=self.max_length,
                truncation=True,
                padding=True
            )
            
            logging.info(f"✅ Modèle de sentiment chargé avec succès (device: {'GPU' if device >= 0 else 'CPU'})")
            
        except Exception as e:
            logging.error(f"❌ Erreur lors du chargement du modèle: {e}")
            raise Exception(f"Impossible de charger le modèle de sentiment: {e}")
    
    def preprocess_text(self, text: str) -> str:
        """
        Préprocessing optimisé pour les commentaires clients
        """
        # Gérer les cas None
        if text is None:
            return ""
            
        # Gérer les listes/tuples
        if isinstance(text, (list, tuple)):
            if len(text) > 0:
                text = str(text[0])  # Prendre le premier élément
            else:
                return ""
                
        # Gérer les types pandas/numpy
        elif hasattr(text, 'iloc') or hasattr(text, '__array__'):  # Series ou array
            if hasattr(text, 'iloc') and len(text) > 0:  # Series non vide
                text = str(text.iloc[0])  # Prendre le premier élément
            elif hasattr(text, '__len__') and len(text) > 0:  # Array non vide
                text = str(text[0])  # Prendre le premier élément
            else:
                return ""
        
        # Convertir explicitement en string pour éviter les erreurs avec arrays
        text_str = str(text) if text is not None else ''
        
        if (pd.isna(text) or 
            text_str.strip() == '' or
            text_str == 'nan'):
            return ""
        
        text = text_str.strip()
        
        # Nettoyage basique
        text = re.sub(r'\s+', ' ', text)  # Normaliser les espaces
        text = re.sub(r'[^\w\s\.,!?;:()\'-]', '', text)  # Garder la ponctuation utile
        
        # Gestion des textes très longs pour les recommandations
        if len(text) > self.max_length * 2:  # Si très long, extraire les phrases clés
            sentences = re.split(r'[.!?]+', text)
            # Garder les phrases les plus expressives (début, fin, et celles avec mots-clés)
            key_sentences = []
            key_sentences.extend(sentences[:2])  # Début
            key_sentences.extend(sentences[-2:])  # Fin
            
            # Sentences avec mots-clés émotionnels
            emotion_words = ['satisfait', 'content', 'déçu', 'excellent', 'mauvais', 'recommande', 'apprécie']
            for sentence in sentences[2:-2]:
                if any(word in sentence.lower() for word in emotion_words):
                    key_sentences.append(sentence)
            
            text = '. '.join(key_sentences[:8])  # Limiter à 8 phrases max
        
        return text[:self.max_length * 3]  # Sécurité supplémentaire
    
    def analyze_with_context(self, text: str) -> Tuple[str, float, float]:
        """
        Analyse avec prise en compte du contexte métier
        Returns: (sentiment_label, base_score, confidence)
        """
        try:
            # Prédiction du modèle multilingue
            result = self.pipeline(text)[0]
            base_confidence = result['score']
            label = result['label']

            # Mapping des labels du modèle nlptown (1-5 stars) vers scores 0-10
            star_mapping = {
                '1 star': 1.0,   # Très négatif
                '2 stars': 3.0,  # Négatif
                '3 stars': 5.0,  # Neutre
                '4 stars': 7.5,  # Positif
                '5 stars': 9.0   # Très positif
            }

            # Score de base selon le label
            base_score = star_mapping.get(label, 5.0)

            # Ajustement contextuel avec mots-clés
            text_lower = text.lower()
            context_boost = 0

            # Limiter le boost contextuel à ±1.0
            context_boost = max(-1.0, min(1.0, context_boost))

            # Détection de connecteurs de contraste
            contrast_words = ['mais', 'cependant', 'toutefois', 'malgré', 'en revanche']
            if any(word in text_lower for word in contrast_words):
                context_boost -= 0.5

            # Neutralisation si polarité mixte détectée
            has_positive = any(word in text_lower for word in self.context_keywords['positive'])
            has_negative = any(word in text_lower for word in self.context_keywords['negative'])
            if has_positive and has_negative:
                context_boost = 0

            # Application du boost contextuel selon les mots-clés
            for sentiment_type, keywords in self.context_keywords.items():
                keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
                if keyword_count > 0:
                    if sentiment_type == 'very_positive':
                        context_boost += keyword_count * 0.8
                    elif sentiment_type == 'positive':
                        context_boost += keyword_count * 0.4
                    elif sentiment_type == 'negative':
                        context_boost -= keyword_count * 0.4
                    elif sentiment_type == 'very_negative':
                        context_boost -= keyword_count * 0.8

            # Calcul du score final
            final_score = base_score + context_boost
            final_score = max(0, min(10, final_score))  # Clamp entre 0 et 10

            # Détermination du label final
            for sentiment_type, (min_val, max_val, _) in self.sentiment_scale.items():
                if min_val <= final_score <= max_val:
                    return sentiment_type, final_score, base_confidence

            return 'neutral', final_score, base_confidence

        except Exception as e:
            logging.error(f"Erreur analyse contextuelle: {e}")
            return 'neutral', 5.0, 0.5
    
    def analyze_sentiment_advanced(self, text: str) -> Tuple[str, float]:
        """
        Méthode principale d'analyse de sentiment
        Optimisée pour les commentaires longs de recommandation
        """
        # Cas spéciaux - gérer les types non-string
        if text is None:
            return 'NEUTRE', 5.0
            
        # Gérer les listes/tuples
        if isinstance(text, (list, tuple)):
            if len(text) > 0:
                text = str(text[0])  # Prendre le premier élément
            else:
                return 'NEUTRE', 5.0
                
        # Gérer les types pandas/numpy
        elif hasattr(text, 'iloc') or hasattr(text, '__array__'):  # Series ou array
            if hasattr(text, 'iloc') and len(text) > 0:  # Series non vide
                text = str(text.iloc[0])  # Prendre le premier élément
            elif hasattr(text, '__len__') and len(text) > 0:  # Array non vide
                text = str(text[0])  # Prendre le premier élément
            else:
                return 'NEUTRE', 5.0
        
        # Convertir en string et vérifier les cas spéciaux
        text_str = str(text) if text is not None else ''
        
        # Vérifier les cas spéciaux après conversion en string
        if (pd.isna(text) or 
            text_str.strip() == '' or 
            text_str == 'Pas de réponse' or
            text_str == 'nan'):
            return 'NEUTRE', 5.0
        
        # Préprocessing
        clean_text = self.preprocess_text(text)
        if not clean_text:
            return 'NEUTRE', 5.0
        
        # Analyse principale
        sentiment_type, score, confidence = self.analyze_with_context(clean_text)
        
        # Mapping vers les labels attendus
        label_mapping = {
            'very_negative': 'TRÈS NÉGATIF',
            'negative': 'NÉGATIF', 
            'neutral': 'NEUTRE',
            'positive': 'POSITIF',
            'very_positive': 'TRÈS POSITIF'
        }
        
        final_label = label_mapping.get(sentiment_type, 'NEUTRE')
        final_score = round(score, 1)
        
        # Log pour les analyses importantes (recommandations longues)
        if len(clean_text) > 100:
            logging.info(f"📝 Analyse longue: '{clean_text[:100]}...' → {final_label} ({final_score})")
        
        return final_label, final_score
    
    def batch_analyze(self, texts: List[str], batch_size: int = 10, progress_callback=None) -> List[Tuple[str, float]]:
        """
        Analyse par batch optimisée pour éviter les timeouts
        """
        if not texts:
            return []
            
        results = []
        total = len(texts)
        
        # Traitement par petits lots pour éviter la surcharge mémoire
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_results = []
            
            for text in batch:
                try:
                    sentiment, score = self.analyze_sentiment_advanced(text)
                    batch_results.append((sentiment, score))
                except Exception as e:
                    logging.error(f"Erreur batch analysis: {e}")
                    batch_results.append(('NEUTRE', 5.0))
            
            results.extend(batch_results)
            
            # Callback de progression
            if progress_callback:
                progress = min(100, int((len(results) / total) * 100))
                progress_callback(progress, len(results), total)
            
            # Log de progression
            if i % (batch_size * 5) == 0 or len(results) == total:
                logging.info(f"🔄 Analyse sentiment: {len(results)}/{total} ({int((len(results)/total)*100)}%)")
        
        return results
    
    def get_model_info(self) -> dict:
        """Retourne les informations du modèle"""
        return {
            'model_name': self.model_name,
            'max_length': self.max_length,
            'device': 'GPU' if torch.cuda.is_available() else 'CPU',
            'sentiment_scale': self.sentiment_scale
        }

# Instance globale pour réutilisation
_analyzer_instance = None

def get_sentiment_analyzer():
    """Factory pour obtenir l'instance du sentiment analyzer"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CamemBERTSentimentAnalyzer()
    return _analyzer_instance

def analyze_sentiment_camembert(text: str) -> Tuple[str, float]:
    """
    Interface simplifiée pour l'analyse de sentiment
    Compatible avec l'API existante
    """
    analyzer = get_sentiment_analyzer()
    return analyzer.analyze_sentiment_advanced(text)
