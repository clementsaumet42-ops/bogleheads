"""
Rebalancement Optimal — Sprint S3.6.

Implémente une cascade de priorités fiscales (du moins cher au plus cher) :

  Étape 1 — GRATUIT (priorité absolue)
    Arbitrage intra-enveloppe PEA / PER / AV / Contrat Cap IS

  Étape 2 — FLUX (dilue la dérive sans vendre)
    Orienter versements vers les classes sous-pondérées (src/rebalancement_flux.py)

  Étape 3 — VENTE SI NÉCESSAIRE (optimisée fiscalement)
    3a. AV > 8 ans : abattement annuel 4 600 € / 9 200 €
    3b. PEA ≥ 5 ans : PS 17,2 % uniquement
    3c. CTO/IR : CMP obligatoire (BOI-RPPM-PVBMI-20-10-20-40)
    3d. CTO/IS : FIFO (PCG + art. 38 CGI) + tax-loss harvesting
    3e. En dernier recours : PER (fiscalité sortie lourde)

Un solveur MILP (PuLP) minimise le coût fiscal + frais de courtage tout en
respectant les bandes d'allocation ±5 pp par classe d'actifs.

TODO(S3.7) : implémenter contraintes_liquidite() pour fenêtres d'éligibilité.
TODO(S3.8) : horizon_temporel > 0 pour optimisation multi-périodes 30 ans.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

# PuLP est une dépendance optionnelle (extra "optim" dans pyproject.toml).
# On tente l'import ; s'il échoue le solveur MILP est désactivé mais la
# cascade manuelle reste pleinement fonctionnelle.
try:
    import pulp

    PULP_AVAILABLE = True
except ImportError:  # pragma: no cover
    PULP_AVAILABLE = False

# ─── Constantes fiscales ─────────────────────────────────────────────────────

TAUX_PS = 0.172  # Prélèvements sociaux 2026
TAUX_PFU = 0.314  # PFU (IR 12,8% + PS 17,2% + CDHR/CEHR selon profil)
TAUX_PEA_POST5ANS = 0.172  # PS uniquement
ABATTEMENT_AV_CELIBATAIRE = 4_600.0
ABATTEMENT_AV_COUPLE = 9_200.0

ENVELOPPES_GRATUITES = {"PEA", "PER", "PEE", "AV", "Contrat_Cap_IS"}
ENVELOPPES_PEA = {"PEA"}
ENVELOPPES_AV = {"AV"}
ENVELOPPES_PER = {"PER"}
ENVELOPPES_CTO = {"CTO_perso", "CTO_IS"}

# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class Lot:
    """Lot d'acquisition d'un ETF (pour FIFO ou traçabilité)."""

    date_acquisition: str  # ISO 8601
    quantite: float
    prix_unitaire: float

    @property
    def date(self) -> datetime.date:
        return datetime.date.fromisoformat(self.date_acquisition)

    @property
    def montant_total(self) -> float:
        return self.quantite * self.prix_unitaire


@dataclass
class Position:
    """Position détaillée d'un ETF dans une enveloppe."""

    etf: str
    enveloppe: str
    quantite: float
    prix_revient_moyen: float  # CMP pour CTO/IR
    montant_actuel: float  # valeur de marché actuelle
    lots: list[Lot] = field(default_factory=list)
    date_ouverture_enveloppe: str | None = None  # ISO 8601

    @property
    def plus_value_latente(self) -> float:
        """PV latente (peut être négative = moins-value latente)."""
        cout_total = self.prix_revient_moyen * self.quantite
        return self.montant_actuel - cout_total

    @property
    def cours_actuel(self) -> float:
        """Prix unitaire actuel estimé."""
        return self.montant_actuel / self.quantite if self.quantite > 0 else 0.0

    def age_enveloppe_ans(self, date_ref: datetime.date | None = None) -> float | None:
        """Âge de l'enveloppe en années à date_ref (None → aujourd'hui)."""
        if self.date_ouverture_enveloppe is None:
            return None
        ref = date_ref or datetime.date.today()
        ouverture = datetime.date.fromisoformat(self.date_ouverture_enveloppe)
        return (ref - ouverture).days / 365.25


