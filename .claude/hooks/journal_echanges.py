"""Hooks Claude Code du terminal : chaque question et chaque réponse dans le journal Excel.

Appelé par les hooks de .claude/settings.json :
- UserPromptSubmit : met la question de côté (journal/.en_attente/<session>.json) ;
- Stop : retrouve la réponse dans le transcript de la session et l'ajoute au journal
  (journal_excel.py, commun avec l'interface).

Le script ne bloque jamais Claude Code : une erreur est notée dans journal/erreurs.log.
"""
import getpass
import json
import sys
import time
import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
import journal_excel  # noqa: E402

EN_ATTENTE = journal_excel.JOURNAL / ".en_attente"
PERIME_APRES_S = 6 * 3600  # question d'une autre session restée sans Stop depuis 6 h


def heure_locale(horodatage_utc):
    """'2026-09-24T07:55:31.434Z' -> '2026-09-24T09:55:31' (heure locale)."""
    d = datetime.fromisoformat(horodatage_utc.replace("Z", "+00:00"))
    return d.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


# ---------- Lecture du transcript ----------

def charger_transcript(chemin):
    if not chemin or not Path(chemin).exists():
        return []
    lignes = []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            with suppress(json.JSONDecodeError):
                lignes.append(json.loads(ligne))
    return lignes


def texte_utilisateur(ligne):
    """Texte d'une vraie question de l'utilisateur ; None pour toute autre ligne."""
    if ligne.get("type") != "user" or ligne.get("isMeta") or ligne.get("isSidechain"):
        return None
    contenu = ligne.get("message", {}).get("content")
    if isinstance(contenu, str):
        return contenu
    if isinstance(contenu, list) and not any(b.get("type") == "tool_result" for b in contenu):
        return "\n".join(b.get("text", "") for b in contenu if b.get("type") == "text")
    return None


def lire_reponse(transcript, questions, essais=1):
    """Réponse de Claude aux questions en attente : (texte, outils appelés, horodatage de fin).

    Tout ce que Claude a écrit après la première question en attente en fait partie,
    y compris après un message envoyé pendant qu'il travaillait.
    """
    for essai in range(essais):
        lignes = charger_transcript(transcript)
        posees = [(i, t) for i, l in enumerate(lignes) if (t := texte_utilisateur(l)) is not None]
        # Début : la première question en attente (à défaut, la dernière posée)
        debut = next((i for i, t in reversed(posees) if t.strip() == questions[0].strip()),
                     posees[-1][0] if posees else len(lignes))
        textes, outils, fin = [], [], None
        for ligne in lignes[debut + 1:]:
            if ligne.get("type") != "assistant" or ligne.get("isSidechain"):
                continue
            contenu = ligne.get("message", {}).get("content") or []
            if isinstance(contenu, str):
                contenu = [{"type": "text", "text": contenu}]
            for bloc in contenu:
                if bloc.get("type") == "text" and bloc.get("text", "").strip():
                    textes.append(bloc["text"].strip())
                elif bloc.get("type") == "tool_use":
                    outils.append(bloc.get("name", "?"))
            fin = ligne.get("timestamp") or fin
        if textes or essai == essais - 1:
            break
        time.sleep(0.3)  # le transcript n'est peut-être pas encore écrit
    return "\n\n".join(textes), journal_excel.resume_outils(outils), fin


# ---------- Événements ----------

def fichier_attente(session):
    return EN_ATTENTE / f"{session}.json"


def mettre_de_cote(entree):
    """UserPromptSubmit : ajoute la question à la liste d'attente de la session."""
    f = fichier_attente(entree.get("session_id", "inconnue"))
    attente = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    attente.append({
        "question": entree.get("prompt", ""),
        "date": journal_excel.maintenant(),
        "transcript": entree.get("transcript_path"),
    })
    f.write_text(json.dumps(attente, ensure_ascii=False), encoding="utf-8")


def echange(f, session, en_direct, dernier_message=None):
    """Construit l'échange à partir d'un fichier d'attente et du transcript."""
    attente = json.loads(f.read_text(encoding="utf-8"))
    questions = [a["question"] for a in attente]
    reponse, outils, fin = lire_reponse(attente[-1].get("transcript"), questions, essais=5 if en_direct else 1)
    if isinstance(dernier_message, str) and dernier_message.strip() and not reponse.endswith(dernier_message.strip()):
        reponse = f"{reponse}\n\n{dernier_message.strip()}".strip()
    if not reponse:
        statut = "sans réponse"
    else:
        statut = "répondu" if en_direct else "interrompu"
    return {
        "date_question": attente[0]["date"],
        "date_reponse": heure_locale(fin) if fin else (journal_excel.maintenant() if en_direct else ""),
        "source": "terminal",
        "utilisateur": getpass.getuser(),
        "session": session,
        "question": "\n\n— puis —\n\n".join(questions),
        "pieces_jointes": "",
        "reponse": reponse,
        "outils": outils,
        "statut": statut,
    }


def enregistrer(entree):
    """Stop : enregistre l'échange de la session, plus ceux des sessions fermées sans Stop."""
    session = entree.get("session_id", "inconnue")
    a_traiter = []
    f = fichier_attente(session)
    if f.exists():
        a_traiter.append((f, echange(f, session, True, entree.get("last_assistant_message"))))
    for autre in EN_ATTENTE.glob("*.json"):
        if autre != f and time.time() - autre.stat().st_mtime > PERIME_APRES_S:
            a_traiter.append((autre, echange(autre, autre.stem, False)))
    if not a_traiter:
        return None
    message = journal_excel.ajouter([e for _, e in a_traiter])
    for fichier, _ in a_traiter:
        fichier.unlink(missing_ok=True)
    return message


def main():
    EN_ATTENTE.mkdir(parents=True, exist_ok=True)
    if "--reconstruire" in sys.argv:  # conservé pour compatibilité : préférer python journal_excel.py
        print(journal_excel.reconstruire() or f"{journal_excel.XLSX} reconstruit.")
        return
    brut = sys.stdin.buffer.read().decode("utf-8")  # UTF-8 aussi sous Windows
    entree = json.loads(brut) if brut.strip() else {}
    message = None
    if entree.get("hook_event_name") == "UserPromptSubmit":
        mettre_de_cote(entree)
    elif entree.get("hook_event_name") == "Stop":
        message = enregistrer(entree)
    if message:
        print(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        journal_excel.JOURNAL.mkdir(exist_ok=True)
        with open(journal_excel.JOURNAL / "erreurs.log", "a", encoding="utf-8") as log:
            log.write(f"{journal_excel.maintenant()}\n{traceback.format_exc()}\n")
        print(json.dumps({"systemMessage": "Journal des échanges : erreur, voir journal/erreurs.log"}))
    sys.exit(0)
