# Contexte pour Claude Code

## Le projet

Dépôt central pour exploiter les données de l'ERP Negolux avec Claude Code, le MCP Negolux et, à terme, n8n.
Premier cas d'usage : la prévision du CA annuel (`prevision/`, résultats dans `docs/`).

## Accès aux données : MCP Negolux (lecture seule)

- **`stats_commandes`** : la référence pour le CA, la marge et les pièces vendues. Ses calculs sont ceux de l'écran ERP « Statistiques commandes v2 ». Toujours le préférer au SQL libre pour ces chiffres.
  - Une année par appel avec `par_mois: true`. Sur plusieurs années d'un coup, la requête dépasse le délai (`max_statement_time`).
  - Pour comparer à l'année précédente, un seul appel avec `comparer_avec` plutôt que deux appels.
  - `regroupement: regroupement_places` donne le détail par canal (Vente privée, Amazon…), `univers` sépare garden et home.
- **`historique_produits`** : historique jour par jour par produit, fournisseur ou famille (logistique DENJEAN uniquement).
- **`lister_tables`, `decrire_table`, `executer_requete_sql`** : pour tout le reste. Toujours mettre un `LIMIT`, car le résultat est tronqué au-delà de 200 lignes.
- Pièges connus :
  - la table `commande` contient environ 20 000 lignes avec `DATE_C = 0000-00-00`, à exclure en SQL libre ;
  - `produit_budget` est obsolète (dernières données en 2021).

## Définitions à respecter

- **CA** = CA brut (quantité × prix + transport) − remises − avoirs, en **€ TTC**, à la **date de commande**.
- La base est une copie de la veille : pas de données du jour.
- **Les avoirs sont saisis avec plusieurs semaines de retard.** Sur les 2-3 derniers mois, le CA est donc surestimé. `prevision/commun.py` corrige cet effet. Ne jamais comparer un mois récent brut à un mois ancien sans cette correction.
- **Saisonnalité forte** : avril-août font environ 61 % du CA annuel, juillet seul environ 17 %. L'univers garden pèse environ deux tiers du CA.
- Les années 2020 à 2022 sont déformées par le Covid : ne pas s'en servir pour la saisonnalité ni pour les tendances.

## Mettre à jour les données de prévision

Les scripts ne lisent que `data/`. Pour rafraîchir les données (N = année en cours, « veille » = date d'arrêt) :

1. **`data/ca_mensuel.csv`** : appeler `stats_commandes` du 1er janvier N à la veille, avec `par_mois: true` et `comparer_avec` sur les mêmes dates de N-1. Reporter `ca`, `ca_brut` et `avoir` de chaque mois de N. Remettre aussi à jour les mois de N-1 avec un appel sur l'année N-1 complète, car des avoirs continuent d'arriver.
2. **`data/extraction.json`** :
   - `date_arret` = la veille ;
   - `mois_en_cours_partiel` = `true` si le mois n'est pas terminé ;
   - `ca_mois_en_cours_n1_a_date` = le `comparaison.ca` du mois en cours dans l'appel de l'étape 1 (même mois l'an dernier, arrêté au même jour) ;
   - `periode_recente` = du 1er du mois M-2 à la veille.
3. **`data/ca_canaux.csv`** : appeler `stats_commandes` avec `regroupement: regroupement_places` :
   - année N-1 complète → `ca_n1_total` ;
   - du 1er janvier N à la veille, avec `comparer_avec` N-1 → `ca_n_a_date` et `ca_n1_a_date` ;
   - `periode_recente`, avec `comparer_avec` N-1 → `ca_recent_n` et `ca_recent_n1`.

   Garder les 15 plus gros canaux, plus la ligne `TOTAL` (préfixe `*`) qui porte les totaux de chaque appel. Mettre `nouveau = 1` pour un canal ouvert en cours d'année N-1, c'est-à-dire sans base de comparaison.
4. Lancer `python prevision/prevision_ca.py`, puis mettre à jour `docs/` si les conclusions changent.

Au changement d'année, faire glisser `ANNEES_STABLES` dans `prevision/commun.py`.

## Conventions

- Réponses et documents en français. Montants en € TTC sauf mention contraire.
- Les chiffres viennent des outils, jamais de mémoire. Toujours indiquer l'outil et la période utilisés.
- Les données sont confidentielles : le dépôt doit rester **privé**. Aucun identifiant ni clé API dans le dépôt : les mettre dans `.env`, ignoré par git.
- Python 3.11 ou plus : `pip install -r requirements.txt`.
