# negolux-ia

Projet de connexion d'une base de données et de ses données via un MCP et n8n.

Ce dépôt central regroupe :
- l'**interface web** qui interroge l'ERP Negolux via le MCP et Claude Code ;
- les analyses faites avec Claude Code et les scripts Python qui les produisent ;
- plus tard, les workflows n8n qui les automatiseront.

## Contenu

| Élément | Rôle |
|---|---|
| `app.py` | Interface web Streamlit : assistant, explorateur MCP, journal |
| `assistant.py` | Appel de Claude Code (Claude Agent SDK) avec les outils du MCP Negolux |
| `mcp_direct.py` | Appel direct du serveur MCP, sans Claude (explorateur) |
| `auth.py` | Comptes de l'interface et écran de connexion |
| `fichiers.py` | Lecture des pièces jointes (Excel, CSV, PDF, texte) |
| `exports.py` | Extractions des réponses en PDF, Excel et CSV |
| `journal_excel.py` | Journal des questions et réponses, commun à l'interface et au terminal |
| `lancer.ps1` | Lancement de l'interface sous Windows |
| `data/`, `prevision/`, `docs/` | Données extraites de l'ERP, scripts et notes de la prévision du CA |
| `CLAUDE.md` | Contexte chargé automatiquement par Claude Code dans le terminal |
| `.claude/` | Hooks qui ajoutent au journal les échanges faits dans le terminal |

## Interface web

### Lancer

Sous Windows, depuis le dossier du dépôt :

```powershell
.\lancer.ps1
```

Au premier lancement, le script :
1. crée l'environnement Python `.venv` et installe les dépendances (il les réinstalle chaque fois que `requirements.txt` change) ;
2. crée le fichier `.env` à partir de `.env.example`, puis s'arrête. Renseigne `MCP_API_KEY` dans `.env` et relance.

L'interface s'ouvre ensuite sur http://localhost:8501. L'onglet Assistant a besoin de Claude Code (`claude`) installé et connecté à ton compte.

### Connexion

La première fois, l'interface propose de **créer le premier compte**. Les comptes suivants se gèrent en ligne de commande :

```powershell
.\.venv\Scripts\python auth.py ajouter <identifiant>     # créer un compte ou changer son mot de passe
.\.venv\Scripts\python auth.py supprimer <identifiant>
.\.venv\Scripts\python auth.py lister
```

Les mots de passe sont stockés hachés dans `comptes.json`, qui reste sur le poste (ignoré par git). La session se ferme quand on recharge la page.

### Assistant

- **Pièces jointes** : le bouton « + » de la zone de saisie joint un ou plusieurs fichiers Excel (`.xlsx`, `.xlsm`), CSV, PDF ou texte.
  - Leur contenu est transmis à Claude avec la question.
  - Limites : environ 60 000 caractères par fichier et 150 000 au total. Les PDF scannés, sans texte, ne sont pas lisibles.
- **Extractions** : sous chaque réponse, trois boutons de téléchargement.
  - **PDF** : la question et la réponse, avec ses tableaux.
  - **Excel** : une feuille par tableau de la réponse, plus les données brutes renvoyées par les outils MCP.
  - **CSV** : un fichier par tableau, au format d'Excel en français (`;` et virgule décimale).

  Si la question parle d'Excel, de CSV ou de PDF, le bouton correspondant est mis en avant.
- L'**explorateur MCP** propose aussi l'export Excel et CSV des résultats.

### Journal

Chaque question posée à Claude et sa réponse sont ajoutées à `journal/echanges.xlsx`, qu'elles viennent de l'interface ou du terminal. Le journal indique aussi :
- la date, la durée et la source (interface ou terminal) ;
- l'utilisateur connecté ;
- les pièces jointes et les outils utilisés.

L'onglet **Journal** de l'interface permet de le consulter, de filtrer ses propres questions et de télécharger le classeur.

- Le dossier `journal/` reste sur le poste : il est ignoré par git, car il contient des données confidentielles.
- Si le classeur est ouvert dans Excel au moment d'un échange, celui-ci est quand même conservé dans `journal/echanges.jsonl`. Le classeur est rattrapé à l'échange suivant, ou avec le bouton « Reconstruire », ou avec `python journal_excel.py`.
- Pour le terminal : il faut Python dans le PATH avec `openpyxl` et, sous Windows, Git pour Windows (Git Bash), que Claude Code utilise pour lancer les hooks. En cas de souci, le détail est dans `journal/erreurs.log`.

## Prévision du CA

```powershell
python -m pip install -r requirements.txt
python prevision/prevision_ca.py   # atterrissage de l'année, backtests, scénarios N+1
python prevision/par_canal.py      # détail canal par canal
```

Pour mettre à jour les données, ouvrir Claude Code dans ce dépôt, avec le MCP Negolux connecté, et demander : « mets à jour les données de prévision ». La procédure à suivre est décrite dans `CLAUDE.md`.

## Prochaines étapes

- `n8n/` : exports JSON des workflows, par exemple une mise à jour mensuelle des données suivie de l'envoi de la synthèse par e-mail.
