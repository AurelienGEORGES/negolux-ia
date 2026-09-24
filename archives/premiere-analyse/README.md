# Première analyse (24/09/2026)

Premières versions des scripts, écrites pendant l'analyse initiale de la base Negolux. Les chiffres y sont écrits directement dans le code.

| Fichier | Contenu |
|---|---|
| `forecast.py` | Atterrissage 2026, Holt-Winters, backtests et scénarios 2027 |
| `bottomup.py` | Prévision canal par canal |
| `bottomup.csv` | Résultat de `bottomup.py` (k€ TTC) |

Ces fichiers sont gardés pour l'historique. Les versions à utiliser sont dans `prevision/` : elles lisent les données dans `data/`. Leur prévision centrale 2027 est de 14,4 M€, contre 14,5 M€ ici, parce que les petits canaux y sont projetés selon leur rythme récent.

Pour les relancer : `python forecast.py` et `python bottomup.py` depuis ce dossier.