@dataclass
class VentePlanifiee:
    """Vente planifiée dans le plan de rebalancement."""

    etf: str
    enveloppe: str
    montant: float  # montant à vendre en €
    plus_value_realisee: float  # PV réalisée après méthode CMP/FIFO
    cout_fiscal: float  # coût fiscal en €
    frais_courtage: float  # frais de courtage en €
    methode: str  # "GRATUIT", "AV_ABATTEMENT", "PEA_PS", "CTO_CMP", "CTO_FIFO", "PER"
    detail: str  # explication textuelle


@dataclass
class AchatPlanifie:
    """Achat planifié dans le plan de rebalancement."""

    etf: str
    enveloppe: str
    montant: float
    frais_courtage: float


@dataclass
class PlanRebalancement:
    """Plan de rebalancement complet produit par l'optimiseur."""

    date_generation: str
    profil_code: str

    # Dérive constatée
    derive_par_classe: dict[str, float]  # {classe: derive_pp en pp}

    # Étape 1 — arbitrages gratuits
    arbitrages_gratuits: list[dict[str, Any]] = field(default_factory=list)

    # Étape 2 — flux
    flux_recommandes: list[dict[str, Any]] = field(default_factory=list)

    # Étape 3 — ventes
    ventes: list[VentePlanifiee] = field(default_factory=list)
    achats: list[AchatPlanifie] = field(default_factory=list)

    # Résultats
    allocation_atteinte: bool = False
    cout_fiscal_total: float = 0.0
    cout_fiscal_naif: float = 0.0
    economie_fiscale: float = 0.0
    horizon_mois: int = 0  # 0 = immédiat, > 0 = plan étalé sur N mois


# ─── Helpers fiscaux ──────────────────────────────────────────────────────────


def calculer_pv_cmp(
    montant_vente: float,
    prix_revient_moyen: float,
    cours_actuel: float,
) -> float:
    """
    Calcule la plus-value selon la méthode CMP (CTO/IR).

    BOI-RPPM-PVBMI-20-10-20-40 : le prix de revient unitaire est le CMP
    de l'ensemble des titres de même nature détenus par le contribuable.

    PV = montant_vente - (montant_vente / cours_actuel) × prix_revient_moyen
    """
    if cours_actuel <= 0:
        return 0.0
    quantite_vendue = montant_vente / cours_actuel
    cout_revient = quantite_vendue * prix_revient_moyen
    return montant_vente - cout_revient


def calculer_pv_fifo(
    montant_vente: float,
    lots: list[Lot],
    cours_actuel: float,
) -> float:
    """
    Calcule la plus-value selon la méthode FIFO (CTO/IS, PCG + art. 38 CGI).

    Les lots les plus anciens sont cédés en premier.
    """
    if cours_actuel <= 0 or not lots:
        return 0.0

    quantite_a_vendre = montant_vente / cours_actuel
    lots_tries = sorted(lots, key=lambda lot: lot.date)

    cout_revient_total = 0.0
    reste = quantite_a_vendre

    for lot in lots_tries:
        if reste <= 0:
            break
        qty_lot = min(reste, lot.quantite)
        cout_revient_total += qty_lot * lot.prix_unitaire
        reste -= qty_lot

    return montant_vente - cout_revient_total


def cout_fiscal_cto_ir(plus_value: float) -> float:
    """Coût fiscal CTO/IR : PFU 31,4 % (IR 12,8% + PS 17,2%)."""
    if plus_value <= 0:
        return 0.0
    return plus_value * TAUX_PFU


def cout_fiscal_pea(plus_value: float, age_ans: float | None) -> float:
    """
    Coût fiscal PEA.

    PEA < 5 ans : clôture totale → calcul PFU (retrait = fermeture du plan).
    PEA ≥ 5 ans : PS 17,2 % uniquement (Art. 150-0 A CGI).
    """
    if plus_value <= 0:
        return 0.0
    if age_ans is None or age_ans < 5.0:
        return plus_value * TAUX_PFU  # clôture totale → PFU
    return plus_value * TAUX_PEA_POST5ANS


