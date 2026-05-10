"""Parcours mission VISION — mapping pages <-> phases 1..7.

VISION.md section 4 definit 7 phases de mission. Ce module est la SEULE
source de verite pour :
    - le mapping page Streamlit -> phase
    - le mapping etape canonique -> phase
    - la prochaine phase / etape a traiter
    - la liste ordonnee des phases pour la navigation

Toute UI qui affiche le parcours doit lire ces structures, jamais redefinir
la sequence en local. Cela evite la derive si VISION evolue.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.mission.checklist import ETAPES_CANONIQUES
from src.mission.etat import EtatEtape, EtatMission


@dataclass(frozen=True)
class PhaseParcours:
    """Une phase du parcours mission VISION."""

    numero: int  # 1..7
    cle: str  # identifiant stable (snake_case)
    titre: str  # libelle EC-friendly
    sous_titre: str  # accroche courte
    objectif: str  # une phrase decrivant l'output de la phase
    pages: tuple[str, ...]  # pages Streamlit qui composent cette phase
    etapes_canoniques: tuple[str, ...]  # cles d'etapes (cf checklist)
    livrable_principal: str  # ce que la phase produit
    duree_indicative: str  # estimation EC-time


# Phases canoniques — alignees sur VISION.md section 4
PHASES_PARCOURS: tuple[PhaseParcours, ...] = (
    PhaseParcours(
        numero=1,
        cle="qualification",
        titre="Qualification",
        sous_titre="Pertinence de la mission",
        objectif=(
            "Valider que la mission patrimoniale a du sens pour ce client. "
            "Decision go / no-go documentee."
        ),
        pages=("00_Mission_EC.py",),
        etapes_canoniques=(),
        livrable_principal="Decision go/no-go + ouverture mission",
        duree_indicative="30 min",
    ),
    PhaseParcours(
        numero=2,
        cle="onboarding",
        titre="Onboarding",
        sous_titre="Profil foyer + MIF II",
        objectif=(
            "Saisir le foyer, profiler le client MIF II, generer DER et "
            "lettre de mission pour signature eIDAS."
        ),
        pages=("04_Profil.py", "03_Profilage.py"),
        etapes_canoniques=("profil_saisi", "profilage_mif", "lettre_mission"),
        livrable_principal="DER signe + lettre de mission signee + profil MIF II valide",
        duree_indicative="2h cumulees EC + client",
    ),
    PhaseParcours(
        numero=3,
        cle="diagnostic",
        titre="Diagnostic",
        sous_titre="Etat des lieux chiffre",
        objectif=(
            "Importer les releves PDF, executer les moteurs d'alertes, "
            "chiffrer la friction fiscale actuelle."
        ),
        pages=(
            "24_Import_Patrimoine.py",
            "15_Alertes_Fiscales.py",
            "13_Simulateur_Fiscal.py",
        ),
        etapes_canoniques=("patrimoine_importe", "audit_patrimonial"),
        livrable_principal="Etat des lieux chiffre + alertes hierarchisees",
        duree_indicative="4h EC",
    ),
    PhaseParcours(
        numero=4,
        cle="recommandations",
        titre="Recommandations",
        sous_titre="Allocation cible + asset location",
        objectif=(
            "Fixer une allocation cible Boglehead adaptee au profil et "
            "calculer l'asset location optimale par MILP."
        ),
        pages=("05_Allocation.py", "07_Asset_Location.py"),
        etapes_canoniques=("allocation_cible", "asset_location", "allocation_validee"),
        livrable_principal="Allocation cible + mapping ETF -> enveloppe defendable",
        duree_indicative="2h EC",
    ),
    PhaseParcours(
        numero=5,
        cle="plan_action",
        titre="Plan d'action",
        sous_titre="Cascade 12 mois + ordres",
        objectif=(
            "Produire la cascade trimestrielle de versements, les ordres prets "
            "a passer et le calendrier d'execution."
        ),
        pages=("22_Plan_Execution.py",),
        etapes_canoniques=("plan_rebalancement", "plan_execution"),
        livrable_principal="Planning d'execution operationnel sur 12 mois",
        duree_indicative="2h EC",
    ),
    PhaseParcours(
        numero=6,
        cle="livrables",
        titre="Livrables signes",
        sous_titre="ZIP horodate eIDAS",
        objectif=(
            "Generer le ZIP de fin de mission : PDF client, DER, LM, RAA, "
            "Excel, CSV ordres, journal — tout signe et archive."
        ),
        pages=("21_Conformite_CIF.py",),
        etapes_canoniques=("conformite", "livrables_pdf_excel", "envoi_client"),
        livrable_principal="ZIP mission complet, defendable ACPR/AMF",
        duree_indicative="1h EC",
    ),
    PhaseParcours(
        numero=7,
        cle="suivi_annuel",
        titre="Suivi annuel",
        sous_titre="Revue + delta fiscal realise",
        objectif=(
            "Comparer allocation realisee vs cible, chiffrer la friction "
            "evitee, mettre a jour le DER, produire le nouveau plan 12m."
        ),
        pages=(),  # pas encore de page dediee
        etapes_canoniques=("revue_3_mois",),
        livrable_principal="Livrable de revue annuelle + nouveau plan",
        duree_indicative="2h EC/an",
    ),
)


PHASES_PAR_CLE: dict[str, PhaseParcours] = {p.cle: p for p in PHASES_PARCOURS}
PHASES_PAR_NUMERO: dict[int, PhaseParcours] = {p.numero: p for p in PHASES_PARCOURS}


def phase_d_une_page(nom_fichier_page: str) -> PhaseParcours | None:
    """Retrouve la phase a laquelle appartient une page Streamlit.

    Args:
        nom_fichier_page : ex. '24_Import_Patrimoine.py' (avec ou sans .py).

    Returns:
        La phase ou None si la page n'est rattachee a aucune phase.
    """
    nom = nom_fichier_page if nom_fichier_page.endswith(".py") else f"{nom_fichier_page}.py"
    for phase in PHASES_PARCOURS:
        if nom in phase.pages:
            return phase
    return None


def phase_d_une_etape(cle_etape: str) -> PhaseParcours | None:
    """Retrouve la phase a laquelle appartient une etape canonique."""
    for phase in PHASES_PARCOURS:
        if cle_etape in phase.etapes_canoniques:
            return phase
    return None


def phase_courante(etat: EtatMission) -> PhaseParcours:
    """Determine la phase courante d'une mission selon l'avancement.

    Logique : la phase courante est la premiere phase dont au moins une
    etape obligatoire n'est pas VALIDE/SKIP. Si toutes les phases sont
    validees, on retourne Phase 7 (suivi annuel).
    """
    etats_valides = (EtatEtape.VALIDE, EtatEtape.SKIP)
    for phase in PHASES_PARCOURS:
        for cle in phase.etapes_canoniques:
            statut = etat.etapes.get(cle, EtatEtape.NON_COMMENCE)
            if statut not in etats_valides:
                # On verifie si l'etape est obligatoire
                etape_def = next((e for e in ETAPES_CANONIQUES if e.cle == cle), None)
                if etape_def and etape_def.obligatoire:
                    return phase
        # Si toutes les obligatoires de cette phase sont validees, on continue
    # Toutes phases bouclees -> on est en phase 7
    return PHASES_PAR_CLE["suivi_annuel"]


def phases_terminees(etat: EtatMission) -> list[PhaseParcours]:
    """Liste des phases ou TOUTES les etapes canoniques sont VALIDE ou SKIP.

    Une phase n'est consideree terminee que si elle a au moins une etape
    canonique declaree ET que toutes ces etapes sont validees ou skippees
    explicitement par l'EC. Une mission neuve renvoie donc une liste vide.
    """
    etats_valides = (EtatEtape.VALIDE, EtatEtape.SKIP)
    out: list[PhaseParcours] = []
    for phase in PHASES_PARCOURS:
        if not phase.etapes_canoniques:
            continue
        toutes_validees = all(
            etat.etapes.get(cle, EtatEtape.NON_COMMENCE) in etats_valides
            for cle in phase.etapes_canoniques
        )
        if toutes_validees:
            out.append(phase)
    return out


def progression_par_phase(etat: EtatMission) -> dict[int, int]:
    """Renvoie le pct (0-100) de completion de chaque phase.

    Pour les phases sans etape canonique declaree, renvoie 0.
    """
    etats_valides = (EtatEtape.VALIDE, EtatEtape.SKIP)
    out: dict[int, int] = {}
    for phase in PHASES_PARCOURS:
        if not phase.etapes_canoniques:
            out[phase.numero] = 0
            continue
        valides = sum(
            1
            for cle in phase.etapes_canoniques
            if etat.etapes.get(cle, EtatEtape.NON_COMMENCE) in etats_valides
        )
        out[phase.numero] = round(valides / len(phase.etapes_canoniques) * 100)
    return out


def prochaine_page_recommandee(etat: EtatMission) -> str | None:
    """Retourne la 1re page de la phase courante (CTA principal)."""
    phase = phase_courante(etat)
    if phase.pages:
        return phase.pages[0]
    return None
