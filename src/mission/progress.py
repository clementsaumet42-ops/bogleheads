"""Calcul de progression et détection de blocages d'une mission CGP."""

from __future__ import annotations

from src.mission.checklist import ETAPES_CANONIQUES, ETAPES_PAR_CLE, Etape
from src.mission.etat import EtatEtape, EtatMission


def calculer_progression(etat: EtatMission) -> dict:
    """Calcule les métriques d'avancement d'une mission.

    Retourne un dict avec :
    - pct_global : % d'étapes VALIDE ou SKIP sur total
    - pct_obligatoire : % d'étapes obligatoires VALIDE
    - pct_par_rdv : {'RDV1': X, 'RDV2': Y}
    - prochaine_etape : Etape | None
    - etapes_bloquees : list[Etape]
    - alertes : list[str]
    """
    etapes_valides = 0
    etapes_obligatoires_valides = 0
    etapes_obligatoires_total = 0
    rdv_stats: dict[str, dict[str, int]] = {}

    for etape in ETAPES_CANONIQUES:
        statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
        est_valide = statut in (EtatEtape.VALIDE, EtatEtape.SKIP)

        if est_valide:
            etapes_valides += 1

        if etape.obligatoire:
            etapes_obligatoires_total += 1
            if statut == EtatEtape.VALIDE:
                etapes_obligatoires_valides += 1

        if etape.rdv:
            rdv = etape.rdv
            if rdv not in rdv_stats:
                rdv_stats[rdv] = {"valides": 0, "total": 0}
            rdv_stats[rdv]["total"] += 1
            if est_valide:
                rdv_stats[rdv]["valides"] += 1

    total = len(ETAPES_CANONIQUES)
    pct_global = round(etapes_valides / total * 100) if total > 0 else 0
    pct_obligatoire = (
        round(etapes_obligatoires_valides / etapes_obligatoires_total * 100)
        if etapes_obligatoires_total > 0
        else 0
    )
    pct_par_rdv = {
        rdv: round(stats["valides"] / stats["total"] * 100) if stats["total"] > 0 else 0
        for rdv, stats in rdv_stats.items()
    }

    etapes_bloquees = detecter_blocages(etat)

    # Prochaine étape = première étape NON_COMMENCE non bloquée
    prochaine_etape: Etape | None = None
    for etape in ETAPES_CANONIQUES:
        statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
        if statut == EtatEtape.NON_COMMENCE and etape not in etapes_bloquees:
            prochaine_etape = etape
            break

    alertes: list[str] = []
    for etape in etapes_bloquees:
        deps_non_valides = [
            ETAPES_PAR_CLE[dep].titre
            for dep in etape.depends_on
            if dep in ETAPES_PAR_CLE
            and etat.etapes.get(dep, EtatEtape.NON_COMMENCE)
            not in (EtatEtape.VALIDE, EtatEtape.SKIP)
        ]
        if deps_non_valides:
            deps_str = ", ".join(f'"{d}"' for d in deps_non_valides)
            alertes.append(f'Pour débloquer "{etape.titre}", valider d\'abord : {deps_str}.')

    return {
        "pct_global": pct_global,
        "pct_obligatoire": pct_obligatoire,
        "pct_par_rdv": pct_par_rdv,
        "prochaine_etape": prochaine_etape,
        "etapes_bloquees": etapes_bloquees,
        "alertes": alertes,
    }


def detecter_blocages(etat: EtatMission) -> list[Etape]:
    """Retourne les étapes bloquées par une dépendance non validée."""
    bloquees: list[Etape] = []
    for etape in ETAPES_CANONIQUES:
        statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
        if statut in (EtatEtape.VALIDE, EtatEtape.SKIP):
            continue
        for dep in etape.depends_on:
            statut_dep = etat.etapes.get(dep, EtatEtape.NON_COMMENCE)
            if statut_dep not in (EtatEtape.VALIDE, EtatEtape.SKIP):
                bloquees.append(etape)
                break
    return bloquees