def cout_fiscal_av(
    plus_value: float,
    age_enveloppe_ans: float | None,
    abattement_restant: float,
) -> tuple[float, float]:
    """
    Coût fiscal AV (Art. 125-0 A CGI).

    AV > 8 ans : abattement sur les gains (4 600 € ou 9 200 €/an).
    AV < 8 ans : PFU 31,4%.

    Returns: (cout_fiscal, abattement_consomme)
    """
    if plus_value <= 0:
        return 0.0, 0.0
    if age_enveloppe_ans is not None and age_enveloppe_ans >= 8.0:
        gains_imposables = max(0.0, plus_value - abattement_restant)
        abattement_consomme = min(plus_value, abattement_restant)
        return gains_imposables * TAUX_PFU, abattement_consomme
    return plus_value * TAUX_PFU, 0.0


def est_pea_eligible_retrait(position: Position) -> bool:
    """
    Retourne True si un retrait partiel est possible sur ce PEA sans clôture.

    PEA < 5 ans → tout retrait entraîne la clôture du plan (interdit dans
    notre cascade). PEA ≥ 5 ans → retrait partiel autorisé.
    """
    age = position.age_enveloppe_ans()
    return age is not None and age >= 5.0


# ─── Stubs d'extensibilité (S3.7 / S3.8) ─────────────────────────────────────


@dataclass
class Contrainte:
    """Contrainte de liquidité (stub pour S3.7)."""

    description: str
    enveloppe: str
    eligible_a_partir_de: str | None = None  # ISO 8601


def contraintes_liquidite(
    profil: dict[str, Any],
    date_t: datetime.date | None = None,
) -> list[Contrainte]:
    """
    Retourne les contraintes de liquidité pour le profil à la date date_t.

    TODO(S3.7) : implémenter les fenêtres d'éligibilité PEA 5 ans, AV 8 ans,
    PER déblocage anticipé (Art. L. 224-4 CMF), SCPI délai de cession, etc.
    """
    return []


# ─── Solveur MILP (PuLP) ──────────────────────────────────────────────────────


