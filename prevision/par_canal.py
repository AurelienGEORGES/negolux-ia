"""Prévision canal par canal (bottom-up) : atterrissage de l'année en cours et année suivante.

Usage : python prevision/par_canal.py
"""
import pandas as pd

from commun import DATA, serie_corrigee

PLAFOND_RESTE = 0.30  # borne du rythme appliqué au reste de l'année en cours
AMORTI = 0.5          # part du rythme récent conservée l'année suivante (retour à la moyenne)
PLAFOND_N1 = 0.20     # borne de croissance par canal l'année suivante

COLONNES = ["ca_n1_total", "ca_n1_a_date", "ca_n_a_date", "ca_recent_n1", "ca_recent_n"]


def prevision_par_canal():
    df = pd.read_csv(DATA / "ca_canaux.csv", index_col="canal")
    total = df.loc["TOTAL", COLONNES].astype(float)
    df = df.drop("TOTAL")
    df.loc["Autres canaux", COLONNES] = total - df[COLONNES].sum()
    df.loc["Autres canaux", "nouveau"] = 0
    df[COLONNES] = df[COLONNES].astype(float)
    nouveau = df.nouveau.astype(bool)

    # Même correction d'avoirs à venir que la série mensuelle, répartie au prorata du CA
    _, manque, _ = serie_corrigee()
    df["ca_n_a_date"] *= 1 - manque.sum() / total.ca_n_a_date

    reste_n1 = df.ca_n1_total - df.ca_n1_a_date
    df["g_a_date"] = df.ca_n_a_date / df.ca_n1_a_date - 1
    df["g_recent"] = df.ca_recent_n / df.ca_recent_n1 - 1

    df["atterrissage_n"] = df.ca_n_a_date + reste_n1 * (1 + df.g_recent.clip(-PLAFOND_RESTE, PLAFOND_RESTE))
    # Canal ouvert en cours d'année précédente : pas de base N-1, on extrapole
    # la période récente avec le poids saisonnier « reste de l'année / période récente »
    ratio_reste = (total.ca_n1_total - total.ca_n1_a_date) / total.ca_recent_n1
    df.loc[nouveau, "atterrissage_n"] = df.ca_n_a_date + df.ca_recent_n * ratio_reste

    df["g_n_plus_1"] = (AMORTI * df.g_recent).clip(-PLAFOND_N1, PLAFOND_N1)
    df.loc[nouveau, "g_n_plus_1"] = PLAFOND_N1  # effet année pleine, borné
    df["ca_n_plus_1"] = df.atterrissage_n * (1 + df.g_n_plus_1)
    return df


if __name__ == "__main__":
    df = prevision_par_canal()
    vue = df[["ca_n1_total", "ca_n_a_date", "g_a_date", "g_recent", "atterrissage_n", "g_n_plus_1", "ca_n_plus_1"]].copy()
    vue.loc["TOTAL"] = vue.sum()
    vue.loc["TOTAL", ["g_a_date", "g_recent", "g_n_plus_1"]] = float("nan")
    for c in ["g_a_date", "g_recent", "g_n_plus_1"]:
        vue[c] = (vue[c] * 100).round(1)
    for c in ["ca_n1_total", "ca_n_a_date", "atterrissage_n", "ca_n_plus_1"]:
        vue[c] = (vue[c] / 1000).round(0)
    pd.set_option("display.width", 200)
    print("Montants en k€ TTC, croissances en %\n")
    print(vue.to_string())
