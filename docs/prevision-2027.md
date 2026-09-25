# Prévision du CA 2027

Données au **24/09/2026**, extraites le 25/09/2026 avec les outils du MCP Negolux.

- **Chiffre d'affaires** : `stats_commandes`. Montants en € TTC, à la date de commande. Le CA est le CA brut moins les remises et les avoirs.
- **Volumes de commandes** : `compter_commandes`.
- **Stock et ruptures** : `historique_produits`.
- **Définitions et anomalies connues** : documentation `consulter_doc` (sujets `kpis`, `regles_metier`, `qualite_donnees`).

Chiffres produits par `python prevision/prevision_ca.py` et `python prevision/par_canal.py`.

## Résultat

**CA 2027 estimé : environ 14,4 M€ TTC**, dans une fourchette de 13,9 à 15,3 M€.
C'est à peu près le niveau attendu pour 2026 (+0,6 % par rapport à 14,3 M€) et +7 % par rapport à 2025 (13,5 M€).
En appliquant une TVA de 20 % à tout le CA, cela fait environ 12,0 M€ HT.

| T1 | T2 | T3 | T4 | Total |
|---|---|---|---|---|
| 2,8 M€ | 5,0 M€ | 4,5 M€ | 2,2 M€ | 14,4 M€ |

## Historique

| Année | CA TTC | Évolution |
|---|---|---|
| 2020 | 25,3 M€ | effet Covid |
| 2021 | 21,2 M€ | −16 % |
| 2022 | 17,3 M€ | −18 % |
| 2023 | 13,6 M€ | −22 % |
| 2024 | 13,6 M€ | 0 % |
| 2025 | 13,5 M€ | −0,5 % |
| 2026 (du 1er janvier au 24 septembre) | 12,27 M€ | +7,5 % sur la même période |

Après la bulle Covid, le CA baisse jusqu'en 2023, puis reste stable autour de 13,5 M€ pendant trois ans. 2026 est la première année de reprise.

## Constats

- **Saisonnalité** : avril-août font 61 % du CA, juillet seul 17 %. Le jardin (univers garden) pèse deux tiers du CA et progresse de 7,1 % en 2026 ; la maison (home) progresse un peu plus vite (+8,5 %).
- **La reprise de 2026 ralentit** (par rapport à la même période de 2025) : T1 +13 %, T2 +7,5 %, T3 +1,9 %. Le T3 est corrigé des avoirs non encore saisis.
- **Correction des avoirs** : les avoirs des derniers mois ne sont pas encore saisis. En septembre, ils ne font que 1,3 % du CA brut, contre 5,4 % d'habitude. Environ 64 k€ ont donc été retirés de juillet à septembre 2026.
- **La croissance vient du prix, pas du volume** : du 1er juillet au 24 septembre, le nombre de commandes baisse de 6,8 % et le prix moyen monte de 19,5 %. En juillet-août, les commandes hors SAV baissent de 7 %.
- **Les commandes SAV progressent plus vite que les ventes** (SAV : service après-vente, renvois, avaries, retours) :
  - de janvier à août, 4 693 commandes SAV en 2026 contre 3 868 en 2025, soit +21 % ;
  - elles passent de 11,6 % à 12,8 % des commandes ;
  - elles comptent dans le nombre de commandes mais ne rapportent presque pas de CA. C'est un signal de coût, pas de chiffre d'affaires.
- **Meilleure disponibilité, sur un catalogue plus court** (jardin, logistique DENJEAN) :

  | Jardin, logistique DENJEAN | 2025 | 2026 |
  |---|---|---|
  | Part des produits en rupture en juillet | 57 % | 39 % |
  | Produits actifs en juillet | 2 249 | 1 730 |
  | Stock à fin septembre | 26 532 articles | 22 755 articles (−14 %) |
  | Part des produits en rupture en septembre | 61 % | 49 % |

  Une partie de la croissance 2026 vient donc de ce levier, qui ne jouera pas une seconde fois avec la même ampleur en 2027.