def _resoudre_milp(
    positions: list[Position],
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    regime_fiscal: str,
    abattement_av_restant: float,
    frais_courtage: float,
    bande_pp: float = 0.05,
) -> list[VentePlanifiee]:
    """
    Solveur MILP qui minimise coût_fiscal + frais_courtage + pénalité_dérive.

    Variables de décision : montant vendu par (ETF × enveloppe).
    Contraintes :
      - Nouvelle allocation ∈ bandes ±bande_pp par classe d'actifs
      - Respect des lots disponibles (montant_actuel)
      - PEA < 5 ans : vente interdite (clôture totale → hors cascade)
      - PER : vente interdite (Art. L. 224-4 CMF)

    Retourne la liste des ventes optimales.
    Retourne [] si PuLP n'est pas disponible (mode dégradé).
    """
    if not PULP_AVAILABLE:
        return []

    prob = pulp.LpProblem("rebalancement_optimal", pulp.LpMinimize)

    # Variables : montant vendu par position (≥ 0, ≤ montant_actuel)
    ventes_vars: dict[str, pulp.LpVariable] = {}
    for pos in positions:
        key = f"{pos.etf}__{pos.enveloppe}"
        max_montant = pos.montant_actuel
        # Contraintes légales
        if pos.enveloppe in ENVELOPPES_PER:
            max_montant = 0.0  # PER : sortie interdite
        elif pos.enveloppe in ENVELOPPES_PEA and not est_pea_eligible_retrait(pos):
            max_montant = 0.0  # PEA < 5 ans : clôture totale interdite
        ventes_vars[key] = pulp.LpVariable(
            f"v_{key}", lowBound=0, upBound=max_montant, cat="Continuous"
        )

    # Coût fiscal par position
    def _cout_fiscal_pos(pos: Position, var: pulp.LpVariable) -> pulp.LpAffineExpression:
        """Linéarisation du coût fiscal (approximation affine)."""
        if pos.plus_value_latente <= 0:
            return pulp.lpSum([])  # expression zéro compatible PuLP
        # Taux marginal de PV sur le montant vendu
        pv_pct = pos.plus_value_latente / pos.montant_actuel if pos.montant_actuel > 0 else 0.0
        if pos.enveloppe in ENVELOPPES_GRATUITES:
            taux = 0.0
        elif pos.enveloppe in ENVELOPPES_PEA:
            age = pos.age_enveloppe_ans()
            taux = TAUX_PEA_POST5ANS if (age and age >= 5.0) else TAUX_PFU
        elif pos.enveloppe in ENVELOPPES_AV:
            age = pos.age_enveloppe_ans()
            taux = TAUX_PFU if age is None or age < 8.0 else TAUX_PS
        else:
            taux = TAUX_PFU
        return var * pv_pct * taux

    # Fonction objectif : Σ coût_fiscal + Σ frais_courtage (proxy linéaire) + pénalité dérive
    # Note : frais_courtage est modélisé comme coût linéaire par unité vendue
    # (approximation d'un coût fixe, préserve la linéarité du MILP)
    objectif = pulp.lpSum(
        _cout_fiscal_pos(pos, ventes_vars[f"{pos.etf}__{pos.enveloppe}"])
        + (frais_courtage / max(pos.montant_actuel, 1)) * ventes_vars[f"{pos.etf}__{pos.enveloppe}"]
        for pos in positions
        if f"{pos.etf}__{pos.enveloppe}" in ventes_vars
    )
    # Pénalité sur dérive résiduelle (proxy linéaire)
    poids_penalty = 1000.0
    total_vendu = pulp.lpSum(ventes_vars.values())
    objectif += poids_penalty * total_vendu / (patrimoine_total + 1)
    prob += objectif

    # Contraintes : allocation résultante ∈ [cible - bande, cible + bande]
    for classe, poids_cible in allocation_cible.items():
        if classe == "commentaire":
            continue
        poids_actuel = allocation_actuelle.get(classe, 0.0)
        montant_actuel_classe = poids_actuel * patrimoine_total
        # On suppose que les ventes réduisent proportionnellement les classes
        # (simplification : chaque position vend de sa classe)
        # → contrainte sur le patrimoine résultant (approx.)
        borne_inf = (poids_cible - bande_pp) * (patrimoine_total - total_vendu)
        borne_sup = (poids_cible + bande_pp) * (patrimoine_total - total_vendu)
        prob += montant_actuel_classe - total_vendu * poids_actuel >= borne_inf
        prob += montant_actuel_classe - total_vendu * poids_actuel <= borne_sup

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):
        return []

    ventes: list[VentePlanifiee] = []
    for pos in positions:
        key = f"{pos.etf}__{pos.enveloppe}"
        var = ventes_vars.get(key)
        if var is None:
            continue
        montant = pulp.value(var)
        if montant is None or montant < 1.0:
            continue

        # Calcul de la PV réalisée selon méthode
        if regime_fiscal == "IS" or pos.enveloppe == "CTO_IS":
            pv = calculer_pv_fifo(montant, pos.lots, pos.cours_actuel)
            methode = "CTO_FIFO"
        else:
            pv = calculer_pv_cmp(montant, pos.prix_revient_moyen, pos.cours_actuel)
            methode = "CTO_CMP"

        if pos.enveloppe in ENVELOPPES_GRATUITES:
            cout = 0.0
            methode = "GRATUIT"
        elif pos.enveloppe in ENVELOPPES_PEA:
            age = pos.age_enveloppe_ans()
            cout = cout_fiscal_pea(pv, age)
            methode = "PEA_PS"
        elif pos.enveloppe in ENVELOPPES_AV:
            age = pos.age_enveloppe_ans()
            cout, _ = cout_fiscal_av(pv, age, abattement_av_restant)
            methode = "AV_ABATTEMENT"
        else:
            cout = cout_fiscal_cto_ir(pv) if regime_fiscal == "IR" else pv * 0.15

        ventes.append(
            VentePlanifiee(
                etf=pos.etf,
                enveloppe=pos.enveloppe,
                montant=montant,
                plus_value_realisee=pv,
                cout_fiscal=cout,
                frais_courtage=frais_courtage,
                methode=methode,
                detail=f"MILP : {montant:.0f} € de {pos.etf} ({pos.enveloppe})",
            )
        )

    return ventes


