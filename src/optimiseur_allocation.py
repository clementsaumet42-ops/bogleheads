"""
Module d'optimisation d'allocation — Sprint S2.

Deux modes :
  Mode A — Optimisation d'allocation cible (classes d'actifs) via scipy QP
  Mode B — Optimisation d'asset location (quelle classe dans quelle enveloppe) via pulp MILP

En cas d'indisponibilité de scipy ou pulp, fallback vers l'heuristique de src/asset_location.py.

API principale :
  calculer_allocation_cible(profil, config) -> AllocationCible
  calculer_asset_location(allocation_cible, enveloppes, patrimoine, config) -> ResultatAssetLocation
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"

# ─── Constantes ───────────────────────────────────────────────────────────────

CLASSES_ACTIFS_ORDRE = [
    "actions_usa",
    "actions_dev_ex_usa",
    "actions_em",
    "obligations_agg_monde",
    "obligations_euro",
    "reit",
    "or_matieres",
    "monetaire",
]

CLASSES_ACTIONS = {"actions_usa", "actions_dev_ex_usa", "actions_em"}
CLASSES_OBLIGATIONS = {"obligations_agg_monde", "obligations_euro"}

# Taux sans risque par défaut (OAT 10 ans France 2026)
TAUX_SANS_RISQUE_DEFAUT = 0.025

# Plafond PEA légal
PLAFOND_PEA = 150_000.0

# Frais de gestion enveloppes par défaut (annuels)
FRAIS_GESTION_DEFAUT = {
    "PEA": 0.000,
    "PER": 0.007,
    "AV": 0.008,
    "CTO": 0.001,
    "PEE": 0.004,
    "Contrat_Cap_IS": 0.008,
    "CTO_IS": 0.001,
}


# ─── Chargement de la configuration ───────────────────────────────────────────


def charger_config_optimiseur(chemin: str | None = None) -> dict:
    """Charge config/optimiseur.yaml."""
    if chemin is None:
        chemin = CONFIG_DIR / "optimiseur.yaml"
    with open(chemin, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ─── Helpers mathématiques ────────────────────────────────────────────────────


def _construire_matrice_covariance(classes: list[str], config: dict) -> np.ndarray:
    """Construit la matrice de covariance à partir des volatilités et corrélations."""
    n = len(classes)
    vols = np.array(
        [config["classes_actifs"][c]["volatilite_annuelle"] for c in classes], dtype=float
    )

    corr = config.get("correlations", {})
    corr_matrix = np.eye(n)
    for i, ci in enumerate(classes):
        for j, cj in enumerate(classes):
            if i != j:
                val = corr.get(ci, {}).get(cj, 0.0)
                corr_matrix[i, j] = float(val)

    # σ_ij = ρ_ij × σ_i × σ_j
    cov = np.outer(vols, vols) * corr_matrix
    return cov


def _rendement_attendu(poids: np.ndarray, classes: list[str], config: dict) -> float:
    """Rendement attendu du portefeuille."""
    rendements = np.array(
        [config["classes_actifs"][c]["rendement_attendu_annuel"] for c in classes], dtype=float
    )
    return float(np.dot(poids, rendements))


def _volatilite_attendue(poids: np.ndarray, cov: np.ndarray) -> float:
    """Volatilité annuelle du portefeuille (écart-type)."""
    variance = float(poids @ cov @ poids)
    return float(np.sqrt(max(variance, 0.0)))


def _ratio_sharpe(rendement: float, volatilite: float, rf: float) -> float:
    """Ratio de Sharpe ex-ante."""
    if volatilite < 1e-9:
        return 0.0
    return (rendement - rf) / volatilite


# ─── Mode A : Optimisation d'allocation cible ─────────────────────────────────


def optimiser_allocation_mode_a(
    profil_aversion: str,
    config: dict,
    contraintes: dict | None = None,
    age: int | None = None,
) -> dict:
    """
    Mode A — Optimisation Markowitz de l'allocation cible.

    Parameters
    ----------
    profil_aversion : str
        Clé dans config["profils_aversion_risque"] : "defensif", "equilibre",
        "dynamique", "agressif".
    config : dict
        Contenu de config/optimiseur.yaml.
    contraintes : dict, optional
        Contraintes personnalisées (exposition_usa_max, exposition_em_max…).
    age : int, optional
        Âge du client (pour la règle glide-path âge/100).

    Returns
    -------
    dict avec clés : poids (dict classe→poids), rendement_attendu, volatilite_attendue,
                     ratio_sharpe, statut, message.
    """
    contraintes = contraintes or {}
    classes = [c for c in CLASSES_ACTIFS_ORDRE if c in config["classes_actifs"]]
    n = len(classes)

    profils_ar = config.get("profils_aversion_risque", {})
    profil_ar = profils_ar.get(profil_aversion, profils_ar.get("equilibre", {}))
    lambda_ = float(profil_ar.get("lambda", 0.5))
    actions_min_profil = float(profil_ar.get("actions_min", 0.0))
    actions_max_profil = float(profil_ar.get("actions_max", 1.0))

    # Contraintes personnalisées
    actions_max = min(actions_max_profil, float(contraintes.get("actions_max", 1.0) or 1.0))
    actions_min = max(actions_min_profil, float(contraintes.get("actions_min", 0.0) or 0.0))

    # Règle glide path âge/100
    if age is not None:
        obligations_min_age = max(0.0, (age - 10) / 100.0)
        actions_max_age = 1.0 - obligations_min_age
        # N'appliquer l'age constraint que si elle ne rend pas le problème infaisable
        if actions_max_age >= actions_min:
            actions_max = min(actions_max, actions_max_age)

    cov = _construire_matrice_covariance(classes, config)
    rendements = np.array(
        [config["classes_actifs"][c]["rendement_attendu_annuel"] for c in classes], dtype=float
    )
    rf = float(config.get("taux_sans_risque", TAUX_SANS_RISQUE_DEFAUT))

    try:
        from scipy.optimize import minimize

        def objectif(w: np.ndarray) -> float:
            # Minimiser variance - λ × rendement (formulation Markowitz)
            variance = float(w @ cov @ w)
            rendement = float(np.dot(w, rendements))
            return variance - lambda_ * rendement

        def objectif_grad(w: np.ndarray) -> np.ndarray:
            return 2 * cov @ w - lambda_ * rendements

        # Contraintes linéaires
        contraintes_scipy = []

        # Σ w_i = 1
        contraintes_scipy.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})

        # Contraintes actions
        idx_actions = [i for i, c in enumerate(classes) if c in CLASSES_ACTIONS]
        if idx_actions:
            contraintes_scipy.append(
                {
                    "type": "ineq",
                    "fun": lambda w, idx=idx_actions, mn=actions_min: sum(w[i] for i in idx) - mn,
                }
            )
            contraintes_scipy.append(
                {
                    "type": "ineq",
                    "fun": lambda w, idx=idx_actions, mx=actions_max: mx - sum(w[i] for i in idx),
                }
            )

        # Contrainte USA max
        if "exposition_usa_max" in contraintes and contraintes["exposition_usa_max"] is not None:
            usa_max = float(contraintes["exposition_usa_max"])
            idx_usa = [i for i, c in enumerate(classes) if c == "actions_usa"]
            if idx_usa:
                contraintes_scipy.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=idx_usa, mx=usa_max: mx - sum(w[i] for i in idx),
                    }
                )

        # Contrainte EM max
        if "exposition_em_max" in contraintes and contraintes["exposition_em_max"] is not None:
            em_max = float(contraintes["exposition_em_max"])
            idx_em = [i for i, c in enumerate(classes) if c == "actions_em"]
            if idx_em:
                contraintes_scipy.append(
                    {
                        "type": "ineq",
                        "fun": lambda w, idx=idx_em, mx=em_max: mx - sum(w[i] for i in idx),
                    }
                )

        # Bornes : 0 ≤ w_i ≤ 1 pour toutes les classes
        # Sauf obligations_min calculée par age
        bounds_lower = np.zeros(n)
        bounds_upper = np.ones(n)
        bounds = [(bounds_lower[i], bounds_upper[i]) for i in range(n)]

        # Point de départ : allocation uniforme
        w0 = np.ones(n) / n

        result = minimize(
            objectif,
            w0,
            jac=objectif_grad,
            method="SLSQP",
            bounds=bounds,
            constraints=contraintes_scipy,
            options={"ftol": 1e-10, "maxiter": 1000},
        )

        if result.success or result.status in (0, 4):
            w_opt = np.maximum(result.x, 0.0)
            # Normaliser pour que la somme soit exactement 1
            w_opt = w_opt / w_opt.sum() if w_opt.sum() > 1e-10 else w_opt
            poids = {c: float(w_opt[i]) for i, c in enumerate(classes)}
            rend = _rendement_attendu(w_opt, classes, config)
            vol = _volatilite_attendue(w_opt, cov)
            sharpe = _ratio_sharpe(rend, vol, rf)
            return {
                "poids": poids,
                "rendement_attendu": rend,
                "volatilite_attendue": vol,
                "ratio_sharpe": sharpe,
                "statut": "optimal",
                "message": None,
            }
        else:
            logger.warning("scipy SLSQP n'a pas convergé : %s", result.message)
            return _fallback_allocation_mode_a(classes, config, profil_aversion, contraintes, rf)

    except ImportError:
        warnings.warn(
            "scipy non disponible — fallback heuristique Mode A",
            stacklevel=2,
        )
        return _fallback_allocation_mode_a(classes, config, profil_aversion, contraintes, rf)


def _fallback_allocation_mode_a(
    classes: list[str],
    config: dict,
    profil_aversion: str,
    contraintes: dict,
    rf: float,
) -> dict:
    """
    Fallback heuristique quand scipy est indisponible ou que l'optimiseur ne converge pas.

    Utilise les allocations de référence Boglehead par profil.
    """
    allocations_ref = {
        "defensif": {
            "actions_usa": 0.12,
            "actions_dev_ex_usa": 0.10,
            "actions_em": 0.03,
            "obligations_agg_monde": 0.30,
            "obligations_euro": 0.25,
            "reit": 0.05,
            "or_matieres": 0.10,
            "monetaire": 0.05,
        },
        "equilibre": {
            "actions_usa": 0.25,
            "actions_dev_ex_usa": 0.20,
            "actions_em": 0.08,
            "obligations_agg_monde": 0.20,
            "obligations_euro": 0.15,
            "reit": 0.05,
            "or_matieres": 0.05,
            "monetaire": 0.02,
        },
        "dynamique": {
            "actions_usa": 0.35,
            "actions_dev_ex_usa": 0.25,
            "actions_em": 0.12,
            "obligations_agg_monde": 0.12,
            "obligations_euro": 0.08,
            "reit": 0.04,
            "or_matieres": 0.03,
            "monetaire": 0.01,
        },
        "agressif": {
            "actions_usa": 0.40,
            "actions_dev_ex_usa": 0.30,
            "actions_em": 0.15,
            "obligations_agg_monde": 0.07,
            "obligations_euro": 0.03,
            "reit": 0.03,
            "or_matieres": 0.02,
            "monetaire": 0.00,
        },
    }
    ref = allocations_ref.get(profil_aversion, allocations_ref["equilibre"])

    # Appliquer contraintes personnalisées par projection
    poids = {c: ref.get(c, 0.0) for c in classes}

    # Contrainte USA max
    if "exposition_usa_max" in contraintes and contraintes["exposition_usa_max"] is not None:
        usa_max = float(contraintes["exposition_usa_max"])
        if poids.get("actions_usa", 0.0) > usa_max:
            exces = poids["actions_usa"] - usa_max
            poids["actions_usa"] = usa_max
            # Reporter l'excès sur actions_dev_ex_usa
            poids["actions_dev_ex_usa"] = poids.get("actions_dev_ex_usa", 0.0) + exces

    # Contrainte EM max
    if "exposition_em_max" in contraintes and contraintes["exposition_em_max"] is not None:
        em_max = float(contraintes["exposition_em_max"])
        if poids.get("actions_em", 0.0) > em_max:
            exces = poids["actions_em"] - em_max
            poids["actions_em"] = em_max
            poids["actions_dev_ex_usa"] = poids.get("actions_dev_ex_usa", 0.0) + exces

    # Normaliser
    total = sum(poids.values())
    if total > 1e-10:
        poids = {c: v / total for c, v in poids.items()}

    w = np.array([poids.get(c, 0.0) for c in classes])
    cov = _construire_matrice_covariance(classes, config)
    rend = _rendement_attendu(w, classes, config)
    vol = _volatilite_attendue(w, cov)
    sharpe = _ratio_sharpe(rend, vol, rf)

    return {
        "poids": poids,
        "rendement_attendu": rend,
        "volatilite_attendue": vol,
        "ratio_sharpe": sharpe,
        "statut": "fallback",
        "message": "scipy indisponible — allocation heuristique Boglehead de référence",
    }


# ─── Mode B : Optimisation d'asset location ───────────────────────────────────


def optimiser_asset_location_mode_b(
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    enveloppes_disponibles: dict[str, Any],
    config: dict,
    age: int | None = None,
) -> dict:
    """
    Mode B — Optimisation MILP d'asset location.

    Minimise : Σ coût_fiscal_annuel(x_ij) + Σ frais_gestion(x_ij) + Σ TER_ETF(x_ij)

    Parameters
    ----------
    allocation_cible : dict classe → poids
    patrimoine_total : float
    enveloppes_disponibles : dict
        Issu de profil["enveloppes_disponibles"]. Peut être None → CTO uniquement.
    config : dict
        Contenu optimiseur.yaml.
    age : int, optional

    Returns
    -------
    dict avec clés : ventilation (liste), cout_annuel_optimise, cout_annuel_naif,
                     economie_annuelle, statut, message.
    """
    if enveloppes_disponibles is None:
        enveloppes_disponibles = {}

    # Enveloppes actives
    envs_actives: dict[str, dict] = {}
    for env_id, env_data in enveloppes_disponibles.items():
        if env_data and isinstance(env_data, dict) and env_data.get("ouvert", False):
            envs_actives[env_id] = env_data
    if not envs_actives:
        envs_actives["CTO"] = {"encours_actuel": 0, "plafond": float("inf")}

    classes = [c for c in CLASSES_ACTIFS_ORDRE if c in allocation_cible and allocation_cible[c] > 0]
    montants_cible = {c: allocation_cible[c] * patrimoine_total for c in classes}

    # Essayer PuLP
    try:
        import pulp as _pulp_check  # noqa: F401

        resultat = _mode_b_milp(classes, montants_cible, envs_actives, config, patrimoine_total)
        if resultat["statut"] == "optimal":
            return resultat
        logger.warning("PuLP non-optimal : %s — fallback heuristique", resultat.get("message"))
    except ImportError:
        warnings.warn(
            "pulp non disponible — fallback heuristique Mode B",
            stacklevel=2,
        )
    except Exception as exc:
        logger.warning("Erreur PuLP Mode B : %s — fallback heuristique", exc)

    return _fallback_asset_location(classes, montants_cible, envs_actives, config, patrimoine_total)


def _mode_b_milp(
    classes: list[str],
    montants_cible: dict[str, float],
    envs_actives: dict[str, Any],
    config: dict,
    patrimoine_total: float,
) -> dict:
    """Résolution MILP avec PuLP."""
    import pulp

    prob = pulp.LpProblem("AssetLocation", pulp.LpMinimize)
    env_ids = list(envs_actives.keys())

    # Variables x_ij : montant de la classe i dans l'enveloppe j
    x = {(c, e): pulp.LpVariable(f"x_{c}_{e}", lowBound=0) for c in classes for e in env_ids}

    frais_gestion = config.get("frais_gestion_enveloppes", FRAIS_GESTION_DEFAUT)
    classes_config = config.get("classes_actifs", {})

    # Fonction objectif : minimiser coûts annuels
    cout_total = []
    for c in classes:
        ter = classes_config.get(c, {}).get("frais_ter_moyen", 0.001)
        for e in env_ids:
            fg = frais_gestion.get(e, 0.001)
            cout_total.append((fg + ter) * x[(c, e)])
    prob += pulp.lpSum(cout_total), "Cout_annuel_total"

    # Contraintes : Σ_j x_ij = montant_cible_i (respecte l'allocation cible)
    for c in classes:
        prob += (
            pulp.lpSum(x[(c, e)] for e in env_ids) == montants_cible[c],
            f"alloc_cible_{c}",
        )

    # Contraintes plafonds d'enveloppes
    for e in env_ids:
        env_data = envs_actives[e]
        plafond = env_data.get("plafond")
        encours = float(env_data.get("encours_actuel", 0) or 0)
        if plafond is not None:
            espace_restant = max(0.0, float(plafond) - encours)
            prob += (
                pulp.lpSum(x[(c, e)] for c in classes) <= espace_restant,
                f"plafond_{e}",
            )

    # Contraintes d'éligibilité : x_ij = 0 si classe non éligible à l'enveloppe
    for c in classes:
        c_cfg = classes_config.get(c, {})
        for e in env_ids:
            eligible = _est_eligible(c, e, c_cfg)
            if not eligible:
                prob += (x[(c, e)] == 0, f"elig_{c}_{e}")

    # Résolution silencieuse
    solver = pulp.getSolver("PULP_CBC_CMD", msg=False)
    status = prob.solve(solver)

    if pulp.LpStatus[status] not in ("Optimal", "Not Solved"):
        pass

    if pulp.LpStatus[status] == "Optimal":
        ventilation = []
        cout_opt = 0.0
        for c in classes:
            ter = classes_config.get(c, {}).get("frais_ter_moyen", 0.001)
            for e in env_ids:
                val = pulp.value(x[(c, e)]) or 0.0
                if val > 1.0:
                    ventilation.append({"classe": c, "enveloppe": e, "montant": val})
                    fg = frais_gestion.get(e, 0.001)
                    cout_opt += (fg + ter) * val

        cout_naif = _cout_naif(classes, montants_cible, config)
        return {
            "ventilation": ventilation,
            "cout_annuel_optimise": cout_opt,
            "cout_annuel_naif": cout_naif,
            "economie_annuelle": max(0.0, cout_naif - cout_opt),
            "statut": "optimal",
            "message": None,
        }

    return {
        "ventilation": [],
        "cout_annuel_optimise": 0.0,
        "cout_annuel_naif": 0.0,
        "economie_annuelle": 0.0,
        "statut": "infeasible",
        "message": f"PuLP status: {pulp.LpStatus[status]}",
    }


def _est_eligible(classe: str, enveloppe: str, classe_config: dict) -> bool:
    """Détermine si une classe d'actifs est éligible à une enveloppe."""
    env_lower = enveloppe.lower()
    if "pea" in env_lower:
        return bool(classe_config.get("eligible_pea", False))
    if "per" in env_lower:
        return bool(classe_config.get("eligible_per", True))
    if "av" in env_lower or "assurance" in env_lower:
        return bool(classe_config.get("eligible_av", True))
    if "pee" in env_lower:
        # PEE : actions éligibles, pas obligations
        return classe not in ("monetaire",)
    return bool(classe_config.get("eligible_cto", True))


