from textblob import TextBlob

def analyze_sentiment(text):
    if not text or str(text).strip() == '':
        return 'Pas de réponse', 5  # Neutre par défaut
    blob = TextBlob(str(text))
    polarity = blob.sentiment.polarity  # [-1, 1]
    # Mapping du score sur [0, 10]
    score = int(round((polarity + 1) * 5))
    # Attribution du label
    if score <= 2:
        label = 'very_negative'
    elif score <= 5:
        label = 'negative'
    elif score <= 7:
        label = 'neutral'
    elif score <= 8:
        label = 'positive'
    else:
        label = 'very_positive'
    return label, score 