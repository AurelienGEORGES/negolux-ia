# Prévision du CA 2027

Données au 23/09/2026, issues de l'outil `stats_commandes` du MCP Negolux. Montants en € TTC, à la date de commande.
Chiffres produits par `python prevision/prevision_ca.py`.

## Résultat

**CA 2027 estimé : environ 14,4 M€ TTC**, dans une fourchette de 13,9 à 15,3 M€.
C'est à peu près le niveau attendu pour 2026 (+0,6 % par rapport à 14,3 M€) et +7 % par rapport à 2025 (13,5 M€).
En appliquant une TVA de 20 % à tout le CA, cela fait environ 12,0 M€ HT.

| T1 | T2 | T3 | T4 | Total |
|---|---|---|---|---|
| 2,8 M€ | 5,0 M€ | 4,5 M€ | 2,2 M€ | 14,4 M€ |

## Historique

| Année | CA | Évolution |
|---|---|---|
| 2020 | 25,3 M€ | effet Covid |
| 2021 | 21,2 M€ | −16 % |
| 2022 | 17,3 M€ | −18 % |
| 2023 | 13,6 M€ | −22 % |
| 2024 | 13,6 M€ | 0 % |
| 2025 | 13,5 M€ | −0,5 % |
| 2026 (janvier-septembre, corrigé) | 12,3 M€ | +6,9 % sur la même période |

Après la bulle Covid, le CA baisse jusqu'en 2023, puis reste stable autour de 13,5 M€ pendant trois ans. 2026 est la première année de reprise.

## Constats

- **Saisonnalité** : avril-août font 61 % du CA, juillet seul 17 %. L'univers garden pèse 67 % du CA.
- **La reprise de 2026 ralentit** (par rapport à la même période de 2025) : T1 +13 %, T2 +7,5 %, T3 +1,9 %.
- **Correction des avoirs** : les avoirs des derniers mois ne sont pas encore saisis. En septembre, ils ne font que 1,3 % du CA brut, contre 5,4 % d'habitude. Environ 64 k€ ont donc été retirés de juillet à septembre 2026.
- **La croissance vient du panier moyen** : au T3, le nombre de commandes baisse de 7 % et le prix moyen monte de 20 %.
- **Le mix de canaux change** :
  - en hausse : Vente privée +49 % (27 % du CA), Showroomprivé ×2,2, Groupon, Vente Unique, Brico Marché. Nature & Découvertes est un nouveau canal ;
  - en baisse : Amazon −29 %, Leroy Merlin −19 %, ConceptUsine −17 %, But −26 %. Amazon et ConceptUsine sont à marge négative.

## Méthode

1. **Estimer la fin de 2026.** On prend le réalisé à date (corrigé des avoirs, septembre extrapolé à un mois complet) et on ajoute la fin d'année 2025 au rythme des 3 derniers mois (+1,9 %). Résultat : **14,34 M€**. Deux autres méthodes donnent 14,52 M€ (poids saisonniers) et 14,22 M€ (canal par canal).
2. **Estimer 2027 avec quatre méthodes :**

   | Méthode | 2027 |
   |---|---|
   | Holt-Winters : lissage exponentiel avec tendance amortie et saisonnalité multiplicative, sur les données depuis 2023 (scénario bas) | 13,88 M€ |
   | Persistance : 2027 = 2026 | 14,34 M€ |
   | **Canal par canal : chaque canal garde la moitié de son rythme récent, borné à ±20 % (scénario central)** | **14,44 M€** |
   | Croissance de 2026 à date prolongée d'un an (scénario haut) | 15,33 M€ |

3. **Tester les méthodes sur le passé.** On refait la prévision de N+1 avec les seules données disponibles à fin septembre de l'année N :

   | Année prévue | Réel | Persistance | Tendance prolongée | Holt-Winters |
   |---|---|---|---|---|
   | 2024 | 13,58 M€ | +1,1 % | −23,6 % | −21,7 % |
   | 2025 | 13,51 M€ | −0,9 % | −3,1 % | −13,6 % |
   | 2026 (estimé) | 14,34 M€ | −5,6 % | −4,3 % | −6,7 % |

   Prolonger une tendance échoue quand la tendance change, comme en 2024. La persistance est la méthode la plus fiable sur le passé. Le scénario canal par canal reste proche d'elle, tout en tenant compte des canaux qui montent et de ceux qui baissent.

## Risques et signaux à suivre

- **Le CA dépend beaucoup de Vente privée** (27 % du CA, ventes par opérations). Si ce canal ne progresse pas en 2027, le CA perd environ 0,4 M€.
- **La météo du printemps et de l'été** est le principal facteur d'écart, vu le poids du jardin.
- **Le T4 2026 est à surveiller** (T4 2025 : 2,0 M€) :
  - au-dessus de +5 %, viser plutôt le haut de la fourchette ;
  - en baisse, plutôt le bas.
