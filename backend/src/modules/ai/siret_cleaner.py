import pandas as pd

def clean_siret(siret):
    if pd.isnull(siret):
        return ''
    s = str(siret).strip()
    if len(s) < 14:
        s = s.zfill(14)
    return s 