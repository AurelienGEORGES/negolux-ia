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

## Démarrage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python prevision/prevision_ca.py   # atterrissage de l'année, backtests, scénarios N+1
python prevision/par_canal.py      # détail canal par canal
```

Pour mettre à jour les données, ouvrir Claude Code dans ce dépôt, avec le MCP Negolux connecté, et demander : « mets à jour les données de prévision ». La procédure à suivre est décrite dans `CLAUDE.md`.

## Prochaines étapes

- `.mcp.json` : déclarer le serveur MCP Negolux pour que Claude Code le trouve dans ce dépôt (secrets dans `.env`).
- `n8n/` : exports JSON des workflows, par exemple une mise à jour mensuelle des données suivie de l'envoi de la synthèse par e-mail.
