"""Chargement des extractions Negolux et corrections communes aux scripts de prévision."""
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# Régime stable post-Covid, utilisé pour la saisonnalité et les backtests
ANNEES_STABLES = [2023, 2024, 2025]
# Derniers mois dont les avoirs ne sont pas encore tous saisis dans l'ERP
MOIS_A_CORRIGER = 3


def parametres():
    return json.loads((DATA / "extraction.json").read_text(encoding="utf-8"))


def charger_mensuel():
    df = pd.read_csv(DATA / "ca_mensuel.csv")
    df.index = pd.PeriodIndex(df.pop("periode"), freq="M")
    return df


def avoirs_a_venir(df):
    """Avoirs (en €) qui manquent encore sur les derniers mois.

    Un avoir est saisi plusieurs semaines après la commande : sur les derniers mois,
    le taux d'avoir (avoir / CA brut) est anormalement bas. On le ramène au taux
    du même mois de l'année précédente, qui lui est complet.
    """
    manque = {}
    for p in df.index[-MOIS_A_CORRIGER:]:
        ref = df.loc[p - 12]
        taux_ref = ref.avoir / ref.ca_brut
        taux = df.loc[p, "avoir"] / df.loc[p, "ca_brut"]
        manque[p] = max(0.0, taux_ref - taux) * df.loc[p, "ca_brut"]
    return pd.Series(manque)


def serie_corrigee():
    """CA mensuel (€) corrigé des avoirs à venir, mois en cours extrapolé à un mois complet.

    Renvoie (série, avoirs à venir par mois, paramètres d'extraction).
    """
    params = parametres()
    df = charger_mensuel()
    manque = avoirs_a_venir(df)
    ca = df.ca - manque.reindex(df.index, fill_value=0.0)
    if params["mois_en_cours_partiel"]:
        # Part du mois déjà écoulée, mesurée sur le même mois de l'année précédente
        dernier = ca.index[-1]
        part_ecoulee = params["ca_mois_en_cours_n1_a_date"] / df.loc[dernier - 12, "ca"]
        ca.loc[dernier] = ca.loc[dernier] / part_ecoulee
    return ca, manque, params


def poids_saisonniers(ca):
    """Part de chaque mois (1 à 12) dans le CA annuel, sur les années stables."""
    stable = ca[ca.index.year.isin(ANNEES_STABLES)]
    return stable.groupby(stable.index.month).sum() / stable.sum()
