"""Orchestration du cycle de vie d'une mission EC + CIF.

Une mission passe par 6 étapes :
0. Qualification (questionnaire 8 questions, score WTF 0-10)
1. Onboarding (DER + LM + profilage MIF II signés eIDAS)
2. Diagnostic fiscal patrimonial (alertes chiffrées)
3. Recommandations (allocation cible + asset location MILP)
4. Plan d'action 12 mois (cascade trimestrielle)
5. Livrables signés (RAA MIF II + classeur PDF)
6. Suivi annuel (revue + delta fiscal réalisé)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Protocol


class EtapeMission(str, Enum):
    QUALIFICATION = "qualification"
    ONBOARDING = "onboarding"
    DIAGNOSTIC = "diagnostic"
    RECOMMANDATIONS = "recommandations"
    PLAN_ACTION = "plan_action"
    LIVRABLES = "livrables"
    SUIVI = "suivi"


class Mission(Protocol):
    id: str
    client: str
    etape_actuelle: EtapeMission
    snapshot_sha256: str
    chemin_dossier: Path


def creer_mission(client: str, ec_orias: str) -> Mission:
    """Crée une nouvelle mission. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1 — voir src/mission/lifecycle.py")


def avancer_etape(mission: Mission, vers: EtapeMission) -> Mission:
    """Fait progresser la mission vers l'étape suivante. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")


def generer_livrable_final(mission: Mission) -> Path:
    """Assemble le ZIP mission complet. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