# ─── Étapes de la cascade ─────────────────────────────────────────────────────


def etape1_arbitrages_gratuits(
    positions: list[Position],
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    bande_pp: float = 0.05,
) -> list[dict[str, Any]]:
    """
    Étape 1 — Arbitrages intra-enveloppe GRATUITS.

    Pour chaque enveloppe exonérée (PEA, PER, AV, Contrat_Cap_IS) : on identifie
    les positions surpondérées et les classes sous-pondérées dans la même
    enveloppe, et on propose un arbitrage sans fiscalité.

    Retourne une liste de dict {enveloppe, vendre_etf, acheter_classe,
    montant, cout_fiscal, impact_pp}.
    """
    arbitrages: list[dict[str, Any]] = []

    enveloppes = {p.enveloppe for p in positions if p.enveloppe in ENVELOPPES_GRATUITES}

    # Identifier les classes surpondérées et sous-pondérées
    classes_surponderes = {
        k: (allocation_actuelle.get(k, 0.0) - v)
        for k, v in allocation_cible.items()
        if k != "commentaire" and (allocation_actuelle.get(k, 0.0) - v) > bande_pp
    }
    classes_sous_ponderees = [
        k
        for k, v in allocation_cible.items()
        if k != "commentaire" and (v - allocation_actuelle.get(k, 0.0)) > bande_pp
    ]

    if not classes_surponderes or not classes_sous_ponderees:
        return arbitrages

    for env in sorted(enveloppes):
        pos_env = [p for p in positions if p.enveloppe == env]
        if not pos_env:
            continue

        for pos in pos_env:
            # Chercher la classe surpondérée qui correspond à cet ETF
            # (simplification : on associe chaque position à la première classe surpondérée)
            if not classes_surponderes:
                break
            classe_sur = next(iter(classes_surponderes))
            derive = classes_surponderes[classe_sur]
            classe_cible = classes_sous_ponderees[0] if classes_sous_ponderees else "obligations"

            if pos.montant_actuel > 0:
                montant = min(pos.montant_actuel, abs(derive) * patrimoine_total)
                if montant < 100:
                    continue
                impact_pp = montant / patrimoine_total
                arbitrages.append(
                    {
                        "enveloppe": env,
                        "vendre_etf": pos.etf,
                        "acheter_classe": classe_cible,
                        "montant": round(montant, 2),
                        "cout_fiscal": 0.0,
                        "impact_pp": round(impact_pp * 100, 2),
                        "detail": (
                            f"✅ {env} : Vendre {montant:.0f} € {pos.etf} → "
                            f"acheter {classe_cible}    Coût : 0 €"
                        ),
                    }
                )

    return arbitrages


def etape2_flux(
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    versement_mensuel: float,
    nb_mois: int = 3,
) -> list[dict[str, Any]]:
    """
    Étape 2 — Réorientation des flux (versements) vers les classes sous-pondérées.

    Réutilise la logique de src/rebalancement_flux.py.
    Retourne la liste des flux recommandés sur nb_mois.
    """
    from src.rebalancement_flux import EtatPortefeuille, repartir_versement

    portef_kwargs = {
        k: v * patrimoine_total for k, v in allocation_actuelle.items() if k != "commentaire"
    }
    try:
        portefeuille = EtatPortefeuille(**portef_kwargs)
    except TypeError:
        # Clés non reconnues par EtatPortefeuille → on ignore
        portefeuille = EtatPortefeuille()

    cible_flux = {k: v for k, v in allocation_cible.items() if k != "commentaire"}
    versement_total = versement_mensuel * nb_mois
    rep = repartir_versement(portefeuille, cible_flux, versement_total)

    flux: list[dict[str, Any]] = []
    for classe, montant in rep.repartition.items():
        if montant < 1.0:
            continue
        flux.append(
            {
                "classe": classe,
                "montant": round(montant, 2),
                "horizon_mois": nb_mois,
                "cout_fiscal": 0.0,
                "detail": (
                    f"➡️ Orienter {montant:.0f} € vers {classe} (sur {nb_mois} mois)    Coût : 0 €"
                ),
            }
        )

    return flux


