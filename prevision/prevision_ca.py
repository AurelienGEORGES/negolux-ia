"""Prévision du CA annuel Negolux : atterrissage de l'année en cours, backtests et scénarios N+1.

Usage : python prevision/prevision_ca.py
"""
import warnings

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from commun import ANNEES_STABLES, poids_saisonniers, serie_corrigee
from par_canal import prevision_par_canal

warnings.filterwarnings("ignore")  # avertissements de convergence de statsmodels


def k(x):
    return f"{x / 1000:,.0f} k€".replace(",", " ")


def pct(x):
    return f"{x * 100:+.1f} %"


def atterrissage(ca, annee, dernier_mois):
    """CA de l'année = réalisé à date + reste de l'année N-1 au rythme des 3 derniers mois."""
    fin = pd.Period(f"{annee}-{dernier_mois:02d}", "M")
    a_date = ca[f"{annee}-01":str(fin)].sum()
    a_date_n1 = ca[f"{annee - 1}-01":str(fin - 12)].sum()
    recent = ca[str(fin - 2):str(fin)].sum()
    recent_n1 = ca[str(fin - 14):str(fin - 12)].sum()
    g_a_date = a_date / a_date_n1 - 1
    g_recent = recent / recent_n1 - 1
    reste_n1 = ca[str(fin - 11):f"{annee - 1}-12"].sum()
    return a_date + reste_n1 * (1 + g_recent), g_a_date, g_recent


def holt_winters(ca, debut, fin, horizon):
    """Lissage exponentiel : tendance additive amortie, saisonnalité multiplicative."""
    y = ca[debut:fin].to_timestamp().asfreq("MS")
    modele = ExponentialSmoothing(
        y, trend="add", damped_trend=True, seasonal="mul", seasonal_periods=12,
        initialization_method="estimated",
    ).fit(optimized=True)
    prev = modele.forecast(horizon)
    prev.index = prev.index.to_period("M")
    return prev


def main():
    ca, manque, params = serie_corrigee()
    annee = int(params["date_arret"][:4])
    dernier_mois = ca.index[-1].month
    cible = annee + 1

    print(f"Données au {params['date_arret']} — {params['unite']}")
    print(f"Avoirs à venir retirés : {k(manque.sum())} ({', '.join(f'{p}: {k(v)}' for p, v in manque.items())})")
    print(f"{ca.index[-1]} extrapolé à un mois complet : {k(ca.iloc[-1])}\n")

    annuel = ca.groupby(ca.index.year).sum()
    print("CA annuel :")
    for a, v in annuel.items():
        suffixe = f" (jan-{dernier_mois:02d}, corrigé)" if a == annee else ""
        print(f"  {a} : {k(v)}{suffixe}")

    poids = poids_saisonniers(ca)
    print(f"\nPoids saisonniers {ANNEES_STABLES[0]}-{ANNEES_STABLES[-1]} (%) :")
    print("  " + "  ".join(f"{m:02d}:{p * 100:.1f}" for m, p in poids.items()))

    # ---------- Atterrissage de l'année en cours ----------
    land, g_a_date, g_recent = atterrissage(ca, annee, dernier_mois)
    a_date = ca[str(annee)].sum()
    land_poids = a_date / poids.loc[1:dernier_mois].sum()
    canaux = prevision_par_canal()
    land_canaux = canaux.atterrissage_n.sum()
    print(f"\nCroissance à date : {pct(g_a_date)} ; 3 derniers mois : {pct(g_recent)}")
    print(f"Atterrissage {annee} : {k(land)} (retenu) | poids saisonniers {k(land_poids)} | canal par canal {k(land_canaux)}")

    # ---------- Backtests : prévoir N+1 avec les données à fin <dernier_mois> N ----------
    print(f"\nBacktests (prévision N+1 faite à fin {dernier_mois:02d}/N) :")
    lignes = []
    for n in ANNEES_STABLES:
        histo = ca[: f"{n}-{dernier_mois:02d}"]
        l_n, g_n, _ = atterrissage(histo, n, dernier_mois)
        hw = holt_winters(histo, f"{n - 2}-01", f"{n}-{dernier_mois:02d}", 12 - dernier_mois + 12)
        reel = annuel[n + 1] if n + 1 < annee else land
        prev = {"persistance": l_n, "tendance": l_n * (1 + g_n), "holt_winters": hw[str(n + 1)].sum()}
        lignes.append({"N+1": n + 1 if n + 1 < annee else f"{n + 1} (estimé)", "réel": round(reel / 1000),
                       **{f"{m}": f"{round(v / 1000)} ({pct(v / reel - 1)})" for m, v in prev.items()}})
    print(pd.DataFrame(lignes).to_string(index=False))

    # ---------- Scénarios N+1 ----------
    hw = holt_winters(ca, f"{ANNEES_STABLES[0]}-01", None, 12 - dernier_mois + 12)
    scenarios = {
        "bas (Holt-Winters)": hw[str(cible)].sum(),
        "persistance": land,
        "central (canal par canal)": canaux.ca_n_plus_1.sum(),
        "haut (croissance à date prolongée)": land * (1 + g_a_date),
    }
    print(f"\nScénarios {cible} :")
    for nom, v in scenarios.items():
        print(f"  {nom:36s} {k(v):>12s}  ({pct(v / land - 1)} vs {annee}e)")

    central = scenarios["central (canal par canal)"]
    profil = poids * central
    print(f"\nProfil mensuel {cible} (central) :")
    print("  " + "  ".join(f"{m:02d}:{v / 1000:,.0f}" for m, v in profil.items()))
    trimestres = [profil.loc[i:i + 2].sum() for i in (1, 4, 7, 10)]
    print("  Trimestres : " + " | ".join(f"T{i + 1} {k(v)}" for i, v in enumerate(trimestres)))


if __name__ == "__main__":
    main()
