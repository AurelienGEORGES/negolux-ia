"""Interface web Negolux : assistant Q/R (Claude Code) + explorateur MCP direct + journal.

- Connexion obligatoire (comptes dans comptes.json, voir auth.py).
- Assistant : pièces jointes (Excel, CSV, PDF...) et extractions de chaque réponse
  en PDF, Excel et CSV ; chaque échange est ajouté au journal Excel.
- Journal : consultation et téléchargement du journal (commun avec le terminal).

Lancement : lancer.ps1, ou streamlit run app.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import exports
import journal_excel
from assistant import poser_question
from auth import bouton_deconnexion, exiger_connexion
from fichiers import TYPES_ACCEPTES, question_avec_pieces
from mcp_direct import appeler_outil, gabarit_arguments, lister_outils, verifier_sante

if sys.platform == "win32":
    # Nécessaire pour lancer la CLI Claude Code en sous-processus sous Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()
st.set_page_config(page_title="Negolux · Assistant ERP", page_icon="📦", layout="wide")

utilisateur = exiger_connexion()

MODELES = {"Par défaut (Claude Code)": None, "Sonnet": "sonnet", "Opus": "opus", "Haiku": "haiku"}

etat = st.session_state
etat.setdefault("messages", [])       # historique affiché
etat.setdefault("session_id", None)   # session Claude Code à reprendre
etat.setdefault("outils", None)       # cache de l'explorateur


# ─── Barre latérale : compte et connexion ──────────────────────────────────────
with st.sidebar:
    bouton_deconnexion()
    st.divider()
    st.header("🔌 Connexion MCP")
    url = st.text_input("URL du serveur", os.getenv("MCP_URL", "https://mcp.negolux.fr/mcp"))
    cle_api = st.text_input("Clé API (Bearer)", os.getenv("MCP_API_KEY", ""), type="password")

    if st.button("Tester la connexion", width="stretch"):
        ok, corps = verifier_sante(url, cle_api)
        (st.success if ok else st.error)("Serveur joignable" if ok else "Serveur injoignable")
        st.json(corps) if isinstance(corps, dict) else st.code(str(corps))

    st.divider()
    st.header("🤖 Claude Code")
    modele = MODELES[st.selectbox("Modèle", list(MODELES))]
    if st.button("Nouvelle conversation", width="stretch"):
        etat.messages, etat.session_id = [], None
        st.rerun()
    if etat.session_id:
        st.caption(f"Session : `{etat.session_id[:8]}…`")

if not cle_api:
    st.warning("Renseigne la clé API du serveur MCP (fichier .env ou barre latérale).")


# ─── Affichage des appels d'outils ─────────────────────────────────────────────
def afficher_appel(appel: dict) -> None:
    icone = "❌" if appel.get("erreur") else "🔧"
    with st.expander(f"{icone} {appel['nom']}", expanded=False):
        st.caption("Arguments")
        st.json(appel["entree"])
        if "texte" in appel:
            st.caption("Résultat")
            try:
                donnees = json.loads(appel["texte"])
                if isinstance(donnees, dict) and isinstance(donnees.get("lignes"), list):
                    st.dataframe(donnees["lignes"], width="stretch")
                else:
                    st.json(donnees, expanded=False)
            except (json.JSONDecodeError, TypeError):
                st.code(appel["texte"][:5000])


def boutons_export(fichiers: dict, prefere: str | None, cle: str) -> None:
    """Boutons de téléchargement ; le format demandé dans la question est mis en avant."""
    def genre(fmt):
        return "primary" if prefere == fmt else "secondary"

    colonnes = st.columns(3)
    if fichiers["pdf"]:
        colonnes[0].download_button("PDF", fichiers["pdf"], f"{fichiers['base']}.pdf", exports.MIME["pdf"],
                                    key=f"pdf_{cle}", icon="📄", type=genre("pdf"), on_click="ignore",
                                    width="stretch")
    if fichiers["xlsx"]:
        colonnes[1].download_button("Excel", fichiers["xlsx"], f"{fichiers['base']}.xlsx", exports.MIME["xlsx"],
                                    key=f"xlsx_{cle}", icon="📊", type=genre("xlsx"), on_click="ignore",
                                    width="stretch", help="Une feuille par tableau (réponse et données brutes des outils)")
    if len(fichiers["csv"]) == 1:
        titre, contenu = fichiers["csv"][0]
        colonnes[2].download_button("CSV", contenu, exports.nom_csv(fichiers["base"], titre), exports.MIME["csv"],
                                    key=f"csv_{cle}_0", icon="🧾", type=genre("csv"), on_click="ignore",
                                    width="stretch")
    elif fichiers["csv"]:
        with colonnes[2].popover("CSV", icon="🧾", type=genre("csv"), width="stretch"):
            for n, (titre, contenu) in enumerate(fichiers["csv"]):
                st.download_button(titre, contenu, exports.nom_csv(fichiers["base"], titre), exports.MIME["csv"],
                                   key=f"csv_{cle}_{n}", on_click="ignore", width="stretch")


def afficher_message(message: dict, index: int) -> None:
    with st.chat_message(message["role"]):
        for appel in message.get("outils", []):
            afficher_appel(appel)
        st.markdown(message["contenu"])
        if message.get("pieces"):
            st.caption("📎 " + ", ".join(message["pieces"]))
        if message.get("meta"):
            st.caption(message["meta"])
        if message.get("exports"):
            boutons_export(message["exports"], message.get("format_demande"), str(index))


def journaliser(question: str, pieces: list[str], reponse: str, appels: list[dict], debut: str, statut: str) -> None:
    """Ajoute l'échange au journal Excel ; un problème est signalé sans bloquer l'interface."""
    try:
        alerte = journal_excel.ajouter([{
            "date_question": debut,
            "date_reponse": journal_excel.maintenant(),
            "source": "interface",
            "utilisateur": utilisateur,
            "session": etat.session_id or "",
            "question": question,
            "pieces_jointes": ", ".join(pieces),
            "reponse": reponse,
            "outils": journal_excel.resume_outils(a["nom"] for a in appels),
            "statut": statut,
        }])
    except Exception as exc:
        alerte = f"Journal : l'échange n'a pas pu être enregistré ({exc})."
    if alerte:
        etat.alerte_journal = alerte


onglet_assistant, onglet_explorateur, onglet_journal = st.tabs(["💬 Assistant", "🧰 Explorateur MCP", "📒 Journal"])


# ─── Onglet 1 : assistant question / réponse ───────────────────────────────────
with onglet_assistant:
    if etat.get("alerte_journal"):
        st.warning(etat.pop("alerte_journal"))
    for index, message in enumerate(etat.messages):
        afficher_message(message, index)

    saisie = st.chat_input(
        "Ex. : quel produit s'est le plus vendu en mai 2026 ? Joins un Excel, un CSV ou un PDF avec +",
        accept_file="multiple", file_type=TYPES_ACCEPTES,
    )
    if saisie and cle_api:
        question = (saisie.text or "").strip()
        pieces = [(f.name, f.getvalue()) for f in saisie.files]
        noms_pieces = [nom for nom, _ in pieces]
        debut = journal_excel.maintenant()
        etat.messages.append({"role": "user", "contenu": question or "_(fichiers joints)_", "pieces": noms_pieces})
        afficher_message(etat.messages[-1], len(etat.messages) - 1)

        with st.chat_message("assistant"):
            statut = st.status("Claude réfléchit…", expanded=True)
            zone_texte = st.empty()
            reponse = {"role": "assistant", "contenu": "", "outils": [], "meta": ""}
            textes: list[str] = []
            appels: dict[str, dict] = {}
            en_erreur = False

            def rappel(evenement: str, donnees: dict) -> None:
                if evenement == "texte":
                    textes.append(donnees["texte"])
                    zone_texte.markdown("\n\n".join(textes))
                elif evenement == "outil":
                    appels[donnees["id"]] = donnees
                    statut.write(f"🔧 `{donnees['nom']}` — {json.dumps(donnees['entree'], ensure_ascii=False)[:200]}")
                elif evenement == "resultat" and donnees["id"] in appels:
                    appels[donnees["id"]].update(texte=donnees["texte"], erreur=donnees["erreur"])
                elif evenement == "fin":
                    etat.session_id = donnees["session_id"]
                    cout = f" · {donnees['cout_usd']:.4f} $" if donnees.get("cout_usd") else ""
                    reponse["meta"] = f"{donnees['duree_s']} s · {donnees['tours']} tours{cout}"
                    if not textes and donnees.get("resultat"):
                        textes.append(donnees["resultat"])

            if pieces:
                statut.write(f"📎 Lecture de {len(pieces)} pièce(s) jointe(s)…")
            try:
                prompt = question_avec_pieces(question, pieces)
                asyncio.run(poser_question(prompt, url, cle_api, modele, etat.session_id, rappel))
                statut.update(label=f"Terminé — {len(appels)} appel(s) d'outil", state="complete", expanded=False)
            except Exception as exc:  # CLI absente, auth Claude, réseau...
                en_erreur = True
                statut.update(label="Erreur", state="error")
                textes.append(f"⚠️ **Erreur** : `{exc}`")

            reponse["contenu"] = "\n\n".join(textes) or "_(pas de réponse)_"
            reponse["outils"] = list(appels.values())
            reponse["format_demande"] = exports.format_demande(question)
            try:
                reponse["exports"] = exports.preparer(question, reponse["contenu"], reponse["outils"],
                                                      utilisateur, datetime.now())
            except Exception as exc:
                reponse["meta"] += f" · extractions indisponibles ({exc})"
            etat.messages.append(reponse)
            journaliser(question, noms_pieces, reponse["contenu"], reponse["outils"], debut,
                        "erreur" if en_erreur else "répondu")
            st.rerun()


# ─── Onglet 2 : explorateur MCP (connexion directe, sans Claude) ───────────────
with onglet_explorateur:
    st.caption("Appel direct des outils du serveur MCP, sans passer par Claude.")

    if st.button("Charger les outils", disabled=not cle_api):
        try:
            etat.outils = asyncio.run(lister_outils(url, cle_api))
        except Exception as exc:
            st.error(f"Connexion MCP impossible : {exc}")

    if etat.outils:
        noms = [o["nom"] for o in etat.outils]
        choix = st.selectbox(f"Outil ({len(noms)} disponibles)", noms)
        outil = next(o for o in etat.outils if o["nom"] == choix)

        st.markdown(outil["description"])
        with st.expander("Schéma des arguments"):
            st.json(outil["schema"])

        arguments_bruts = st.text_area(
            "Arguments (JSON)",
            json.dumps(gabarit_arguments(outil["schema"]), indent=2, ensure_ascii=False),
            height=180,
            key=f"args_{choix}",
        )

        if st.button("▶️ Exécuter", type="primary"):
            try:
                arguments = json.loads(arguments_bruts or "{}")
            except json.JSONDecodeError as exc:
                st.error(f"JSON invalide : {exc}")
            else:
                with st.spinner(f"Appel de {choix}…"):
                    try:
                        resultat = asyncio.run(appeler_outil(url, cle_api, choix, arguments))
                    except Exception as exc:
                        st.error(f"Échec de l'appel : {exc}")
                    else:
                        if resultat["erreur"]:
                            st.error(resultat["texte"])
                        elif isinstance(resultat["json"], dict):
                            donnees = resultat["json"]
                            for cle in ("lignes", "detail", "tables"):
                                if isinstance(donnees.get(cle), list):
                                    st.dataframe(donnees[cle], width="stretch")
                            tableaux = exports.tableaux_outils([{"nom": choix, "texte": resultat["texte"]}])
                            if tableaux:
                                base = f"negolux_{choix}_{datetime.now():%Y%m%d_%H%M%S}"
                                boutons_export({"base": base, "pdf": None, "xlsx": exports.en_excel(tableaux),
                                                "csv": [(t, exports.en_csv(df)) for t, df in tableaux]},
                                               None, "explorateur")
                            with st.expander("Réponse brute", expanded=False):
                                st.json(donnees)
                        else:
                            st.code(resultat["texte"])


# ─── Onglet 3 : journal des échanges ───────────────────────────────────────────
with onglet_journal:
    st.caption("Toutes les questions posées à Claude, depuis cette interface ou depuis le terminal (Claude Code).")
    echanges = journal_excel.lire()

    gauche, milieu, droite = st.columns([2, 1, 1])
    seulement_moi = gauche.toggle("Uniquement mes questions")
    if journal_excel.XLSX.exists():
        milieu.download_button("Journal Excel", journal_excel.XLSX.read_bytes(), "journal_negolux.xlsx",
                               exports.MIME["xlsx"], icon="📥", on_click="ignore", width="stretch")
    if droite.button("Reconstruire", icon="🔄", width="stretch",
                     help="Régénère le classeur à partir de journal/echanges.jsonl (utile s'il était ouvert dans Excel)"):
        alerte = journal_excel.reconstruire()
        (st.warning if alerte else st.success)(alerte or "Classeur reconstruit.")

    if not echanges:
        st.info("Aucun échange enregistré pour l'instant.")
    else:
        tableau = pd.DataFrame([{
            "N°": n,
            "Date": (e.get("date_question") or "").replace("T", " "),
            "Source": e.get("source", "terminal"),
            "Utilisateur": e.get("utilisateur", ""),
            "Question": e.get("question", ""),
            "Pièces jointes": e.get("pieces_jointes", ""),
            "Statut": e.get("statut", ""),
        } for n, e in enumerate(echanges, 1)]).iloc[::-1]
        if seulement_moi:
            tableau = tableau[tableau["Utilisateur"] == utilisateur]
        st.dataframe(tableau, hide_index=True, width="stretch",
                     column_config={"Question": st.column_config.TextColumn(width="large")})

        if not tableau.empty:
            numero = st.selectbox("Voir un échange", tableau["N°"].tolist(),
                                  format_func=lambda n: f"N° {n} — {echanges[n - 1].get('question', '')[:90]}")
            echange = echanges[numero - 1]
            with st.container(border=True):
                st.markdown(f"**Question** — {echange.get('utilisateur', '')}, "
                            f"{(echange.get('date_question') or '').replace('T', ' ')}")
                st.markdown(echange.get("question", ""))
                if echange.get("pieces_jointes"):
                    st.caption("📎 " + echange["pieces_jointes"])
                st.divider()
                st.markdown(echange.get("reponse") or "_(pas de réponse)_")
                if echange.get("outils"):
                    st.caption("🔧 " + echange["outils"])