- **Le mix de canaux change** :
  - en hausse : Vente privée +49 % (27 % du CA), Showroomprivé ×2,2, Groupon +56 %, Vente Unique +67 %, Brico Marché +69 %. Nature & Découvertes est un nouveau canal (0,24 M€) ;
  - en baisse : Amazon −29 %, Leroy Merlin −19 %, ConceptUsine −17 %, But −26 %. Amazon et ConceptUsine ont un taux de marque nul ou négatif.
- **Rentabilité** : le taux de marque (marge / CA) passe de 4,9 % à 7,4 %. Selon la documentation, ce rapport s'appelle « taux de marque » ; le « taux de marge » est la marge rapportée au coût d'achat.

## Méthode

1. **Estimer la fin de 2026.** On prend le réalisé à date, corrigé des avoirs, avec septembre extrapolé à un mois complet. On ajoute la fin d'année 2025 au rythme des 3 derniers mois (+1,9 %). Résultat : **14,34 M€**. Deux autres méthodes donnent 14,52 M€ (poids saisonniers) et 14,22 M€ (canal par canal).
2. **Estimer 2027 avec quatre méthodes :**

   | Méthode | 2027 |
   |---|---|
   | Holt-Winters : lissage exponentiel avec tendance amortie et saisonnalité multiplicative, sur les données depuis 2023 (scénario bas) | 13,88 M€ |
   | Persistance : 2027 = 2026 | 14,34 M€ |
   | **Canal par canal : chaque canal garde la moitié de son rythme récent, borné à ±20 % (scénario central)** | **14,42 M€** |
   | Croissance de 2026 à date prolongée d'un an (scénario haut) | 15,33 M€ |

3. **Tester les méthodes sur le passé.** On refait la prévision de N+1 avec les seules données disponibles à fin septembre de l'année N :

   | Année prévue | Réel | Persistance | Tendance prolongée | Holt-Winters |
   |---|---|---|---|---|
   | 2024 | 13,58 M€ | +1,1 % | −23,6 % | −21,7 % |
   | 2025 | 13,51 M€ | −0,9 % | −3,1 % | −13,6 % |
   | 2026 (estimé) | 14,34 M€ | −5,6 % | −4,2 % | −6,7 % |

   Prolonger une tendance échoue quand la tendance change, comme en 2024. La persistance est la méthode la plus fiable sur le passé. Le scénario canal par canal reste proche d'elle, tout en tenant compte des canaux qui montent et de ceux qui baissent.

4. **Confronter aux signaux de volume et de stock.** La baisse des commandes en été, l'effet déjà acquis de la meilleure disponibilité et la hausse des SAV plaident pour une croissance modeste en 2027. Ils confirment le scénario central plutôt que le scénario haut.

## Précautions de données

- **Date d'arrêt** : la base contient aussi des commandes du jour même, ainsi que quelques commandes datées dans le futur (documentation `qualite_donnees`). Les données s'arrêtent donc à la veille, le 24/09/2026.
- **Limites de `historique_produits`** :
  - il ne couvre que la logistique DENJEAN, et son CA exclut les remises et les avoirs ;
  - on s'en sert pour le stock et les ruptures, pas pour le CA ;
  - les comparaisons de CA avec 2025 y sont faussées, parce que d'autres logistiques existaient en 2025.

## Risques et signaux à suivre

- **Le CA dépend beaucoup de Vente privée** (27 % du CA, ventes par opérations). Si ce canal ne progresse pas en 2027, le CA perd environ 0,4 M€.
- **La météo du printemps et de l'été** est le principal facteur d'écart, vu le poids du jardin.
- **L'approvisionnement de la saison 2027** : le stock est plus bas qu'il y a un an. Des arrivages en retard au printemps pèseraient directement sur le T2.
- **Le T4 2026 est à surveiller** (T4 2025 : 2,0 M€) :
  - au-dessus de +5 %, viser plutôt le haut de la fourchette ;
  - en baisse, plutôt le bas.
