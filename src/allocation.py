# -*- coding: utf-8 -*-
"""
Module de gestion des allocations cibles — approche Bogleheads.
Implémente la règle âge-en-obligations et les profils de risque standard.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Profils d'allocation prédéfinis
# ---------------------------------------------------------------------------

PROFILS_DEFAUT = {
    "prudent": {
        "nom": "Prudent",
        "description": "Profil conservateur — capital à préserver, horizon court",
        "actions": 0.30,
        "obligations": 0.70,
        "liquidites": 0.00,
    },
    "equilibre": {
        "nom": "Équilibré",
        "description": "Profil équilibré — rendement/risque modéré, horizon moyen",
        "actions": 0.60,
        "obligations": 0.40,
        "liquidites": 0.00,
    },
    "dynamique": {
        "nom": "Dynamique",
        "description": "Profil offensif — croissance long terme, tolérance volatilité élevée",
        "actions": 0.80,
        "obligations": 0.20,
        "liquidites": 0.00,
    },
}

# Tolérance par défaut autour de l'allocation cible (en points de pourcentage absolus)
TOLERANCE_PAR_DEFAUT = 0.05  # ±5 points absolus

# Tolérance numérique pour la validation des sommes de pourcentages (arrondi flottant)
TOLERANCE_SOMME = 0.001


@dataclass
class AllocationCible:
    """Représente une allocation cible selon l'approche Bogleheads.

    La règle fondamentale de Bogleheads est la règle de l'âge en obligations :
    le pourcentage d'obligations doit être approximativement égal à l'âge du
    titulaire. Cette règle est souvent assouplie à (âge - 10) ou (110 - âge)
    selon le profil de risque.

    Attributes:
        age: Âge du titulaire en années.
        profil: Profil de risque ('prudent', 'equilibre', 'dynamique').
        pct_actions: Pourcentage cible en actions (0 à 1).
        pct_obligations: Pourcentage cible en obligations (0 à 1).
        pct_liquidites: Pourcentage en liquidités (0 à 1).
        tolerance: Bandes de tolérance (en fraction absolue, ex: 0.05 = ±5 %).
        detail_actions: Décomposition de la poche actions par sous-classe.
        detail_obligations: Décomposition de la poche obligations par sous-classe.
    """

    age: int
    profil: str = "equilibre"
    pct_actions: float = 0.60
    pct_obligations: float = 0.40
    pct_liquidites: float = 0.00
    tolerance: float = TOLERANCE_PAR_DEFAUT
    detail_actions: dict = field(default_factory=dict)
    detail_obligations: dict = field(default_factory=dict)

    def __post_init__(self):
        """Valide la cohérence de l'allocation après initialisation."""
        total = self.pct_actions + self.pct_obligations + self.pct_liquidites
        if not (1 - TOLERANCE_SOMME <= total <= 1 + TOLERANCE_SOMME):
            raise ValueError(
                f"L'allocation ne totalise pas 100 % : {total:.1%}. "
                "Vérifier pct_actions + pct_obligations + pct_liquidites = 1."
            )

    @classmethod
    def depuis_profil(cls, profil: str, age: int) -> "AllocationCible":
        """Crée une allocation depuis un profil prédéfini.

        Args:
            profil: Nom du profil ('prudent', 'equilibre', 'dynamique').
            age: Âge du titulaire.

        Returns:
            Instance AllocationCible configurée.

        Raises:
            ValueError: Si le profil est inconnu.
        """
        profil_norm = profil.lower().strip()
        # Accepter les variantes avec accents
        _map_accents = {
            "équilibré": "equilibre",
            "équilibre": "equilibre",
            "dynamique": "dynamique",
            "prudent": "prudent",
        }
        profil_norm = _map_accents.get(profil_norm, profil_norm)

        if profil_norm not in PROFILS_DEFAUT:
            raise ValueError(
                f"Profil inconnu : '{profil}'. "
                f"Valeurs acceptées : {list(PROFILS_DEFAUT.keys())}."
            )
        p = PROFILS_DEFAUT[profil_norm]
        return cls(
            age=age,
            profil=profil_norm,
            pct_actions=p["actions"],
            pct_obligations=p["obligations"],
            pct_liquidites=p["liquidites"],
        )

    @classmethod
    def depuis_age_en_obligations(cls, age: int, variante: str = "standard") -> "AllocationCible":
        """Crée une allocation en appliquant la règle âge-en-obligations.

        Variantes disponibles :
        - 'standard' : pct_obligations = age / 100
        - 'conservateur' : pct_obligations = (age + 10) / 100
        - 'agressif' : pct_obligations = (age - 10) / 100

        Args:
            age: Âge du titulaire en années.
            variante: Variante de la règle à appliquer.

        Returns:
            Instance AllocationCible avec allocation calculée automatiquement.
        """
        if variante == "standard":
            pct_obligations = min(max(age / 100.0, 0.0), 1.0)
        elif variante == "conservateur":
            pct_obligations = min(max((age + 10) / 100.0, 0.0), 1.0)
        elif variante in ("agressif",):
            pct_obligations = min(max((age - 10) / 100.0, 0.0), 1.0)
        else:
            raise ValueError(
                f"Variante inconnue : '{variante}'. "
                "Valeurs : 'standard', 'conservateur', 'agressif'."
            )

        pct_actions = round(1.0 - pct_obligations, 4)

        # Détermination automatique du profil selon l'allocation obtenue
        if pct_actions >= 0.75:
            profil = "dynamique"
        elif pct_actions >= 0.50:
            profil = "equilibre"
        else:
            profil = "prudent"

        return cls(
            age=age,
            profil=profil,
            pct_actions=pct_actions,
            pct_obligations=pct_obligations,
            pct_liquidites=0.0,
        )

    def calculer_montants(self, patrimoine_total: float) -> dict:
        """Calcule les montants cibles en euros pour chaque classe d'actifs.

        Args:
            patrimoine_total: Patrimoine financier total à investir en euros.

        Returns:
            Dictionnaire avec les montants cibles par classe d'actifs.
        """
        return {
            "total": round(patrimoine_total, 2),
            "actions": round(patrimoine_total * self.pct_actions, 2),
            "obligations": round(patrimoine_total * self.pct_obligations, 2),
            "liquidites": round(patrimoine_total * self.pct_liquidites, 2),
        }

    def calculer_bornes_tolerance(self, patrimoine_total: float) -> dict:
        """Calcule les bornes de tolérance en montants et en pourcentages.

        Args:
            patrimoine_total: Patrimoine total en euros.

        Returns:
            Dictionnaire avec les bornes min/max par classe d'actifs.
        """
        montants = self.calculer_montants(patrimoine_total)
        bornes = {}
        for classe in ("actions", "obligations", "liquidites"):
            pct_cible = getattr(self, f"pct_{classe}")
            bornes[classe] = {
                "pct_cible": pct_cible,
                "pct_min": max(0.0, round(pct_cible - self.tolerance, 4)),
                "pct_max": min(1.0, round(pct_cible + self.tolerance, 4)),
                "montant_cible": montants[classe],
                "montant_min": round(max(0.0, pct_cible - self.tolerance) * patrimoine_total, 2),
                "montant_max": round(min(1.0, pct_cible + self.tolerance) * patrimoine_total, 2),
            }
        return bornes

    def est_dans_bandes(self, allocation_actuelle: dict, patrimoine_total: float) -> dict:
        """Vérifie si l'allocation actuelle est dans les bandes de tolérance.

        Args:
            allocation_actuelle: Dictionnaire {classe_actifs: montant_actuel}.
            patrimoine_total: Patrimoine total en euros.

        Returns:
            Dictionnaire {classe_actifs: True/False} indiquant si chaque classe
            est dans les bandes de tolérance.
        """
        bornes = self.calculer_bornes_tolerance(patrimoine_total)
        result = {}
        for classe in ("actions", "obligations", "liquidites"):
            montant = allocation_actuelle.get(classe, 0.0)
            pct = montant / patrimoine_total if patrimoine_total > 0 else 0.0
            b = bornes[classe]
            result[classe] = b["pct_min"] <= pct <= b["pct_max"]
        return result

    def decomposer_actions(
        self,
        pct_monde: float = 0.60,
        pct_usa: float = 0.00,
        pct_europe: float = 0.20,
        pct_emergents: float = 0.10,
        pct_small_cap: float = 0.10,
    ) -> "AllocationCible":
        """Définit la décomposition interne de la poche actions.

        Les pourcentages sont relatifs à la poche actions totale.

        Args:
            pct_monde: Part des ETF Monde (ex: MSCI World).
            pct_usa: Part spécifique USA (si surpondération souhaitée).
            pct_europe: Part Europe.
            pct_emergents: Part marchés émergents.
            pct_small_cap: Part petites capitalisations.

        Returns:
            Instance modifiée (pour chaînage).
        """
        total = pct_monde + pct_usa + pct_europe + pct_emergents + pct_small_cap
        if not (1 - TOLERANCE_SOMME <= total <= 1 + TOLERANCE_SOMME):
            raise ValueError(
                f"La décomposition actions ne totalise pas 100 % : {total:.1%}."
            )
        self.detail_actions = {
            "monde": pct_monde,
            "usa": pct_usa,
            "europe": pct_europe,
            "emergents": pct_emergents,
            "small_cap": pct_small_cap,
        }
        return self

    def decomposer_obligations(
        self,
        pct_etat_euro: float = 0.50,
        pct_etat_usa: float = 0.20,
        pct_credit_ig: float = 0.20,
        pct_high_yield: float = 0.10,
    ) -> "AllocationCible":
        """Définit la décomposition interne de la poche obligations.

        Les pourcentages sont relatifs à la poche obligations totale.

        Args:
            pct_etat_euro: Part obligations d'État zone euro.
            pct_etat_usa: Part Treasuries américains.
            pct_credit_ig: Part crédit investment grade.
            pct_high_yield: Part haut rendement.

        Returns:
            Instance modifiée (pour chaînage).
        """
        total = pct_etat_euro + pct_etat_usa + pct_credit_ig + pct_high_yield
        if not (1 - TOLERANCE_SOMME <= total <= 1 + TOLERANCE_SOMME):
            raise ValueError(
                f"La décomposition obligations ne totalise pas 100 % : {total:.1%}."
            )
        self.detail_obligations = {
            "etat_euro": pct_etat_euro,
            "etat_usa": pct_etat_usa,
            "credit_ig": pct_credit_ig,
            "high_yield": pct_high_yield,
        }
        return self

    def to_dict(self) -> dict:
        """Sérialise l'allocation en dictionnaire pour export Excel/JSON.

        Returns:
            Dictionnaire complet de l'allocation.
        """
        return {
            "age": self.age,
            "profil": self.profil,
            "pct_actions": self.pct_actions,
            "pct_obligations": self.pct_obligations,
            "pct_liquidites": self.pct_liquidites,
            "tolerance": self.tolerance,
            "detail_actions": self.detail_actions,
            "detail_obligations": self.detail_obligations,
        }
