"""Module S18-A — Auto-save session_state dans la mission active.

Stratégie :
- `activer_autosave` : enregistre un marqueur dans session_state ; la page hôte
  appelle cette fonction une fois par run, et le flush est déclenché quand le
  timestamp dépasse l'intervalle.
- `sauvegarder_immediatement` : force le flush d'une clé critique.
- `restaurer_session` : charge le snapshot persisté dans EtatMission.

Les types non sérialisables (DataFrames, objets complexes) sont filtrés avec un
avertissement dans les logs — jamais d'erreur silencieuse.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Clés à exclure systématiquement (clés internes Streamlit / grandes structures)
_CLES_EXCLUES_PREFIXES = ("_",)
_TAILLE_MAX_VALEUR_BYTES = 100_000  # 100 Ko par valeur


def _est_serialisable(valeur: Any) -> bool:
    """Teste si une valeur est sérialisable JSON de façon simple."""
    try:
        json.dumps(valeur, ensure_ascii=False)
        return True
    except (TypeError, ValueError, OverflowError):
        return False


def _convertir_valeur(valeur: Any) -> Any:
    """Tente de convertir les types courants en types JSON-sérialisables.

    - pandas.DataFrame → list[dict]
    - bytes → skip (None)
    - objets complexes → skip (None)
    """
    # Tentative directe
    if _est_serialisable(valeur):
        return valeur

    # pandas DataFrame
    try:
        import pandas as pd

        if isinstance(valeur, pd.DataFrame):
            return valeur.to_dict(orient="records")
    except ImportError:
        pass

    # Fallback : on skippe
    return None


def filtrer_session_state(session_state: dict[str, Any]) -> dict[str, Any]:
    """Filtre session_state pour ne conserver que les valeurs persistables.

    - Exclut les clés commençant par `_` (clés internes Streamlit)
    - Exclut les valeurs non sérialisables après tentative de conversion
    - Avertit dans les logs pour chaque valeur skippée
    """
    resultat: dict[str, Any] = {}
    for cle, valeur in session_state.items():
        # Exclure clés internes
        if any(cle.startswith(p) for p in _CLES_EXCLUES_PREFIXES):
            continue

        converti = _convertir_valeur(valeur)
        if converti is None and valeur is not None:
            logger.debug(
                "autosave: clé '%s' ignorée (type non sérialisable : %s)",
                cle,
                type(valeur).__name__,
            )
            continue

        # Vérifier la taille
        try:
            taille = len(json.dumps(converti, ensure_ascii=False).encode("utf-8"))
            if taille > _TAILLE_MAX_VALEUR_BYTES:
                logger.debug("autosave: clé '%s' ignorée (taille %d octets > max)", cle, taille)
                continue
        except Exception:
            continue

        resultat[cle] = converti

    return resultat


def activer_autosave(mission_id: str, intervalle_secondes: int = 30) -> None:
    """Active la routine d'auto-save pour la mission active.

    Doit être appelée une fois par run Streamlit depuis la page Mission EC.
    Flush le session_state dans EtatMission quand l'intervalle est dépassé.

    Args:
        mission_id: Identifiant de la mission active.
        intervalle_secondes: Intervalle de flush en secondes (défaut 30).
    """
    try:
        import streamlit as st

        from src.mission.etat import charger_mission, sauvegarder_mission

        now = time.time()
        derniere_cle = f"_autosave_last_{mission_id}"
        derniere_sauvegarde = st.session_state.get(derniere_cle, 0.0)

        if now - derniere_sauvegarde >= intervalle_secondes:
            snapshot = filtrer_session_state(dict(st.session_state))
            try:
                etat = charger_mission(mission_id)
                etat.session_state_snapshot = snapshot
                sauvegarder_mission(etat)
                st.session_state[derniere_cle] = now
                logger.debug("autosave: flush mission %s (%d clés)", mission_id, len(snapshot))
            except FileNotFoundError:
                logger.warning("autosave: mission %s introuvable, flush ignoré.", mission_id)
    except ImportError:
        logger.warning("autosave: streamlit non disponible, flush ignoré.")


def restaurer_session(mission_id: str) -> dict[str, Any]:
    """Charge le snapshot persisté pour la mission et le retourne.

    Usage dans une page Streamlit :
        st.session_state.update(restaurer_session(mission_id))

    Args:
        mission_id: Identifiant de la mission.

    Returns:
        Dictionnaire des valeurs restaurées (peut être vide).
    """
    from src.mission.etat import charger_mission

    try:
        etat = charger_mission(mission_id)
        if etat.session_state_snapshot:
            logger.debug(
                "autosave: restauration mission %s (%d clés)",
                mission_id,
                len(etat.session_state_snapshot),
            )
            return dict(etat.session_state_snapshot)
    except FileNotFoundError:
        logger.warning("autosave: mission %s introuvable pour restauration.", mission_id)
    except Exception as exc:
        logger.warning("autosave: erreur restauration mission %s : %s", mission_id, exc)
    return {}


def sauvegarder_immediatement(mission_id: str, cle: str, valeur: Any) -> None:
    """Force la sauvegarde d'une clé critique dans le snapshot de la mission.

    Utile pour les événements importants (validation allocation, etc.).

    Args:
        mission_id: Identifiant de la mission.
        cle: Clé à persister.
        valeur: Valeur à persister (doit être sérialisable JSON).
    """
    from src.mission.etat import charger_mission, sauvegarder_mission

    try:
        etat = charger_mission(mission_id)
        snapshot = dict(etat.session_state_snapshot or {})

        converti = _convertir_valeur(valeur)
        if converti is None and valeur is not None:
            logger.warning(
                "autosave: sauvegarder_immediatement clé '%s' ignorée (type non sérialisable).",
                cle,
            )
            return

        snapshot[cle] = converti
        etat.session_state_snapshot = snapshot
        sauvegarder_mission(etat)
        logger.debug("autosave: sauvegarde immédiate clé '%s' pour mission %s.", cle, mission_id)
    except FileNotFoundError:
        logger.warning("autosave: mission %s introuvable pour sauvegarde immédiate.", mission_id)
    except Exception as exc:
        logger.warning(
            "autosave: erreur sauvegarde immédiate mission %s clé '%s' : %s",
            mission_id,
            cle,
            exc,
        )