def etape3_ventes(
    positions: list[Position],
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    regime_fiscal: str,
    abattement_av_restant: float,
    frais_courtage: float,
    bande_pp: float = 0.05,
    utiliser_milp: bool = True,
) -> list[VentePlanifiee]:
    """
    Étape 3 — Ventes optimisées fiscalement si nécessaire.

    Cascade interne :
      3a. AV > 8 ans : abattement annuel
      3b. PEA ≥ 5 ans : PS 17,2 % uniquement
      3c. CTO/IR : CMP | CTO/IS : FIFO + tax-loss harvesting
      3d. PER : interdit (sauf cas limitatifs = non implémenté ici)

    Si PuLP disponible et utiliser_milp=True, délègue au solveur MILP.
    Sinon, applique la cascade manuelle.
    """
    if utiliser_milp and PULP_AVAILABLE:
        return _resoudre_milp(
            positions=positions,
            allocation_actuelle=allocation_actuelle,
            allocation_cible=allocation_cible,
            patrimoine_total=patrimoine_total,
            regime_fiscal=regime_fiscal,
            abattement_av_restant=abattement_av_restant,
            frais_courtage=frais_courtage,
            bande_pp=bande_pp,
        )

    # ── Cascade manuelle (fallback sans PuLP) ────────────────────────────────
    ventes: list[VentePlanifiee] = []
    derive = {
        k: allocation_actuelle.get(k, 0.0) - v
        for k, v in allocation_cible.items()
        if k != "commentaire"
    }

    classes_surponderes = {k for k, d in derive.items() if d > bande_pp}
    if not classes_surponderes:
        return []

    # Estimation du montant total à vendre (somme des excès)
    montant_a_vendre = sum(d * patrimoine_total for d in derive.values() if d > bande_pp)

    # Ordre de priorité fiscal
    ordre = [
        ("AV", "AV_ABATTEMENT"),
        ("PEA", "PEA_PS"),
        ("CTO_perso", "CTO_CMP" if regime_fiscal == "IR" else "CTO_FIFO"),
        ("CTO_IS", "CTO_FIFO"),
    ]

    reste_a_vendre = montant_a_vendre

    for enveloppe_id, methode in ordre:
        if reste_a_vendre < 1.0:
            break

        pos_list = [p for p in positions if p.enveloppe == enveloppe_id]
        for pos in sorted(pos_list, key=lambda p: p.plus_value_latente):
            if reste_a_vendre < 1.0:
                break

            # Contraintes légales
            if enveloppe_id in ENVELOPPES_PER:
                continue  # Art. L. 224-4 CMF
            if enveloppe_id in ENVELOPPES_PEA and not est_pea_eligible_retrait(pos):
                continue  # PEA < 5 ans

            montant = min(pos.montant_actuel, reste_a_vendre)
            if montant < 1.0:
                continue

            # Calcul PV
            if methode == "CTO_FIFO" or regime_fiscal == "IS":
                pv = calculer_pv_fifo(montant, pos.lots, pos.cours_actuel)
            else:
                pv = calculer_pv_cmp(montant, pos.prix_revient_moyen, pos.cours_actuel)

            # Calcul coût fiscal
            if enveloppe_id == "AV":
                age = pos.age_enveloppe_ans()
                cout, abatt_conso = cout_fiscal_av(pv, age, abattement_av_restant)
                abattement_av_restant = max(0.0, abattement_av_restant - abatt_conso)
            elif enveloppe_id == "PEA":
                age = pos.age_enveloppe_ans()
                cout = cout_fiscal_pea(pv, age)
            else:
                cout = cout_fiscal_cto_ir(pv)

            ventes.append(
                VentePlanifiee(
                    etf=pos.etf,
                    enveloppe=enveloppe_id,
                    montant=montant,
                    plus_value_realisee=pv,
                    cout_fiscal=cout,
                    frais_courtage=frais_courtage,
                    methode=methode,
                    detail=f"⚠️ {enveloppe_id} : Vendre {montant:.0f} € {pos.etf}",
                )
            )
            reste_a_vendre -= montant

    return ventes


