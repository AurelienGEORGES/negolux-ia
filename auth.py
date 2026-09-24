"""Comptes de l'interface : identifiants et mots de passe hachés (PBKDF2-SHA256) dans comptes.json.

Au premier lancement, l'interface propose de créer le premier compte. Ensuite :
    python auth.py ajouter <identifiant>     créer un compte ou changer son mot de passe
    python auth.py supprimer <identifiant>
    python auth.py lister

comptes.json reste sur le poste (ignoré par git).
"""
from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path

FICHIER = Path(__file__).resolve().parent / "comptes.json"
ITERATIONS = 600_000
LONGUEUR_MIN = 8


def charger() -> dict[str, dict]:
    if not FICHIER.exists():
        return {}
    return json.loads(FICHIER.read_text(encoding="utf-8"))


def _sauver(comptes: dict[str, dict]) -> None:
    temporaire = FICHIER.with_suffix(".tmp")
    temporaire.write_text(json.dumps(comptes, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporaire, FICHIER)


def _hacher(mot_de_passe: str, sel: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, iterations).hex()


def enregistrer_compte(identifiant: str, mot_de_passe: str) -> None:
    identifiant = identifiant.strip()
    if not identifiant:
        raise ValueError("L'identifiant est vide.")
    if len(mot_de_passe) < LONGUEUR_MIN:
        raise ValueError(f"Le mot de passe doit faire au moins {LONGUEUR_MIN} caractères.")
    sel = secrets.token_bytes(16)
    comptes = charger()
    comptes[identifiant] = {"sel": sel.hex(), "iterations": ITERATIONS, "hash": _hacher(mot_de_passe, sel, ITERATIONS)}
    _sauver(comptes)


def supprimer_compte(identifiant: str) -> bool:
    comptes = charger()
    if comptes.pop(identifiant, None) is None:
        return False
    _sauver(comptes)
    return True


def verifier(identifiant: str, mot_de_passe: str) -> bool:
    compte = charger().get(identifiant.strip())
    if compte is None:
        _hacher(mot_de_passe, b"sel-factice", ITERATIONS)  # même durée : ne révèle pas si le compte existe
        return False
    calcule = _hacher(mot_de_passe, bytes.fromhex(compte["sel"]), compte["iterations"])
    return hmac.compare_digest(calcule, compte["hash"])


# ---------- Interface Streamlit ----------

def exiger_connexion() -> str:
    """Affiche l'écran de connexion tant que personne n'est connecté ; renvoie l'identifiant."""
    import streamlit as st

    etat = st.session_state
    if etat.get("utilisateur"):
        return etat.utilisateur

    _, centre, _ = st.columns([1, 1.2, 1])
    with centre:
        st.title("📦 Negolux · Assistant ERP")
        if not charger():
            st.info("Aucun compte n'existe encore : crée le premier.")
            with st.form("premier_compte"):
                identifiant = st.text_input("Identifiant")
                mot_de_passe = st.text_input(f"Mot de passe ({LONGUEUR_MIN} caractères minimum)", type="password")
                confirmation = st.text_input("Confirmation", type="password")
                if st.form_submit_button("Créer le compte", type="primary", width="stretch"):
                    if mot_de_passe != confirmation:
                        st.error("Les deux mots de passe ne correspondent pas.")
                    else:
                        try:
                            enregistrer_compte(identifiant, mot_de_passe)
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            etat.utilisateur = identifiant.strip()
                            st.rerun()
        else:
            with st.form("connexion"):
                identifiant = st.text_input("Identifiant")
                mot_de_passe = st.text_input("Mot de passe", type="password")
                if st.form_submit_button("Se connecter", type="primary", width="stretch"):
                    etat.setdefault("echecs", 0)
                    time.sleep(min(etat.echecs, 5))  # ralentit les essais répétés
                    if verifier(identifiant, mot_de_passe):
                        etat.utilisateur, etat.echecs = identifiant.strip(), 0
                        st.rerun()
                    etat.echecs += 1
                    st.error("Identifiant ou mot de passe incorrect.")
    st.stop()


def bouton_deconnexion() -> None:
    import streamlit as st

    st.caption(f"Connecté : **{st.session_state.utilisateur}**")
    if st.button("Se déconnecter", width="stretch"):
        st.session_state.clear()
        st.rerun()


# ---------- Ligne de commande ----------

def main(arguments: list[str]) -> int:
    if len(arguments) == 2 and arguments[0] == "ajouter":
        mot_de_passe = getpass.getpass("Mot de passe : ")
        if mot_de_passe != getpass.getpass("Confirmation : "):
            print("Les deux mots de passe ne correspondent pas.")
            return 1
        try:
            enregistrer_compte(arguments[1], mot_de_passe)
        except ValueError as exc:
            print(exc)
            return 1
        print(f"Compte « {arguments[1]} » enregistré.")
        return 0
    if len(arguments) == 2 and arguments[0] == "supprimer":
        ok = supprimer_compte(arguments[1])
        print(f"Compte « {arguments[1]} » supprimé." if ok else f"Aucun compte « {arguments[1]} ».")
        return 0 if ok else 1
    if arguments == ["lister"]:
        print("\n".join(charger()) or "Aucun compte.")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
