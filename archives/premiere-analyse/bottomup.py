import pandas as pd, numpy as np
# k€ CA net TTC — Negolux stats_commandes, regroupement_places
# canal: (CA 2025 total, CA 2025 au 23/09, CA 2026 au 23/09, croissance T3 2026 (1/07-23/09) vs T3 2025)
d = {
 "Vente privée FR":      (2583.2, 2194.3, 3267.6, 0.217),
 "Maisons du Monde":     (2319.4, 1909.3, 1901.7, -0.080),
 "Amazon":               (2218.1, 1806.7, 1274.7, -0.251),
 "ConceptUsine":         (1771.4, 1587.3, 1321.2, -0.113),
 "Leroy Merlin":         (1630.0, 1503.5, 1222.8, -0.146),
 "But":                  (463.3,  347.2,  257.8, -0.454),
 "ManoMano":             (352.0,  292.3,  340.0, -0.002),
 "Groupon":              (317.4,  228.3,  355.6, 0.827),
 "Cdiscount":            (301.9,  234.9,  228.5, -0.149),
 "Vente Unique":         (249.6,  201.0,  334.0, 0.529),
 "Showroomprivé":        (243.3,  205.9,  450.7, 1.300),
 "Castorama":            (195.1,  181.6,  243.7, 0.155),
 "Brico Marché":         (154.6,  143.7,  242.9, 0.697),
 "Nature & Découvertes": (54.3,   6.3,    235.5, None),  # canal ouvert fin 2025
 "Leclerc":              (38.1,   36.0,   79.1, 0.951),
}
TOT25, YTD25, YTD26 = 13513.1, 11400.4, 12262.6
top = pd.DataFrame(d, index=["ca25","ytd25","ytd26","gq3"]).T
autres = dict(ca25=TOT25-top.ca25.sum(), ytd25=YTD25-top.ytd25.sum(), ytd26=YTD26-top.ytd26.sum())
autres["gq3"] = autres["ytd26"]/autres["ytd25"]-1
top.loc["Autres canaux"] = pd.Series(autres)
df = top.astype(float)
df["reste25"] = df.ca25 - df.ytd25
df["g_ytd"] = df.ytd26/df.ytd25 - 1
# momentum récent du canal (T3), à défaut YTD
df["g_q3"] = df.gq3.fillna(np.nan)
# Nature & Découvertes : fin 2025 = lancement ; on prend le rythme T3 2026 (100 k€ / 12 sem.) pour le T4
nd_q4 = 100.0/ (84/97)  # T3 2026 ramené à 97 jours
# Atterrissage 2026 = réalisé au 23/09 + reste 2025 x (1 + momentum T3 plafonné à ±30 %)
g_rest = df.g_q3.clip(-0.30, 0.30)
df["land26"] = df.ytd26 + df.reste25*(1+g_rest)
df.loc["Nature & Découvertes","land26"] = df.loc["Nature & Découvertes","ytd26"] + nd_q4*0.6  # T4 = basse saison (~60 % du T3)
# Hypothèse 2027 : la moitié du momentum T3 2026, bornée à ±20 % (retour à la moyenne)
df["g27"] = (0.5*df.g_q3).clip(-0.20, 0.20)
df.loc["Nature & Découvertes","g27"] = 0.20  # effet année pleine, borné
df["ca27"] = df.land26*(1+df.g27)
# Les avoirs des mois récents ne sont pas encore saisis (~64 k€) : on les retire du total
adj = 64.0
out = df[["ca25","ytd26","g_ytd","g_q3","land26","g27","ca27"]].copy()
out.loc["TOTAL"] = [out.ca25.sum(), out.ytd26.sum(), np.nan, np.nan, out.land26.sum()-adj, np.nan, out.ca27.sum()-adj*1.0]
pd.set_option("display.width",200)
fmt = out.copy()
for c in ["g_ytd","g_q3","g27"]:
    fmt[c] = (fmt[c]*100).round(1)
for c in ["ca25","ytd26","land26","ca27"]:
    fmt[c] = fmt[c].round(0)
print(fmt.to_string())
t = out.loc["TOTAL"]
print(f"\nAtterrissage 2026 (bottom-up) : {t.land26:.0f} k€ | 2027 : {t.ca27:.0f} k€ ({100*(t.ca27/t.land26-1):+.1f} %)")
out.to_csv("bottomup.csv")