# ─── Tax-loss harvesting ──────────────────────────────────────────────────────


def detecter_moins_values_latentes(positions: list[Position]) -> list[Position]:
    """
    Identifie les positions CTO avec des moins-values latentes.

    Art. 150-0 D CGI : les MV peuvent être imputées sur les PV de même nature
    réalisées dans la même année fiscale.
    """
    return [
        pos for pos in positions if pos.enveloppe in ENVELOPPES_CTO and pos.plus_value_latente < 0
    ]


def compenser_pv_mv(
    ventes: list[VentePlanifiee],
    positions: list[Position],
) -> list[VentePlanifiee]:
    """
    Tax-loss harvesting : compense les PV réalisées sur CTO par les MV latentes.

    Art. 150-0 D CGI : imputation des MV sur PV de même nature (même année).

    Modifie les coûts fiscaux des ventes CTO en tenant compte des MV disponibles.
    """
    mv_disponibles = sum(
        abs(pos.plus_value_latente) for pos in detecter_moins_values_latentes(positions)
    )
    if mv_disponibles <= 0:
        return ventes

    ventes_modifiees: list[VentePlanifiee] = []
    mv_restantes = mv_disponibles

    for vente in ventes:
        if vente.enveloppe in ENVELOPPES_CTO and vente.plus_value_realisee > 0 and mv_restantes > 0:
            compensation = min(vente.plus_value_realisee, mv_restantes)
            pv_nette = vente.plus_value_realisee - compensation
            nouveau_cout = cout_fiscal_cto_ir(pv_nette)
            mv_restantes -= compensation
            ventes_modifiees.append(
                VentePlanifiee(
                    etf=vente.etf,
                    enveloppe=vente.enveloppe,
                    montant=vente.montant,
                    plus_value_realisee=pv_nette,
                    cout_fiscal=nouveau_cout,
                    frais_courtage=vente.frais_courtage,
                    methode=vente.methode,
                    detail=(
                        vente.detail + f"\n     PV compensée par MV : {compensation:.0f} €  ✅"
                    ),
                )
            )
        else:
            ventes_modifiees.append(vente)

    return ventes_modifiees


# ─── Coût naïf (scénario de référence) ───────────────────────────────────────


def calculer_cout_naif(
    positions: list[Position],
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    bande_pp: float = 0.05,
) -> float:
    """
    Calcule le coût fiscal du scénario naïf (tout vendre/racheter en CTO au PFU).

    Sert de base de comparaison pour mesurer l'économie réalisée par l'optimiseur.
    """
    montant_a_vendre = sum(
        max(0.0, (allocation_actuelle.get(k, 0.0) - v) * patrimoine_total)
        for k, v in allocation_cible.items()
        if k != "commentaire" and (allocation_actuelle.get(k, 0.0) - v) > bande_pp
    )
    # Hypothèse naïve : 30 % de PV latente sur tout le montant vendu en CTO PFU
    return montant_a_vendre * 0.30 * TAUX_PFU


# ─── Point d'entrée principal ─────────────────────────────────────────────────


