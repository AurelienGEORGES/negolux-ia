import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")

# CA net (k€ TTC) par mois, source : Negolux stats_commandes (ca = ca_brut - remises - avoirs)
raw = {
    2020: [808.6, 547.1, 1152.6, 5321.6, 4723.8, 2720.5, 4156.5, 3146.4, 867.1, 452.3, 853.6, 561.4],
    2021: [858.4, 1357.8, 2479.3, 2975.1, 3177.9, 3093.2, 3031.6, 1342.5, 774.2, 750.2, 905.9, 487.2],
    2022: [1155.2, 1081.0, 1140.6, 1969.9, 3690.0, 2353.4, 1763.3, 1407.2, 782.3, 537.7, 943.0, 497.8],
    2023: [850.9, 770.2, 917.5, 1399.1, 1540.0, 1848.2, 2582.4, 1131.2, 552.4, 627.8, 706.3, 659.9],
    2024: [938.6, 697.1, 861.7, 1305.9, 1615.3, 1542.7, 2280.8, 1416.4, 683.2, 647.5, 740.4, 846.6],
    2025: [840.9, 876.5, 1059.3, 1372.0, 1546.5, 1815.4, 2232.5, 1217.8, 543.0, 557.7, 780.0, 671.6],
}
# 2026 : jan-août constatés ; juil-août corrigés des avoirs non encore saisis
# (taux d'avoir 2025 mûr : juil 4,48 %, août 6,20 % ; 2026 : 4,00 %, 3,44 %)
m2026 = [986.0, 762.4, 1388.9, 1504.9, 1641.0, 1944.1, 2418.6 - 12.0, 1181.9 - 33.8]
# Septembre 2026 : 1-23 sept = 434,7 k€, -18,1 k€ d'avoirs à venir, extrapolé
# avec le ratio 2025 (1-23 sept 2025 = 439,6 / 543,0 = 81,0 % du mois)
sep26 = (434.7 - 18.1) / (439.6 / 543.0)
m2026.append(sep26)

s = []
for y in sorted(raw):
    for m, v in enumerate(raw[y], 1):
        s.append((pd.Timestamp(y, m, 1), v))
for m, v in enumerate(m2026, 1):
    s.append((pd.Timestamp(2026, m, 1), v))
ts = pd.Series(dict(s)).asfreq("MS")

annual = ts.groupby(ts.index.year).sum()
print("CA annuel (M€):")
print((annual / 1000).round(2).to_string())
print(f"Sept 2026 estimé : {sep26:.1f} k€")

# ---------- Saisonnalité (régime stable 2023-2025) ----------
stable = ts["2023":"2025"]
shares = stable.groupby(stable.index.month).sum() / stable.sum()
print("\nPoids saisonniers 2023-2025 (%):")
print((shares * 100).round(1).to_string())
share_jan_sep = shares.loc[1:9].sum()
print(f"Part jan-sept : {share_jan_sep*100:.1f} %")

ytd26 = ts["2026-01":"2026-09"].sum()
ytd25 = ts["2025-01":"2025-09"].sum()
ytd24 = ts["2024-01":"2024-09"].sum()
print(f"\nJan-sept 2026 corrigé : {ytd26:.0f} k€  vs 2025 : {ytd25:.0f} k€ -> {100*(ytd26/ytd25-1):+.1f} %")

# ---------- Estimation atterrissage 2026 ----------
q4_25 = ts["2025-10":"2025-12"].sum()
q4_24 = ts["2024-10":"2024-12"].sum()
land_A = ytd26 + q4_25 * 1.037  # Q4 = Q4 2025 x dynamique T3 (+3,7 %)
land_B = ytd26 / share_jan_sep   # méthode des poids saisonniers
land_C = ytd26 + q4_25           # Q4 plat
print(f"\nAtterrissage 2026 : Q4 plat {land_C:.0f} | Q4 x T3 {land_A:.0f} | poids saisonniers {land_B:.0f}")

# ---------- Holt-Winters ----------
def hw_forecast(series, start, horizon, damped=True):
    y = series[start:]
    model = ExponentialSmoothing(
        y, trend="add", damped_trend=damped, seasonal="mul", seasonal_periods=12,
        initialization_method="estimated",
    ).fit(optimized=True)
    return model.forecast(horizon), model

res = {}
for start in ["2022-01", "2023-01"]:
    fc, mdl = hw_forecast(ts, start, 15)
    y26 = ts["2026-01":"2026-09"].sum() + fc["2026-10":"2026-12"].sum()
    y27 = fc["2027"].sum()
    res[start] = (y26, y27)
    print(f"\nHolt-Winters (depuis {start}, tendance amortie) : 2026 = {y26:.0f} k€ ; 2027 = {y27:.0f} k€ "
          f"(phi={mdl.params.get('damping_trend', float('nan')):.2f}, niveau fin={mdl.level.iloc[-1]:.0f}, pente={mdl.trend.iloc[-1]:.1f} k€/mois)")

# ---------- Backtests : prévoir l'année N+1 avec les données à fin sept N ----------
print("\nBacktests (prévision N+1 à fin septembre N) :")
bt = []
for N in [2023, 2024, 2025]:
    hist = ts[: f"{N}-09"]
    actual_next = annual[N + 1] if N + 1 in annual.index and N + 1 < 2026 else None
    # Méthode naïve saisonnière x croissance YTD
    g = hist[f"{N}-01":f"{N}-09"].sum() / hist[f"{N-1}-01":f"{N-1}-09"].sum() - 1
    land = hist[f"{N}-01":f"{N}-09"].sum() + ts[f"{N-1}-10":f"{N-1}-12"].sum() * (1 + g)
    naive = land * (1 + g)
    flat = land
    fc, _ = hw_forecast(hist, f"{N-2}-01", 15)
    hw = fc[str(N + 1)].sum()
    row = dict(N=N, croissance_ytd=round(100 * g, 1), naive_x_g=round(naive), plat=round(flat), hw=round(hw),
               reel=round(actual_next) if actual_next else None)
    bt.append(row)
print(pd.DataFrame(bt).to_string(index=False))

# ---------- Scénarios 2027 ----------
base26 = land_A
print(f"\nBase 2026 retenue : {base26:.0f} k€ ({100*(base26/annual[2025]-1):+.1f} % vs 2025)")
for name, g in [("Prudent", -0.03), ("Central", 0.035), ("Haut", 0.08)]:
    print(f"  {name:8s} {g*100:+.1f} % -> 2027 = {base26*(1+g):.0f} k€")

# Profil mensuel 2027 (scénario central) avec les poids saisonniers
central27 = base26 * 1.035
prof = (shares * central27).round(0)
prof.index = [f"2027-{m:02d}" for m in prof.index]
print("\nProfil mensuel 2027 (central, k€):")
print(prof.to_string())
