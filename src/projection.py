"""
Projection patrimoniale Monte-Carlo.

Simule l'évolution d'un portefeuille Boglehead sur 10/20/30 ans en tenant compte :
- des versements périodiques mensuels/annuels
- du rebalancement annuel vers l'allocation cible
- de la fiscalité de sortie par enveloppe
- de la variabilité des rendements (tirages gaussiens corrélés par classe d'actifs)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

# Ordre canonique des classes d'actifs (correspond aux colonnes du YAML)
_CLASSES = [
    "actions_monde",
    "actions_usa",
    "actions_europe",
    "actions_emergents",
    "obligations",
    "monetaire",
    "or",
    "immobilier",
    "matieres_premieres",
]

# Corrélations par défaut entre classes non spécifiées dans le YAML
# Matrice symétrique indexée par les noms de classes
_CORR_DEFAULTS: dict[tuple[str, str], float] = {
    # actions entre elles
    ("actions_monde", "actions_usa"): 0.90,
    ("actions_monde", "actions_europe"): 0.85,
    ("actions_monde", "actions_emergents"): 0.70,
    ("actions_usa", "actions_europe"): 0.80,
    ("actions_usa", "actions_emergents"): 0.65,
    ("actions_europe", "actions_emergents"): 0.65,
    # actions vs other
    ("actions_monde", "obligations"): -0.10,
    ("actions_usa", "obligations"): -0.10,
    ("actions_europe", "obligations"): -0.10,
    ("actions_emergents", "obligations"): -0.05,
    ("actions_monde", "or"): 0.00,
    ("actions_usa", "or"): 0.00,
    ("actions_europe", "or"): 0.00,
    ("actions_emergents", "or"): 0.00,
    ("actions_monde", "immobilier"): 0.65,
    ("actions_usa", "immobilier"): 0.65,
    ("actions_europe", "immobilier"): 0.60,
    ("actions_emergents", "immobilier"): 0.55,
    ("actions_monde", "matieres_premieres"): 0.30,
    ("actions_usa", "matieres_premieres"): 0.30,
    ("actions_europe", "matieres_premieres"): 0.30,
    ("actions_emergents", "matieres_premieres"): 0.40,
    ("actions_monde", "monetaire"): 0.00,
    ("actions_usa", "monetaire"): 0.00,
    ("actions_europe", "monetaire"): 0.00,
    ("actions_emergents", "monetaire"): 0.00,
    # other cross
    ("obligations", "or"): 0.15,
    ("obligations", "immobilier"): 0.10,
    ("obligations", "matieres_premieres"): -0.05,
    ("obligations", "monetaire"): 0.50,
    ("or", "immobilier"): 0.10,
    ("or", "matieres_premieres"): 0.30,
    ("or", "monetaire"): 0.00,
    ("immobilier", "matieres_premieres"): 0.20,
    ("immobilier", "monetaire"): 0.00,
    ("matieres_premieres", "monetaire"): 0.00,
}


@dataclass
class AllocationClasses:
    """Allocation cible par classe d'actifs (somme = 1.0)."""

    actions_monde: float = 0.0
    actions_usa: float = 0.0
    actions_europe: float = 0.0
    actions_emergents: float = 0.0
    obligations: float = 0.0
    monetaire: float = 0.0
    or_: float = 0.0
    immobilier: float = 0.0
    matieres_premieres: float = 0.0

    def as_array(self) -> np.ndarray:
        """Retourne l'allocation sous forme de tableau NumPy (même ordre que _CLASSES)."""
        return np.array([
            self.actions_monde,
            self.actions_usa,
            self.actions_europe,
            self.actions_emergents,
            self.obligations,
            self.monetaire,
            self.or_,
            self.immobilier,
            self.matieres_premieres,
        ], dtype=float)

    @property
    def classes(self) -> list[str]:
        """Liste des noms de classes dans l'ordre canonique."""
        return list(_CLASSES)


@dataclass
class ParametresProjection:
    """Paramètres d'une projection."""

    capital_initial: float
    versement_annuel: float  # 0 si pas de versement
    horizon_annees: int  # 10, 20 ou 30
    allocation: AllocationClasses
    nb_tirages: int = 10000
    seed: int | None = 42
    objectif_capital: float | None = None  # pour calcul probabilité d'atteinte
    rebalancement_annuel: bool = True


@dataclass
class ResultatProjection:
    """Résultats agrégés d'une projection Monte-Carlo."""

    trajectoires: np.ndarray  # shape (nb_tirages, horizon_annees+1)
    capital_final_percentiles: dict[int, float]  # {5: ..., 50: ..., 95: ...}
    capital_median_par_annee: np.ndarray  # shape (horizon_annees+1,)
    capital_p10_par_annee: np.ndarray
    capital_p90_par_annee: np.ndarray
    probabilite_objectif: float | None  # ∈ [0, 1] si objectif fourni
    annee_mediane_atteinte_objectif: int | None
    parametres: ParametresProjection


