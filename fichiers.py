"""Pièces jointes : fichiers Excel, CSV, PDF ou texte transformés en texte lisible par Claude.

L'assistant n'a pas accès aux fichiers du poste (aucun outil Read ni Bash) : le contenu
des pièces jointes est donc extrait ici et placé dans la question, entre balises <fichier>.
"""
from __future__ import annotations

import io
from pathlib import Path

TYPES_ACCEPTES = ["xlsx", "xlsm", "csv", "pdf", "txt", "md", "json"]
MAX_PAR_FICHIER = 60_000   # caractères transmis par fichier
MAX_TOTAL = 150_000        # caractères transmis pour l'ensemble des fichiers


def _decoder(contenu: bytes) -> str:
    for encodage in ("utf-8-sig", "cp1252"):  # cp1252 : exports CSV d'Excel en français
        try:
            return contenu.decode(encodage)
        except UnicodeDecodeError:
            continue
    return contenu.decode("utf-8", errors="replace")


def _excel(contenu: bytes) -> str:
    import pandas as pd

    feuilles = pd.read_excel(io.BytesIO(contenu), sheet_name=None)
    parties = []
    for nom, df in feuilles.items():
        parties.append(f"### Feuille « {nom} » ({len(df)} lignes × {len(df.columns)} colonnes)\n"
                       + df.to_csv(index=False, sep=";"))
    return "\n".join(parties) or "(classeur vide)"


def _pdf(contenu: bytes) -> str:
    from pypdf import PdfReader

    lecteur = PdfReader(io.BytesIO(contenu))
    textes = [(page.extract_text() or "").strip() for page in lecteur.pages]
    if not any(textes):
        return f"(PDF de {len(textes)} page(s) sans texte extractible : document scanné ?)"
    return "\n".join(f"--- page {i} ---\n{t}" for i, t in enumerate(textes, 1))


def extraire_texte(nom: str, contenu: bytes) -> str:
    """Texte d'une pièce jointe, tronqué à MAX_PAR_FICHIER caractères."""
    extension = Path(nom).suffix.lower().lstrip(".")
    try:
        if extension in ("xlsx", "xlsm"):
            texte = _excel(contenu)
        elif extension == "pdf":
            texte = _pdf(contenu)
        else:
            texte = _decoder(contenu)
    except Exception as exc:  # fichier corrompu, protégé par mot de passe...
        return f"(lecture impossible : {exc})"
    if len(texte) > MAX_PAR_FICHIER:
        coupe = texte[:MAX_PAR_FICHIER].rsplit("\n", 1)[0]
        texte = f"{coupe}\n[… tronqué : {len(texte):,} caractères au total, seul le début est transmis]".replace(",", " ")
    return texte


def question_avec_pieces(question: str, pieces: list[tuple[str, bytes]]) -> str:
    """Question envoyée à Claude : le contenu des pièces jointes, puis la question."""
    if not pieces:
        return question
    blocs, reste = [], MAX_TOTAL
    for nom, contenu in pieces:
        texte = extraire_texte(nom, contenu)
        if reste <= 0:
            texte = "(non transmis : limite de taille des pièces jointes atteinte)"
        elif len(texte) > reste:
            texte = texte[:reste] + "\n[… tronqué : limite de taille des pièces jointes atteinte]"
        reste -= len(texte)
        blocs.append(f'<fichier nom="{nom}">\n{texte}\n</fichier>')
    return ("Pièces jointes par l'utilisateur :\n\n" + "\n\n".join(blocs)
            + f"\n\nQuestion : {question or 'Analyse ces fichiers.'}")
