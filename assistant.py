"""Assistant question/réponse : Claude Code (via le Claude Agent SDK) + serveur MCP Negolux.

Le SDK pilote la CLI Claude Code installée sur le poste. Claude ne reçoit ici
QUE les outils du serveur MCP Negolux : pas de Bash, pas d'accès fichiers.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

NOM_SERVEUR = "negolux"

PROMPT_SYSTEME = """Tu es l'assistant data de Concept Usine (ERP Negolux).
Tu réponds en français, de façon concise, à partir des données réelles de l'ERP.

Règles :
- Utilise exclusivement les outils du serveur MCP negolux. N'invente jamais un chiffre.
- Pour le CA, la marge ou les pièces vendues, utilise stats_commandes (référence de l'écran ERP).
- Pour l'historique par produit (stock, ruptures, prix), utilise historique_produits.
- En SQL libre : lister_tables et decrire_table avant d'écrire la requête, toujours un LIMIT,
  valeurs passées via des "?".
- Précise la période, le périmètre et la définition utilisés (date de commande, avoirs déduits...).
- Présente les résultats chiffrés dans un tableau Markdown quand il y a plusieurs lignes.
"""

Rappel = Callable[[str, dict[str, Any]], Awaitable[None] | None]


def construire_options(url: str, cle_api: str, modele: str | None, session_id: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=PROMPT_SYSTEME,
        mcp_servers={
            NOM_SERVEUR: {
                "type": "http",
                "url": url,
                "headers": {"Authorization": f"Bearer {cle_api}"},
            }
        },
        tools=[],                                    # aucun outil intégré (Bash, Read, Write...)
        allowed_tools=[f"mcp__{NOM_SERVEUR}__*"],    # outils MCP Negolux pré-approuvés
        strict_mcp_config=True,                      # ignore les autres serveurs MCP du poste
        setting_sources=[],                          # ignore CLAUDE.md / settings locaux
        model=modele or None,
        resume=session_id,                           # reprend la conversation précédente
        max_turns=25,
    )


def texte_resultat(contenu: Any) -> str:
    """Le contenu d'un résultat d'outil peut être une chaîne ou une liste de blocs."""
    if contenu is None:
        return ""
    if isinstance(contenu, str):
        return contenu
    morceaux = []
    for bloc in contenu:
        if isinstance(bloc, dict):
            morceaux.append(bloc.get("text", str(bloc)))
        else:
            morceaux.append(getattr(bloc, "text", str(bloc)))
    return "\n".join(morceaux)


async def poser_question(
    question: str,
    url: str,
    cle_api: str,
    modele: str | None,
    session_id: str | None,
    rappel: Callable[[str, dict[str, Any]], None],
) -> None:
    """Envoie la question et remonte chaque évènement à l'interface.

    Évènements : texte, outil, resultat, fin.
    """
    options = construire_options(url, cle_api, modele, session_id)
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for bloc in message.content:
                if isinstance(bloc, TextBlock):
                    rappel("texte", {"texte": bloc.text})
                elif isinstance(bloc, ToolUseBlock):
                    rappel("outil", {
                        "id": bloc.id,
                        "nom": bloc.name.removeprefix(f"mcp__{NOM_SERVEUR}__"),
                        "entree": bloc.input,
                    })
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for bloc in message.content:
                if isinstance(bloc, ToolResultBlock):
                    rappel("resultat", {
                        "id": bloc.tool_use_id,
                        "texte": texte_resultat(bloc.content),
                        "erreur": bool(bloc.is_error),
                    })
        elif isinstance(message, ResultMessage):
            rappel("fin", {
                "session_id": message.session_id,
                "erreur": message.is_error,
                "resultat": message.result,
                "cout_usd": message.total_cost_usd,
                "duree_s": round((message.duration_ms or 0) / 1000, 1),
                "tours": message.num_turns,
            })