def _fallback_asset_location(
    classes: list[str],
    montants_cible: dict[str, float],
    envs_actives: dict[str, Any],
    config: dict,
    patrimoine_total: float,
) -> dict:
    """
    Fallback heuristique Boglehead pour l'asset location.
    Priorités :
      - Actions → PEA (si éligible) → PER → AV → CTO
      - Obligations → PER → AV → CTO
      - Or/Matières → CTO → PER
      - Monétaire → AV → CTO
    """
    classes_config = config.get("classes_actifs", {})
    frais_gestion = config.get("frais_gestion_enveloppes", FRAIS_GESTION_DEFAUT)

    priorites = {
        "actions_usa": ["PEA", "PER", "AV", "CTO"],
        "actions_dev_ex_usa": ["PEA", "PER", "AV", "CTO"],
        "actions_em": ["PEA", "PER", "AV", "CTO"],
        "obligations_agg_monde": ["PER", "AV", "CTO"],
        "obligations_euro": ["PER", "AV", "CTO"],
        "reit": ["PER", "AV", "CTO"],
        "or_matieres": ["CTO", "PER"],
        "monetaire": ["AV", "CTO"],
    }

    # Espace restant par enveloppe
    espaces = {}
    for env_id, env_data in envs_actives.items():
        plafond = env_data.get("plafond")
        encours = float(env_data.get("encours_actuel", 0) or 0)
        if plafond is not None:
            espaces[env_id] = max(0.0, float(plafond) - encours)
        else:
            espaces[env_id] = float("inf")

    ventilation = []
    cout_opt = 0.0

    for c in classes:
        restant = montants_cible[c]
        prio = priorites.get(c, ["CTO"])
        c_cfg = classes_config.get(c, {})
        ter = c_cfg.get("frais_ter_moyen", 0.001)

        for env_id in prio:
            if restant <= 0.01:
                break
            # Vérifier éligibilité
            if not _est_eligible(c, env_id, c_cfg):
                continue
            if env_id not in espaces:
                continue
            espace = espaces[env_id]
            placer = min(restant, espace)
            if placer > 1.0:
                ventilation.append({"classe": c, "enveloppe": env_id, "montant": placer})
                fg = frais_gestion.get(env_id, 0.001)
                cout_opt += (fg + ter) * placer
                espaces[env_id] = espace - placer
                restant -= placer

        # Résidu en CTO
        if restant > 1.0:
            env_fallback = (
                "CTO" if "CTO" in espaces else list(espaces.keys())[0] if espaces else "CTO"
            )
            ventilation.append({"classe": c, "enveloppe": env_fallback, "montant": restant})
            fg = frais_gestion.get(env_fallback, 0.001)
            cout_opt += (fg + ter) * restant

    cout_naif = _cout_naif(classes, montants_cible, config)
    return {
        "ventilation": ventilation,
        "cout_annuel_optimise": cout_opt,
        "cout_annuel_naif": cout_naif,
        "economie_annuelle": max(0.0, cout_naif - cout_opt),
        "statut": "fallback",
        "message": "pulp indisponible — allocation heuristique Boglehead",
    }


