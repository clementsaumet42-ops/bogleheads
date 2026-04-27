"""Comparaison de snapshots d'hypothèses — audit-trail — Sprint S17."""

from __future__ import annotations

from src.hypotheses.snapshot import SnapshotHypotheses
from src.hypotheses.source import Hypothese


def _valeur_str(h: Hypothese) -> str:
    """Représentation string de la valeur d'une hypothèse pour comparaison."""
    return f"{h.valeur}|{h.unite}|{h.version}|{h.confiance}"


def comparer_snapshots(
    snap_a: SnapshotHypotheses,
    snap_b: SnapshotHypotheses,
) -> dict[str, list]:
    """Compare deux snapshots et retourne un rapport d'audit-trail.

    Returns
    -------
    dict avec clés :
        "ajoutees"  : hypothèses présentes dans B mais pas dans A
        "retirees"  : hypothèses présentes dans A mais pas dans B
        "modifiees" : hypothèses présentes dans les deux mais dont la valeur a changé
        "inchangees": hypothèses identiques dans les deux snapshots
    """
    cles_a = set(snap_a.hypotheses.keys())
    cles_b = set(snap_b.hypotheses.keys())

    ajoutees = [snap_b.hypotheses[c] for c in sorted(cles_b - cles_a)]
    retirees = [snap_a.hypotheses[c] for c in sorted(cles_a - cles_b)]

    modifiees: list[dict] = []
    inchangees: list[str] = []
    for cle in sorted(cles_a & cles_b):
        ha = snap_a.hypotheses[cle]
        hb = snap_b.hypotheses[cle]
        if _valeur_str(ha) != _valeur_str(hb):
            modifiees.append(
                {
                    "cle": cle,
                    "avant": ha,
                    "apres": hb,
                    "delta_valeur": f"{ha.valeur} → {hb.valeur}",
                }
            )
        else:
            inchangees.append(cle)

    return {
        "ajoutees": ajoutees,
        "retirees": retirees,
        "modifiees": modifiees,
        "inchangees": inchangees,
    }
