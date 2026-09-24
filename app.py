"""Interface web Negolux : assistant Q/R (Claude Code) + explorateur MCP direct.

Lancement : streamlit run app.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv

from assistant import poser_question
from mcp_direct import appeler_outil, gabarit_arguments, lister_outils, verifier_sante

if sys.platform == "win32":
    # Nécessaire pour lancer la CLI Claude Code en sous-processus sous Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()
st.set_page_config(page_title="Negolux · Assistant ERP", page_icon="📦", layout="wide")

MODELES = {"Par défaut (Claude Code)": None, "Sonnet": "sonnet", "Opus": "opus", "Haiku": "haiku"}

etat = st.session_state
etat.setdefault("messages", [])       # historique affiché
etat.setdefault("session_id", None)   # session Claude Code à reprendre
etat.setdefault("outils", None)       # cache de l'explorateur


# ─── Barre latérale : connexion ────────────────────────────────────────────────
with st.sidebar:
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


def afficher_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        for appel in message.get("outils", []):
            afficher_appel(appel)
        st.markdown(message["contenu"])
        if message.get("meta"):
            st.caption(message["meta"])


onglet_assistant, onglet_explorateur = st.tabs(["💬 Assistant", "🧰 Explorateur MCP"])


# ─── Onglet 1 : assistant question / réponse ───────────────────────────────────
with onglet_assistant:
    for message in etat.messages:
        afficher_message(message)

    question = st.chat_input("Ex. : quel produit s'est le plus vendu en mai 2026 ?")
    if question and cle_api:
        etat.messages.append({"role": "user", "contenu": question})
        afficher_message(etat.messages[-1])

        with st.chat_message("assistant"):
            statut = st.status("Claude réfléchit…", expanded=True)
            zone_texte = st.empty()
            reponse = {"role": "assistant", "contenu": "", "outils": [], "meta": ""}
            textes: list[str] = []
            appels: dict[str, dict] = {}

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

            try:
                asyncio.run(poser_question(question, url, cle_api, modele, etat.session_id, rappel))
                statut.update(label=f"Terminé — {len(appels)} appel(s) d'outil", state="complete", expanded=False)
            except Exception as exc:  # CLI absente, auth Claude, réseau...
                statut.update(label="Erreur", state="error")
                textes.append(f"⚠️ **Erreur** : `{exc}`")

            reponse["contenu"] = "\n\n".join(textes) or "_(pas de réponse)_"
            reponse["outils"] = list(appels.values())
            etat.messages.append(reponse)
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
                            with st.expander("Réponse brute", expanded=False):
                                st.json(donnees)
                        else:
                            st.code(resultat["texte"])
