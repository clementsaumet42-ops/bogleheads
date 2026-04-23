"""
Glide path — évolution de l'allocation d'actifs avec l'âge (lifecycle investing).

Supporte deux types de règles :
  - type="formule" : actions% = f(age) avec une expression paramétrable
  - type="points"  : interpolation linéaire entre points d'ancrage

Compatible avec src/projection.py pour projeter avec allocation variable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

# Import pour interop avec projection
from src.projection import AllocationClasses

_CONFIG_DIR = Path(__file__).parent.parent / "config"


@dataclass
class GlidePath:
    """Représente une règle de glide path (trajectoire d'allocation)."""

    nom: str
    description: str
    type: Literal["formule", "points"]
    formule: str | None = None
    points: list[dict] | None = None
    repartition_defensive: dict[str, float] = field(default_factory=dict)
    repartition_actions: dict[str, float] = field(default_factory=dict)

    def part_actions(self, age: int) -> float:
        """Retourne la part d'actions (∈ [0, 1]) à l'âge donné."""
        if self.type == "formule":
            pct = _evaluer_formule_glide(self.formule, age)
            return pct / 100.0
        # type == "points"
        return _interpoler_points(self.points, age) / 100.0

    def allocation_a_age(self, age: int) -> AllocationClasses:
        """Construit l'allocation complète (9 classes) à un âge donné."""
        part_a = self.part_actions(age)
        part_d = 1.0 - part_a

        kwargs: dict[str, float] = {}
        # Poche actions répartie selon repartition_actions
        for classe, poids in self.repartition_actions.items():
            kwargs[classe] = part_a * poids
        # Poche défensive
        for classe, poids in self.repartition_defensive.items():
            kwargs[classe] = part_d * poids

        # Mapping vers les champs de AllocationClasses (attention : 'or' -> 'or_')
        return _construire_allocation(kwargs)

    def trajectoire(
        self,
        age_debut: int,
        age_fin: int,
    ) -> list[tuple[int, AllocationClasses]]:
        """Trajectoire d'allocation année par année."""
        return [(a, self.allocation_a_age(a)) for a in range(age_debut, age_fin + 1)]


def _evaluer_formule_glide(formule: str, age: int) -> float:
    """
    Évaluation SÉCURISÉE d'une expression du type "max(20, min(90, 110 - age))".
    Utilise ast.parse + liste blanche d'opérations — JAMAIS eval() nu.
    """
    import ast
    import operator as op

    ops_autorisees = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Mod: op.mod,
        ast.USub: op.neg,
        ast.UAdd: op.pos,
    }
    fonctions_autorisees = {"max": max, "min": min, "abs": abs}

    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"constante interdite: {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id == "age":
                return age
            raise ValueError(f"variable interdite: {node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in ops_autorisees:
            return ops_autorisees[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops_autorisees:
            return ops_autorisees[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = fonctions_autorisees.get(node.func.id)
            if fn is None:
                raise ValueError(f"fonction interdite: {node.func.id}")
            return fn(*(_eval(a) for a in node.args))
        raise ValueError(f"noeud AST interdit: {type(node).__name__}")

    tree = ast.parse(formule, mode="eval")
    return float(_eval(tree.body))


def _interpoler_points(points: list[dict], age: int) -> float:
    """
    Interpolation linéaire entre points d'ancrage {age, actions}.
    Hors bornes : on "clippe" à la valeur extrême (pas d'extrapolation).
    """
    pts = sorted(points, key=lambda p: p["age"])
    if age <= pts[0]["age"]:
        return float(pts[0]["actions"])
    if age >= pts[-1]["age"]:
        return float(pts[-1]["actions"])
    for i in range(len(pts) - 1):
        a0, a1 = pts[i]["age"], pts[i + 1]["age"]
        if a0 <= age <= a1:
            v0, v1 = pts[i]["actions"], pts[i + 1]["actions"]
            t = (age - a0) / (a1 - a0)
            return float(v0 + t * (v1 - v0))
    return float(pts[-1]["actions"])


def _construire_allocation(kwargs: dict[str, float]) -> AllocationClasses:
    """Construit AllocationClasses depuis un dict, en gérant le cas 'or' -> 'or_'."""
    mapping_alias = {"or": "or_"}
    normalise = {mapping_alias.get(k, k): v for k, v in kwargs.items()}
    # Filtrer uniquement les champs connus de AllocationClasses
    champs_valides = {
        "actions_monde",
        "actions_usa",
        "actions_europe",
        "actions_emergents",
        "obligations",
        "monetaire",
        "or_",
        "immobilier",
        "matieres_premieres",
    }
    return AllocationClasses(**{k: v for k, v in normalise.items() if k in champs_valides})


def charger_glide_paths(
    chemin: str | Path | None = None,
) -> dict[str, GlidePath]:
    """Charge tous les glide paths du YAML."""
    if chemin is None:
        chemin = _CONFIG_DIR / "glide_paths.yaml"
    data = yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))
    repartition_actions_defaut = data.get("repartition_actions_defaut", {})
    gps: dict[str, GlidePath] = {}
    for nom, cfg in data["glide_paths"].items():
        gp = GlidePath(
            nom=nom,
            description=cfg.get("description", ""),
            type=cfg["type"],
            formule=cfg.get("formule"),
            points=cfg.get("points"),
            repartition_defensive=cfg.get("repartition_defensive", {}),
            repartition_actions=cfg.get("repartition_actions", repartition_actions_defaut),
        )
        gps[nom] = gp
    return gps


def glide_path_pour_profil(
    profil_id: str,
    chemin: str | Path | None = None,
) -> GlidePath:
    """Retourne le glide path associé à un profil client."""
    if chemin is None:
        chemin = _CONFIG_DIR / "glide_paths.yaml"
    data = yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))
    nom_gp = data["association_profils"].get(profil_id)
    if nom_gp is None:
        raise KeyError(f"Aucun glide path associé au profil {profil_id!r}")
    return charger_glide_paths(chemin)[nom_gp]