def _cout_naif(
    classes: list[str],
    montants_cible: dict[str, float],
    config: dict,
) -> float:
    """Coût annuel du scénario naïf (tout en CTO)."""
    classes_config = config.get("classes_actifs", {})
    frais_gestion = config.get("frais_gestion_enveloppes", FRAIS_GESTION_DEFAUT)
    fg_cto = frais_gestion.get("CTO", 0.001)
    cout = 0.0
    for c in classes:
        ter = classes_config.get(c, {}).get("frais_ter_moyen", 0.001)
        cout += (fg_cto + ter) * montants_cible.get(c, 0.0)
    return cout


# ─── API publique S3.6 ────────────────────────────────────────────────────────


def calculer_allocation_cible(
    profil: Any,
    config: dict | None = None,
) -> dict[str, float]:
    """
    Retourne l'allocation cible optimale sous forme de dict classe → poids.

    API publique consommée par S3.6 (rebalancement optimal).

    Parameters
    ----------
    profil : dict ou objet Pydantic Profil
        Profil client (champs : profil_aversion_risque, contraintes_personnalisees, age).
    config : dict, optional
        Contenu de config/optimiseur.yaml. Chargé automatiquement si non fourni.

    Returns
    -------
    dict : classe d'actifs → poids (float, somme ≈ 1)
    """
    if config is None:
        config = charger_config_optimiseur()

    # Compatibilité dict et objet Pydantic
    if hasattr(profil, "model_dump"):
        profil_dict = profil.model_dump(by_alias=True)
    else:
        profil_dict = dict(profil) if not isinstance(profil, dict) else profil

    profil_aversion = profil_dict.get("profil_aversion_risque") or "equilibre"
    age = profil_dict.get("age")

    contraintes_raw = profil_dict.get("contraintes_personnalisees") or {}
    if hasattr(contraintes_raw, "model_dump"):
        contraintes = contraintes_raw.model_dump(exclude_none=True)
    elif isinstance(contraintes_raw, dict):
        contraintes = {k: v for k, v in contraintes_raw.items() if v is not None}
    else:
        contraintes = {}

    resultat = optimiser_allocation_mode_a(
        profil_aversion=profil_aversion,
        config=config,
        contraintes=contraintes,
        age=age,
    )
    return resultat["poids"]


