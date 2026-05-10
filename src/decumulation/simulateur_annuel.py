"""Simulateur multi-annees de decumulation.

Projette une strategie de retrait sur 5 / 10 / 20 ans avec :
- croissance annuelle des enveloppes (rendement nominal)
- inflation du besoin annuel
- consommation progressive des bases capital / abattement
- detection annee d'epuisement par enveloppe
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.decumulation.optimiseur_retraits import (
    EnveloppeDecumulation,
    PlanDecumulation,
    optimiser_retraits_annuels,
)
from src.decumulation.regles_enveloppes import ContexteFiscal


@dataclass
class AnneeProjection:
    annee: int  # 1 = annee 1
    besoin_net_annee: float
    plan: PlanDecumulation
    valeur_patrimoine_debut: float
    valeur_patrimoine_fin: float


@dataclass
class ProjectionDecumulation:
    horizon_ans: int
    rendement_annuel: float
    inflation_annuelle: float
    annees: list[AnneeProjection] = field(default_factory=list)
    patrimoine_initial: float = 0.0
    patrimoine_final: float = 0.0
    cout_fiscal_cumule: float = 0.0
    annees_couvertes: int = 0
    enveloppes_epuisees: dict[str, int] = field(default_factory=dict)  # nom -> annee


def _appliquer_rendement(
    enveloppes: list[EnveloppeDecumulation], rendement: float
) -> list[EnveloppeDecumulation]:
    """Applique un rendement annuel : valeur croit, base capital constante."""
    out = []
    for env in enveloppes:
        nouvelle = EnveloppeDecumulation(
            nom=env.nom,
            type_=env.type_,
            valeur=env.valeur * (1 + rendement),
            versements_cumules=env.versements_cumules,  # base inchangee
            duree_detention_ans=env.duree_detention_ans + 1.0,
            versements_deduits_ratio=env.versements_deduits_ratio,
            versements_avant_2017_ratio=env.versements_avant_2017_ratio,
            pee_debloque=env.pee_debloque,
        )
        out.append(nouvelle)
    return out


def simuler_decumulation(
    enveloppes_initiales: list[EnveloppeDecumulation],
    besoin_net_annuel_initial: float,
    horizon_ans: int = 20,
    rendement_annuel: float = 0.04,
    inflation_annuelle: float = 0.02,
    contexte_initial: ContexteFiscal | None = None,
) -> ProjectionDecumulation:
    """Projection multi-annees de la decumulation.

    Args:
        enveloppes_initiales : etat de depart.
        besoin_net_annuel_initial : besoin annee 1, indexe inflation chaque annee.
        horizon_ans : duree de projection.
        rendement_annuel : rendement nominal (ex 0.04 = 4%).
        inflation_annuelle : indexation du besoin annuel.
        contexte_initial : contexte fiscal foyer (situation, TMI...).
    """
    contexte = contexte_initial or ContexteFiscal()
    enveloppes_courantes = [
        EnveloppeDecumulation(**e.__dict__) for e in enveloppes_initiales
    ]
    patrimoine_initial = sum(e.valeur for e in enveloppes_courantes)
    annees: list[AnneeProjection] = []
    cout_cumule = 0.0
    annees_couvertes = 0
    enveloppes_epuisees: dict[str, int] = {}

    besoin = besoin_net_annuel_initial
    for annee in range(1, horizon_ans + 1):
        valeur_debut = sum(e.valeur for e in enveloppes_courantes)
        # Reinit abattement annuel (consommation par annee fiscale)
        contexte_annee = ContexteFiscal(
            situation=contexte.situation,
            tmi=contexte.tmi,
            abattement_av_deja_utilise_annee=0.0,
            encours_av_total_foyer=sum(
                e.valeur for e in enveloppes_courantes if e.type_ == "AV"
            ),
        )
        plan = optimiser_retraits_annuels(
            besoin_net_annuel=besoin,
            enveloppes=enveloppes_courantes,
            contexte=contexte_annee,
        )
        # Met a jour les enveloppes
        enveloppes_courantes = list(plan.enveloppes_finales)
        # Detecte epuisement
        for env in enveloppes_courantes:
            if env.valeur <= 0.01 and env.nom not in enveloppes_epuisees:
                enveloppes_epuisees[env.nom] = annee
        # Croissance fin d'annee
        enveloppes_courantes = _appliquer_rendement(enveloppes_courantes, rendement_annuel)
        valeur_fin = sum(e.valeur for e in enveloppes_courantes)
        if plan.couverture_atteinte:
            annees_couvertes += 1
        cout_cumule += plan.cout_fiscal_total
        annees.append(
            AnneeProjection(
                annee=annee,
                besoin_net_annee=besoin,
                plan=plan,
                valeur_patrimoine_debut=valeur_debut,
                valeur_patrimoine_fin=valeur_fin,
            )
        )
        # Indexation besoin
        besoin *= 1 + inflation_annuelle
        # Stop si patrimoine < 1k€
        if valeur_fin < 1_000:
            break

    return ProjectionDecumulation(
        horizon_ans=horizon_ans,
        rendement_annuel=rendement_annuel,
        inflation_annuelle=inflation_annuelle,
        annees=annees,
        patrimoine_initial=patrimoine_initial,
        patrimoine_final=sum(e.valeur for e in enveloppes_courantes),
        cout_fiscal_cumule=cout_cumule,
        annees_couvertes=annees_couvertes,
        enveloppes_epuisees=enveloppes_epuisees,
    )
