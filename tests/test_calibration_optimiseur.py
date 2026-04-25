"""Tests de calibration et documentation Markowitz — Sprint S11-A (≥ 6 tests)."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent


# ─── A.1 / A.2 : YAML enrichi et modèle Pydantic ─────────────────────────────


def test_yaml_se_charge_dans_config_optimiseur_enrichi():
    """Le YAML enrichi se charge sans erreur dans ConfigOptimiseurEnrichi."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    assert cfg is not None
    assert cfg.metadonnees is not None


def test_metadonnees_date_calibration_presente():
    """Les métadonnées contiennent une date_calibration valide."""
    from datetime import date

    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    assert isinstance(cfg.metadonnees.date_calibration, date)


def test_metadonnees_avertissements_non_vides():
    """Les métadonnées contiennent au moins un avertissement non vide."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    assert len(cfg.metadonnees.avertissements) >= 1
    for a in cfg.metadonnees.avertissements:
        assert a.strip(), "Un avertissement est vide."


def test_tous_les_mu_ont_source_specifique():
    """Tous les rendements espérés ont une source_specifique non vide."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    assert cfg.rendements_esperes, "Aucun rendement espéré trouvé."
    for classe, re in cfg.rendements_esperes.items():
        assert re.source_specifique and re.source_specifique.strip(), (
            f"La classe '{classe}' n'a pas de source_specifique renseignée."
        )


def test_matrice_correlations_coherente():
    """La matrice de corrélations est symétrique, diagonale = 1, valeurs ∈ [-1, 1]."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    corr = cfg.correlations
    assert corr is not None, "Matrice de corrélations absente."

    for ci, row in corr.items():
        for cj, val in row.items():
            assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9, (
                f"Corrélation hors [-1, 1] : [{ci}][{cj}] = {val}"
            )
            if ci == cj:
                assert abs(val - 1.0) < 1e-9, f"Diagonale ≠ 1 : [{ci}][{ci}] = {val}"
            if cj in corr and ci in corr[cj]:
                inverse = corr[cj][ci]
                assert abs(val - inverse) < 1e-9, (
                    f"Matrice non symétrique : [{ci}][{cj}]={val} mais [{cj}][{ci}]={inverse}"
                )


def test_shrinkage_ledoit_wolf_matrice_definie_positive():
    """Le shrinkage Ledoit-Wolf produit une matrice définie positive."""
    from src.optimiseur_allocation import (
        CLASSES_ACTIFS_ORDRE,
        _construire_matrice_covariance,
        appliquer_shrinkage_ledoit_wolf,
        charger_config_optimiseur,
    )

    config = charger_config_optimiseur()
    classes = [c for c in CLASSES_ACTIFS_ORDRE if c in config["classes_actifs"]]
    cov = _construire_matrice_covariance(classes, config)
    cov_shrunk = appliquer_shrinkage_ledoit_wolf(cov)

    eigenvalues = np.linalg.eigvalsh(cov_shrunk)
    assert np.all(eigenvalues > -1e-9), (
        f"Matrice non semi-définie positive : valeurs propres min = {eigenvalues.min():.6f}"
    )


def test_retrocompatibilite_sans_shrinkage():
    """L'optimiseur produit des résultats identiques avec appliquer_shrinkage=False."""

    from src.optimiseur_allocation import charger_config_optimiseur, optimiser_allocation_mode_a

    config = charger_config_optimiseur()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res1 = optimiser_allocation_mode_a("equilibre", config, appliquer_shrinkage=False)
        res2 = optimiser_allocation_mode_a("equilibre", config)

    poids1 = res1["poids"]
    poids2 = res2["poids"]

    assert set(poids1.keys()) == set(poids2.keys()), "Clés différentes entre les deux appels."
    for k in poids1:
        assert abs(poids1[k] - poids2[k]) < 1e-10, (
            f"Poids[{k}] différents : {poids1[k]} vs {poids2[k]}"
        )


def test_rendements_esperes_intervalle_confiance_coherent():
    """Les intervalles de confiance sont cohérents (borne inf ≤ valeur ≤ borne sup)."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    for classe, re in cfg.rendements_esperes.items():
        if re.intervalle_confiance_95 is not None:
            lo, hi = re.intervalle_confiance_95
            assert lo <= hi, f"IC 95% incohérent pour '{classe}': [{lo}, {hi}]"


def test_periode_donnees_coherente():
    """La période de données est cohérente (début < fin, nb observations raisonnable)."""
    from src.optimiseur.config_schemas import charger_config_enrichie

    cfg = charger_config_enrichie()
    periode = cfg.metadonnees.periode_donnees
    assert periode.debut < periode.fin, "Date début ≥ date fin"
    assert periode.nb_observations_mensuelles >= 12, "Moins de 12 observations mensuelles"