def optimiser_portefeuille_complet(
    profil: Any,
    config: dict | None = None,
) -> dict:
    """
    Chaîne Mode A → Mode B :
    1. Calcule l'allocation cible optimale (Mode A)
    2. Ventile par enveloppe (Mode B)

    Returns
    -------
    dict avec clés :
      - allocation_cible : dict classe → poids (Mode A)
      - resultat_mode_a : dict complet du résultat Mode A
      - resultat_mode_b : dict complet du résultat Mode B (asset location)
    """
    if config is None:
        config = charger_config_optimiseur()

    if hasattr(profil, "model_dump"):
        profil_dict = profil.model_dump(by_alias=True)
    else:
        profil_dict = dict(profil) if not isinstance(profil, dict) else profil

    profil_aversion = profil_dict.get("profil_aversion_risque") or "equilibre"
    age = profil_dict.get("age")
    patrimoine = float(profil_dict.get("patrimoine_financier_total", 100_000) or 100_000)
    enveloppes = profil_dict.get("enveloppes_disponibles") or {}

    contraintes_raw = profil_dict.get("contraintes_personnalisees") or {}
    if hasattr(contraintes_raw, "model_dump"):
        contraintes = contraintes_raw.model_dump(exclude_none=True)
    elif isinstance(contraintes_raw, dict):
        contraintes = {k: v for k, v in contraintes_raw.items() if v is not None}
    else:
        contraintes = {}

    # Mode A
    res_a = optimiser_allocation_mode_a(
        profil_aversion=profil_aversion,
        config=config,
        contraintes=contraintes,
        age=age,
    )

    # Mode B
    res_b = optimiser_asset_location_mode_b(
        allocation_cible=res_a["poids"],
        patrimoine_total=patrimoine,
        enveloppes_disponibles=enveloppes,
        config=config,
        age=age,
    )

    return {
        "allocation_cible": res_a["poids"],
        "resultat_mode_a": res_a,
        "resultat_mode_b": res_b,
    }