def optimiser_rebalancement(
    positions: list[Position],
    allocation_actuelle: dict[str, float],
    allocation_cible: dict[str, float],
    patrimoine_total: float,
    versement_mensuel: float = 0.0,
    regime_fiscal: str = "IR",
    abattement_av_restant: float = ABATTEMENT_AV_CELIBATAIRE,
    frais_courtage: float = 0.0,
    bande_pp: float = 0.05,
    utiliser_milp: bool = True,
    nb_mois_flux: int = 3,
    seuil_alerte_pp: float = 0.08,
    profil_code: str = "PROFIL_INCONNU",
    horizon_temporel: int = 0,
) -> PlanRebalancement:
    """
    Point d'entrée principal du rebalancement optimal (cascade 3 étapes).

    Parameters
    ----------
    positions
        Liste des positions détaillées du portefeuille.
    allocation_actuelle
        Poids actuels par classe d'actifs (somme ≈ 1).
    allocation_cible
        Poids cibles par classe d'actifs.
    patrimoine_total
        Valeur totale du portefeuille en €.
    versement_mensuel
        Versement mensuel prévu (€).
    regime_fiscal
        "IR" (particulier) ou "IS" (personne morale).
    abattement_av_restant
        Abattement AV annuel restant (€).
    frais_courtage
        Frais de courtage par transaction (€).
    bande_pp
        Bande de tolérance en points de pourcentage (défaut 5 pp).
    utiliser_milp
        True pour utiliser le solveur MILP PuLP si disponible.
    nb_mois_flux
        Horizon du plan de flux (mois).
    seuil_alerte_pp
        Seuil de dérive pour alerte événementielle (défaut 8 pp).
    profil_code
        Code du profil client (pour nommage du plan).
    horizon_temporel
        0 = optimisation à t. > 0 = multi-périodes (TODO S3.8).

    Returns
    -------
    PlanRebalancement
        Plan d'action complet.

    Notes
    -----
    TODO(S3.8) : quand horizon_temporel > 0, activer le solveur multi-périodes.
    """
    date_gen = datetime.date.today().isoformat()

    # Calcul des dérives
    derive_par_classe = {
        k: round((allocation_actuelle.get(k, 0.0) - v) * 100, 2)
        for k, v in allocation_cible.items()
        if k != "commentaire"
    }

    # Alerte événementielle
    derive_max = max((abs(d) for d in derive_par_classe.values()), default=0.0)
    alerte = derive_max > seuil_alerte_pp * 100

    plan = PlanRebalancement(
        date_generation=date_gen,
        profil_code=profil_code,
        derive_par_classe=derive_par_classe,
    )

    if not alerte and derive_max <= bande_pp * 100:
        # Allocation dans les bandes : aucune action nécessaire
        plan.allocation_atteinte = True
        plan.cout_fiscal_total = 0.0
        plan.cout_fiscal_naif = 0.0
        plan.economie_fiscale = 0.0
        return plan

    # ── Étape 1 : arbitrages gratuits ────────────────────────────────────────
    plan.arbitrages_gratuits = etape1_arbitrages_gratuits(
        positions=positions,
        allocation_actuelle=allocation_actuelle,
        allocation_cible=allocation_cible,
        patrimoine_total=patrimoine_total,
        bande_pp=bande_pp,
    )

    # ── Étape 2 : flux entrants ───────────────────────────────────────────────
    if versement_mensuel > 0:
        plan.flux_recommandes = etape2_flux(
            allocation_actuelle=allocation_actuelle,
            allocation_cible=allocation_cible,
            patrimoine_total=patrimoine_total,
            versement_mensuel=versement_mensuel,
            nb_mois=nb_mois_flux,
        )

    # ── Étape 3 : ventes si nécessaire ───────────────────────────────────────
    ventes = etape3_ventes(
        positions=positions,
        allocation_actuelle=allocation_actuelle,
        allocation_cible=allocation_cible,
        patrimoine_total=patrimoine_total,
        regime_fiscal=regime_fiscal,
        abattement_av_restant=abattement_av_restant,
        frais_courtage=frais_courtage,
        bande_pp=bande_pp,
        utiliser_milp=utiliser_milp,
    )

    # Tax-loss harvesting : compensation PV/MV sur CTO même année
    ventes = compenser_pv_mv(ventes, positions)
    plan.ventes = ventes

    # Calcul des coûts
    plan.cout_fiscal_total = sum(v.cout_fiscal for v in ventes)
    plan.cout_fiscal_naif = calculer_cout_naif(
        positions, allocation_actuelle, allocation_cible, patrimoine_total, bande_pp
    )
    plan.economie_fiscale = max(0.0, plan.cout_fiscal_naif - plan.cout_fiscal_total)
    plan.allocation_atteinte = len(ventes) > 0 or len(plan.arbitrages_gratuits) > 0
    plan.horizon_mois = nb_mois_flux if plan.flux_recommandes else 0

    return plan
