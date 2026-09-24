"""Connexion directe au serveur MCP Negolux (Streamable HTTP + Bearer).

Aucun LLM ici : on parle au serveur MCP comme le ferait n'importe quel client
(lister les outils, appeler un outil avec des arguments JSON).
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def entetes(cle_api: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {cle_api}"} if cle_api else {}


@asynccontextmanager
async def session_mcp(url: str, cle_api: str):
    """Ouvre une session MCP initialisée, fermée proprement à la sortie."""
    async with streamablehttp_client(url, headers=entetes(cle_api), timeout=30) as (lecture, ecriture, _):
        async with ClientSession(lecture, ecriture) as session:
            await session.initialize()
            yield session


async def lister_outils(url: str, cle_api: str) -> list[dict[str, Any]]:
    async with session_mcp(url, cle_api) as session:
        resultat = await session.list_tools()
        return [
            {
                "nom": outil.name,
                "description": outil.description or "",
                "schema": outil.inputSchema or {},
            }
            for outil in resultat.tools
        ]


async def appeler_outil(url: str, cle_api: str, nom: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async with session_mcp(url, cle_api) as session:
        resultat = await session.call_tool(nom, arguments)
        textes = [bloc.text for bloc in resultat.content if getattr(bloc, "type", "") == "text"]
        texte = "\n".join(textes)
        return {"erreur": bool(resultat.isError), "texte": texte, "json": essayer_json(texte)}


def essayer_json(texte: str) -> Any | None:
    try:
        return json.loads(texte)
    except (json.JSONDecodeError, TypeError):
        return None


def verifier_sante(url: str, cle_api: str) -> tuple[bool, Any]:
    """Appelle GET /health à côté de /mcp (ex. https://mcp.negolux.fr/health)."""
    base = url.rstrip("/").removesuffix("/mcp")
    try:
        reponse = httpx.get(f"{base}/health", headers=entetes(cle_api), timeout=10)
        corps = essayer_json(reponse.text) or reponse.text
        return reponse.status_code == 200, corps
    except httpx.HTTPError as exc:
        return False, str(exc)


def gabarit_arguments(schema: dict[str, Any]) -> dict[str, Any]:
    """Pré-remplit les arguments obligatoires d'un outil à partir de son JSON Schema."""
    proprietes = schema.get("properties", {})
    exemple: dict[str, Any] = {}
    for cle in schema.get("required", []):
        definition = proprietes.get(cle, {})
        type_ = definition.get("type")
        if "default" in definition:
            exemple[cle] = definition["default"]
        elif "enum" in definition:
            exemple[cle] = definition["enum"][0]
        elif type_ == "string" and "\\d{4}-\\d{2}-\\d{2}" in definition.get("pattern", ""):
            exemple[cle] = "2026-05-01"
        else:
            exemple[cle] = {"string": "", "integer": 0, "number": 0, "boolean": False,
                            "array": [], "object": {}}.get(type_, "")
    return exemple