def charger_params(
    chemin: str | Path = "config/projection_params.yaml",
) -> dict:
    """Charge les paramètres de simulation depuis YAML."""
    chemin = Path(chemin)
    if not chemin.is_absolute():
        # Chercher d'abord depuis la racine du projet
        racine = Path(__file__).parent.parent
        chemin = racine / chemin
    with open(chemin, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _construire_matrice_covariance(params_marche: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    Construit la matrice de covariance Σ et le vecteur de rendements moyens μ
    à partir des paramètres de marché.

    Retourne (mu, Sigma) où :
    - mu : np.ndarray de shape (n_classes,)
    - Sigma : np.ndarray de shape (n_classes, n_classes), semi-définie positive
    """
    classes_actifs = params_marche.get("classes_actifs", {})
    correlations = params_marche.get("correlations", {})

    n = len(_CLASSES)
    mu = np.zeros(n)
    vols = np.zeros(n)

    for i, cls in enumerate(_CLASSES):
        # "or_" → "or" dans le YAML
        yaml_key = "or" if cls == "or" else cls
        if yaml_key in classes_actifs:
            mu[i] = classes_actifs[yaml_key].get("rendement_moyen", 0.0)
            vols[i] = classes_actifs[yaml_key].get("volatilite", 0.01)
        else:
            vols[i] = 0.01  # fallback minimal

    # Construire la matrice de corrélation
    corr = np.eye(n)
    for i, cls_i in enumerate(_CLASSES):
        for j, cls_j in enumerate(_CLASSES):
            if i == j:
                continue
            # Correspondance clé YAML (or_ → or)
            key_i = "or" if cls_i == "or" else cls_i
            key_j = "or" if cls_j == "or" else cls_j

            # Chercher dans les corrélations du YAML (format: "actions_obligations" etc.)
            corr_val = None
            yaml_corr_key = f"{key_i}_{key_j}"
            yaml_corr_key_rev = f"{key_j}_{key_i}"
            # Simplification YAML : "actions" = actions_monde, "obligations" = obligations
            # Mapper les clés du YAML vers les classes
            _yaml_corr_map = {
                "actions_obligations": (
                    {"actions_monde", "actions_usa", "actions_europe", "actions_emergents"},
                    {"obligations"},
                ),
                "actions_or": (
                    {"actions_monde", "actions_usa", "actions_europe", "actions_emergents"},
                    {"or"},
                ),
                "actions_immobilier": (
                    {"actions_monde", "actions_usa", "actions_europe", "actions_emergents"},
                    {"immobilier"},
                ),
            }
            for yaml_key_corr, (set_a, set_b) in _yaml_corr_map.items():
                if (key_i in set_a and key_j in set_b) or (key_j in set_a and key_i in set_b):
                    corr_val = correlations.get(yaml_key_corr)
                    break

            if corr_val is None:
                # Chercher dans les valeurs par défaut
                pair = (cls_i, cls_j)
                pair_rev = (cls_j, cls_i)
                corr_val = _CORR_DEFAULTS.get(pair, _CORR_DEFAULTS.get(pair_rev, 0.0))

            corr[i, j] = corr_val

    # Matrice de covariance : Σ_ij = σ_i * ρ_ij * σ_j
    sigma = np.outer(vols, vols) * corr

    # S'assurer que Σ est semi-définie positive (régularisation si besoin)
    eigenvalues = np.linalg.eigvalsh(sigma)
    if eigenvalues.min() < 0:
        # Régularisation : ajouter une petite valeur sur la diagonale
        epsilon = abs(eigenvalues.min()) + 1e-8
        sigma += epsilon * np.eye(n)

    return mu, sigma


def simuler_monte_carlo(
    params: ParametresProjection,
    params_marche: dict | None = None,
) -> ResultatProjection:
    """
    Simule `nb_tirages` trajectoires du portefeuille sur `horizon_annees`.

    Algorithme :
    1. Pour chaque année t ∈ [1, horizon]:
       - Tirer un vecteur de rendements multi-normal r_t ~ N(μ, Σ)
         où μ et Σ sont construits depuis params_marche
       - Appliquer le rendement à chaque poche : V_t_c = V_{t-1}_c * (1 + r_t_c)
       - Ajouter le versement annuel réparti selon l'allocation cible
       - Si rebalancement_annuel : rééquilibrer vers l'allocation cible
    2. Retourner les trajectoires totales (somme des poches par année).

    Utilise `np.random.default_rng(seed)` pour reproductibilité.
    """
    if params_marche is None:
        params_marche = charger_params()

    mu, sigma = _construire_matrice_covariance(params_marche)

    alloc = params.allocation.as_array()
    # Normaliser l'allocation si la somme n'est pas exactement 1
    somme_alloc = alloc.sum()
    if somme_alloc > 0:
        alloc = alloc / somme_alloc

    n_classes = len(_CLASSES)
    n_tirages = params.nb_tirages
    T = params.horizon_annees

    rng = np.random.default_rng(params.seed)

    # Initialisation des poches par classe d'actifs : shape (n_tirages, n_classes)
    # Capital initial réparti selon l'allocation cible
    portefeuille = np.outer(np.ones(n_tirages), alloc) * params.capital_initial

    # Stocker la valeur totale du portefeuille à chaque année : shape (n_tirages, T+1)
    trajectoires = np.zeros((n_tirages, T + 1))
    trajectoires[:, 0] = portefeuille.sum(axis=1)

    # Tirage vectorisé : shape (T, n_tirages, n_classes)
    # Cholesky pour générer des rendements corrélés
    try:
        L = np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError:
        # Fallback : diagonale (rendements indépendants)
        L = np.diag(np.sqrt(np.diag(sigma)))

    # Z ~ N(0,1) de shape (T, n_tirages, n_classes)
    Z = rng.standard_normal((T, n_tirages, n_classes))
    # Rendements corrélés : r = mu + Z @ L^T → shape (T, n_tirages, n_classes)
    rendements = mu + Z @ L.T

    for t in range(T):
        # Appliquer le rendement
        portefeuille = portefeuille * (1.0 + rendements[t])

        # Ajouter le versement annuel réparti selon l'allocation cible
        if params.versement_annuel != 0:
            portefeuille += params.versement_annuel * alloc

        # Rebalancement annuel vers l'allocation cible
        if params.rebalancement_annuel:
            total = portefeuille.sum(axis=1, keepdims=True)
            portefeuille = total * alloc

        trajectoires[:, t + 1] = portefeuille.sum(axis=1)

    # Calcul des statistiques
    percentiles_config = params_marche.get("simulation", {}).get(
        "percentiles", [5, 10, 25, 50, 75, 90, 95]
    )
    capital_final = trajectoires[:, -1]
    capital_final_percentiles = {
        p: float(np.percentile(capital_final, p)) for p in percentiles_config
    }

    capital_median_par_annee = np.percentile(trajectoires, 50, axis=0)
    capital_p10_par_annee = np.percentile(trajectoires, 10, axis=0)
    capital_p90_par_annee = np.percentile(trajectoires, 90, axis=0)

    # Probabilité d'atteindre l'objectif
    probabilite_objectif = None
    annee_mediane_atteinte_objectif = None
    if params.objectif_capital is not None:
        probabilite_objectif = probabilite_atteindre_objectif(
            trajectoires, params.objectif_capital
        )
        # Année médiane : première année où la médiane dépasse l'objectif
        for annee in range(T + 1):
            if capital_median_par_annee[annee] >= params.objectif_capital:
                annee_mediane_atteinte_objectif = annee
                break

    return ResultatProjection(
        trajectoires=trajectoires,
        capital_final_percentiles=capital_final_percentiles,
        capital_median_par_annee=capital_median_par_annee,
        capital_p10_par_annee=capital_p10_par_annee,
        capital_p90_par_annee=capital_p90_par_annee,
        probabilite_objectif=probabilite_objectif,
        annee_mediane_atteinte_objectif=annee_mediane_atteinte_objectif,
        parametres=params,
    )


def calculer_capital_net_impots(
    capital_brut: float,
    capital_initial: float,
    taux_fiscalite_sortie: float,
) -> float:
    """Applique la fiscalité de sortie sur la plus-value."""
    plus_value = max(0.0, capital_brut - capital_initial)
    return capital_brut - plus_value * taux_fiscalite_sortie


def probabilite_atteindre_objectif(
    trajectoires: np.ndarray,
    objectif: float,
) -> float:
    """Part des trajectoires atteignant l'objectif à l'horizon final."""
    return float(np.mean(trajectoires[:, -1] >= objectif))


def projeter_profil(
    profil: dict,
    allocation: AllocationClasses,
    horizons: list[int] = (10, 20, 30),
    params_marche: dict | None = None,
) -> dict[int, ResultatProjection]:
    """Lance une projection pour un profil client sur plusieurs horizons."""
    if params_marche is None:
        params_marche = charger_params()

    sim_params = params_marche.get("simulation", {})
    nb_tirages = sim_params.get("nb_tirages", 10000)
    seed = sim_params.get("seed", 42)

    capital_initial = float(profil.get("patrimoine_financier_total", 100_000))
    versement_annuel = float(profil.get("capacite_epargne_annuelle", 0))
    objectif_capital = None  # peut être étendu depuis le profil si besoin

    resultats: dict[int, ResultatProjection] = {}
    for horizon in horizons:
        params = ParametresProjection(
            capital_initial=capital_initial,
            versement_annuel=versement_annuel,
            horizon_annees=horizon,
            allocation=allocation,
            nb_tirages=nb_tirages,
            seed=seed,
            objectif_capital=objectif_capital,
            rebalancement_annuel=True,
        )
        resultats[horizon] = simuler_monte_carlo(params, params_marche)

    return resultats
