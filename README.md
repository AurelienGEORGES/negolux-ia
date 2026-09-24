# negolux-ia

Projet de connexion d'une base de données et de ses données via un MCP et n8n.

Ce dépôt central regroupe les analyses des données de l'ERP Negolux faites avec Claude Code et le MCP Negolux, les scripts Python qui les produisent et, plus tard, les workflows n8n qui les automatiseront.

## Contenu

| Dossier | Rôle |
|---|---|
| `data/` | Extractions de l'ERP faites avec le MCP Negolux (CSV + paramètres d'extraction) |
| `prevision/` | Scripts Python de prévision du CA |
| `docs/` | Analyses et notes de méthode |
| `CLAUDE.md` | Contexte chargé automatiquement par Claude Code : outils MCP, définitions, procédure de mise à jour des données |
| `.claude/` | Configuration Claude Code du projet : hooks qui tiennent le journal des questions et réponses |

## Démarrage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python prevision/prevision_ca.py   # atterrissage de l'année, backtests, scénarios N+1
python prevision/par_canal.py      # détail canal par canal
```

Pour mettre à jour les données, ouvrir Claude Code dans ce dépôt, avec le MCP Negolux connecté, et demander : « mets à jour les données de prévision ». La procédure à suivre est décrite dans `CLAUDE.md`.

## Journal des questions et réponses

Chaque question posée à Claude Code dans ce dépôt, et chaque réponse, est ajoutée automatiquement à `journal/echanges.xlsx`, avec :
- la date de la question et de la réponse, et la durée ;
- l'utilisateur et la session ;
- les outils utilisés (par exemple `mcp__Negolux__stats_commandes ×3`).

**Ce qu'il faut :**
- Python dans le PATH, avec `openpyxl` (`pip install -r requirements.txt`) ;
- sous Windows, Git pour Windows (Git Bash), que Claude Code utilise pour lancer les hooks.

**Bon à savoir :**
- Le dossier `journal/` reste sur ton poste : il est ignoré par git, car il contient des données confidentielles.
- Si le classeur est ouvert dans Excel au moment d'une réponse, l'échange est quand même conservé dans `journal/echanges.jsonl`. Le classeur est rattrapé à la réponse suivante, ou tout de suite avec :

  ```bash
  python .claude/hooks/journal_echanges.py --reconstruire
  ```
- En cas de souci, le détail est dans `journal/erreurs.log`. Le journal ne bloque jamais Claude Code.

## Prochaines étapes

- `.mcp.json` : déclarer le serveur MCP Negolux pour que Claude Code le trouve dans ce dépôt (secrets dans `.env`).
- `n8n/` : exports JSON des workflows, par exemple une mise à jour mensuelle des données suivie de l'envoi de la synthèse par e-mail.
