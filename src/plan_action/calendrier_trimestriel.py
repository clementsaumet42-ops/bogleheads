"""Calendrier trimestriel d'execution — cascade 12 mois (Bloc C de la roadmap).

Implemente la promesse n.2 du README : *rebalancement par les flux entrants
d'abord*.

Entree :
    allocation_cible       : dict[classe -> poids ∈ [0,1]]
    portefeuille_actuel    : EtatPortefeuille (montants par classe)
    flux_entrants_12m      : float (somme des versements prevus sur 12 mois)
    enveloppes_disponibles : list[str] (PEA, AV, CTO, PER...)
    config                 : dict charge depuis config/rebalancement_flux.yaml

Sortie :
    CalendrierTrimestriel avec 4 trimestres + chiffrage du cout fiscal evite.

Algorithme :
    1. Decoupe le flux 12m en 4 versements trimestriels egaux.
    2. Pour chaque trimestre, repartit le versement sur les classes
       sous-ponderees via repartir_versement().
    3. Si la derive maximale finale > seuil, propose un arbitrage par
       VENTE en privilegiant les enveloppes sans friction (PEA antériorité,
       AV > 8 ans, PEE débloqué).
    4. Chiffre le cout fiscal evite par rapport a un rebalancement naïf
       qui solderait l'ecart entierement par vente.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.rebalancement_flux import (
    EtatPortefeuille,
    calculer_ecarts,
    charger_config,
    repartir_versement,
)

# ── Friction fiscale par enveloppe (taux effectif sur PV en cas de vente) ─
# Ordre croissant = preference pour arbitrage.
ENVELOPPES_SANS_FRICTION = ("PEA_5ans", "AV_8ans_abattement", "PEE_debloque")
ENVELOPPES_AVEC_FRICTION = ("AV_UC", "CTO_perso", "PER", "CTO_IS")


@dataclass
class Versement:
    """Un versement trimestriel sur une enveloppe / une classe."""

    enveloppe: str
    classe: str
    montant: float
    justification: str


@dataclass
class Arbitrage:
    """Une vente recommandee si les flux ne suffisent pas a sortir des bandes."""

    enveloppe_source: str
    classe_vendue: str
    classe_achetee: str
    montant: float
    cout_fiscal_estime: float
    justification: str


@dataclass
class Trimestre:
    """Plan d'un trimestre de la cascade 12 mois."""

    numero: int  # 1 a 4
    mois_debut: int  # 0, 3, 6, 9 depuis t0
    versement_total: float
    versements: list[Versement] = field(default_factory=list)
    arbitrages: list[Arbitrage] = field(default_factory=list)
    derive_avant_pct: float = 0.0  # derive maximale avant ce trimestre
    derive_apres_pct: float = 0.0  # derive maximale apres ce trimestre
    classes_ramenees: list[str] = field(default_factory=list)


@dataclass
class CalendrierTrimestriel:
    """Plan complet de la cascade 12 mois."""

    trimestres: list[Trimestre]
    flux_total_12m: float
    derive_initiale_pct: float
    derive_finale_pct: float
    cout_fiscal_naif: float  # rebalancement immediat tout par vente
    cout_fiscal_optimise: float  # somme des arbitrages restants
    economie_realisee: float
    classes_ramenees_dans_cible: list[str]
    classes_encore_hors_bandes: list[str]
    recommandation: str

    def vers_dict(self) -> dict:
        """Dump dict-friendly pour persistance JSON."""
        return {
            "flux_total_12m": self.flux_total_12m,
            "derive_initiale_pct": self.derive_initiale_pct,
            "derive_finale_pct": self.derive_finale_pct,
            "cout_fiscal_naif": self.cout_fiscal_naif,
            "cout_fiscal_optimise": self.cout_fiscal_optimise,
            "economie_realisee": self.economie_realisee,
            "recommandation": self.recommandation,
            "classes_ramenees_dans_cible": list(self.classes_ramenees_dans_cible),
            "classes_encore_hors_bandes": list(self.classes_encore_hors_bandes),
            "trimestres": [
                {
                    "numero": t.numero,
                    "mois_debut": t.mois_debut,
                    "versement_total": t.versement_total,
                    "derive_avant_pct": t.derive_avant_pct,
                    "derive_apres_pct": t.derive_apres_pct,
                    "classes_ramenees": list(t.classes_ramenees),
                    "versements": [
                        {
                            "enveloppe": v.enveloppe,
                            "classe": v.classe,
                            "montant": v.montant,
                            "justification": v.justification,
                        }
                        for v in t.versements
                    ],
                    "arbitrages": [
                        {
                            "enveloppe_source": a.enveloppe_source,
                            "classe_vendue": a.classe_vendue,
                            "classe_achetee": a.classe_achetee,
                            "montant": a.montant,
                            "cout_fiscal_estime": a.cout_fiscal_estime,
                            "justification": a.justification,
                        }
                        for a in t.arbitrages
                    ],
                }
                for t in self.trimestres
            ],
        }


def _derive_max(portefeuille: EtatPortefeuille, allocation_cible: dict[str, float]) -> float:
    """Renvoie l'ecart max |poids_actuel - poids_cible| (en fraction, pas %)."""
    poids = portefeuille.poids_actuels()
    return max(
        (abs(allocation_cible.get(c, 0.0) - poids.get(c, 0.0)) for c in allocation_cible),
        default=0.0,
    )


def _affecter_versement_a_enveloppe(
    repartition_par_classe: dict[str, float],
    enveloppes_disponibles: list[str],
    eligibilite_classe_enveloppe: dict[str, list[str]] | None,
) -> list[Versement]:
    """Mappe un versement (par classe) sur des enveloppes.

    Si `eligibilite_classe_enveloppe` est None, on prend la 1re enveloppe
    de la liste (heuristique simple). Sinon on prend la 1re enveloppe
    eligible pour cette classe.
    """
    versements: list[Versement] = []
    for classe, montant in repartition_par_classe.items():
        if montant <= 0:
            continue
        eligibles = (
            eligibilite_classe_enveloppe.get(classe, enveloppes_disponibles)
            if eligibilite_classe_enveloppe
            else enveloppes_disponibles
        )
        # Premiere enveloppe disponible et eligible
        cible = next(
            (e for e in enveloppes_disponibles if e in eligibles),
            enveloppes_disponibles[0] if enveloppes_disponibles else "CTO_perso",
        )
        versements.append(
            Versement(
                enveloppe=cible,
                classe=classe,
                montant=montant,
                justification=f"Versement classe {classe} (sous-ponderee)",
            )
        )
    return versements


def _proposer_arbitrages(
    portefeuille: EtatPortefeuille,
    allocation_cible: dict[str, float],
    enveloppes_disponibles: list[str],
    enveloppes_sans_friction: tuple[str, ...],
    config: dict,
) -> list[Arbitrage]:
    """Propose des ventes pour solder les classes encore hors bandes.

    Privilegie les enveloppes sans friction (PEA antériorité, AV > 8 ans,
    PEE débloqué) avant les enveloppes taxables (CTO, AV < 8 ans).
    """
    ecarts = calculer_ecarts(portefeuille, allocation_cible, config)
    sur_ponderees = sorted(
        (e for e in ecarts if not e.sous_pondere and e.ecart_montant < 0),
        key=lambda e: e.ecart_montant,  # plus negatif = plus a vendre
    )
    sous_ponderees = sorted(
        (e for e in ecarts if e.sous_pondere and e.ecart_montant > 0),
        key=lambda e: -e.ecart_montant,
    )

    pv_pct = config.get("hypothese_plus_value_latente_pct", 0.30)
    taux_table = config.get("taux_fiscalite_par_enveloppe", {})

    # Choisit l'enveloppe-source : sans friction d'abord, sinon CTO_perso.
    def _choisir_enveloppe_source() -> str:
        for env in enveloppes_disponibles:
            if env in enveloppes_sans_friction:
                return env
        return (
            "CTO_perso" if "CTO_perso" not in enveloppes_disponibles else enveloppes_disponibles[0]
        )

    arbitrages: list[Arbitrage] = []
    # On apparie surponderees -> sousponderees jusqu'a equilibrer.
    for src in sur_ponderees:
        montant_a_arbitrer = -src.ecart_montant
        for dst in sous_ponderees:
            if dst.ecart_montant <= 0 or montant_a_arbitrer <= 0:
                continue
            transfert = min(montant_a_arbitrer, dst.ecart_montant)
            env_source = _choisir_enveloppe_source()
            taux = taux_table.get(env_source, 0.314)
            cout = transfert * pv_pct * taux
            justif = (
                f"Arbitrage : vente {src.classe} pour acheter {dst.classe}. "
                f"Source : {env_source}"
                + (" (sans friction)" if env_source in enveloppes_sans_friction else "")
            )
            arbitrages.append(
                Arbitrage(
                    enveloppe_source=env_source,
                    classe_vendue=src.classe,
                    classe_achetee=dst.classe,
                    montant=transfert,
                    cout_fiscal_estime=cout,
                    justification=justif,
                )
            )
            dst.ecart_montant -= transfert
            montant_a_arbitrer -= transfert
    return arbitrages


def _appliquer_versements(
    portefeuille: EtatPortefeuille, versements: list[Versement]
) -> EtatPortefeuille:
    """Renvoie un nouveau EtatPortefeuille avec les versements appliques."""
    montants = portefeuille.as_dict()
    for v in versements:
        if v.classe in montants:
            montants[v.classe] += v.montant
    return EtatPortefeuille(**montants)


def _appliquer_arbitrages(
    portefeuille: EtatPortefeuille, arbitrages: list[Arbitrage]
) -> EtatPortefeuille:
    """Applique les arbitrages (transfert de classe a classe, total constant)."""
    montants = portefeuille.as_dict()
    for a in arbitrages:
        if a.classe_vendue in montants:
            montants[a.classe_vendue] -= a.montant
        if a.classe_achetee in montants:
            montants[a.classe_achetee] += a.montant
    return EtatPortefeuille(**montants)


def generer_calendrier(
    portefeuille_actuel: EtatPortefeuille,
    allocation_cible: dict[str, float],
    flux_entrants_12m: float,
    enveloppes_disponibles: list[str] | None = None,
    eligibilite_classe_enveloppe: dict[str, list[str]] | None = None,
    enveloppes_sans_friction: tuple[str, ...] = ENVELOPPES_SANS_FRICTION,
    config: dict | None = None,
) -> CalendrierTrimestriel:
    """Genere la cascade trimestrielle 12 mois.

    Args:
        portefeuille_actuel: etat de depart par classe d'actifs.
        allocation_cible: {classe -> poids_cible ∈ [0,1]}.
        flux_entrants_12m: somme des versements prevus (epargne nouvelle) sur 12m.
        enveloppes_disponibles: liste ordonnee de preference des enveloppes
            (PEA, AV, CTO, PER...). Si None, defaut ["PEA","AV_UC","CTO_perso"].
        eligibilite_classe_enveloppe: {classe -> [enveloppes eligibles]}.
            Permet de forcer ex. "actions_emergents" hors PEA.
        enveloppes_sans_friction: enveloppes a privilegier en cas de vente.
        config: surcharge de config/rebalancement_flux.yaml.

    Returns:
        CalendrierTrimestriel pret a etre serialise / affiche.

    Raises:
        ValueError: si flux_entrants_12m < 0 ou allocation_cible vide.
    """
    if flux_entrants_12m < 0:
        raise ValueError(f"flux_entrants_12m doit etre >= 0, recu {flux_entrants_12m}")
    if not allocation_cible or sum(allocation_cible.values()) <= 0:
        raise ValueError("allocation_cible vide ou somme nulle")

    cfg = config or charger_config()
    enveloppes_disponibles = enveloppes_disponibles or ["PEA", "AV_UC", "CTO_perso"]
    versement_par_trimestre = flux_entrants_12m / 4.0

    derive_initiale = _derive_max(portefeuille_actuel, allocation_cible)
    portefeuille_courant = portefeuille_actuel
    trimestres: list[Trimestre] = []
    classes_ramenees_global: list[str] = []

    for q in range(4):
        derive_avant = _derive_max(portefeuille_courant, allocation_cible)

        # Etape 1 : repartir le versement trimestriel sur sous-ponderees
        rep = repartir_versement(
            portefeuille_courant,
            allocation_cible,
            versement_par_trimestre,
            cfg,
        )
        versements_q = _affecter_versement_a_enveloppe(
            {c: m for c, m in rep.repartition.items() if m > 0},
            enveloppes_disponibles,
            eligibilite_classe_enveloppe,
        )
        portefeuille_courant = _appliquer_versements(portefeuille_courant, versements_q)

        for c in rep.classes_rebalancees:
            if c not in classes_ramenees_global:
                classes_ramenees_global.append(c)

        derive_apres = _derive_max(portefeuille_courant, allocation_cible)
        trimestre = Trimestre(
            numero=q + 1,
            mois_debut=q * 3,
            versement_total=versement_par_trimestre,
            versements=versements_q,
            arbitrages=[],
            derive_avant_pct=derive_avant,
            derive_apres_pct=derive_apres,
            classes_ramenees=list(rep.classes_rebalancees),
        )
        trimestres.append(trimestre)

    # Etape 2 : si la derive finale depasse le seuil, on propose des arbitrages
    # sur le dernier trimestre.
    seuil_vente = cfg.get("seuil_derive_vente_absolue", 0.15)
    derive_finale = _derive_max(portefeuille_courant, allocation_cible)
    arbitrages: list[Arbitrage] = []
    if derive_finale > seuil_vente:
        arbitrages = _proposer_arbitrages(
            portefeuille_courant,
            allocation_cible,
            enveloppes_disponibles,
            enveloppes_sans_friction,
            cfg,
        )
        trimestres[-1].arbitrages = arbitrages
        portefeuille_courant = _appliquer_arbitrages(portefeuille_courant, arbitrages)
        trimestres[-1].derive_apres_pct = _derive_max(portefeuille_courant, allocation_cible)
        derive_finale = trimestres[-1].derive_apres_pct

    # Cout fiscal naif : on solderait l'ecart initial *total* en CTO_perso a 30% PFU.
    pv_pct = cfg.get("hypothese_plus_value_latente_pct", 0.30)
    taux_naif = cfg.get("taux_fiscalite_par_enveloppe", {}).get("CTO_perso", 0.314)
    ecarts_init = calculer_ecarts(portefeuille_actuel, allocation_cible, cfg)
    montant_a_arbitrer_naif = sum(abs(e.ecart_montant) for e in ecarts_init if not e.sous_pondere)
    cout_naif = montant_a_arbitrer_naif * pv_pct * taux_naif
    cout_optimise = sum(a.cout_fiscal_estime for a in arbitrages)
    economie = max(0.0, cout_naif - cout_optimise)

    classes_encore_hors = []
    tol_abs = cfg["bandes_tolerance"]["tolerance_absolue"]
    for c, p_cible in allocation_cible.items():
        p_actuel = portefeuille_courant.poids_actuels().get(c, 0.0)
        if abs(p_cible - p_actuel) > tol_abs:
            classes_encore_hors.append(c)

    if not classes_encore_hors:
        reco = (
            f"Cascade 12m suffisante : la cible est atteinte sur les bandes "
            f"de tolerance. Economie fiscale vs naif : {economie:,.0f} €."
        )
    elif arbitrages:
        reco = (
            f"Versements + {len(arbitrages)} arbitrage(s) necessaires. "
            f"Cout fiscal estime : {cout_optimise:,.0f} € (vs {cout_naif:,.0f} € naif). "
            f"Economie : {economie:,.0f} €."
        )
    else:
        reco = (
            f"Versements seuls : derive finale {derive_finale:.1%} reste sous "
            f"le seuil {seuil_vente:.0%}. Aucun arbitrage taxable necessaire. "
            f"Economie vs naif : {economie:,.0f} €."
        )

    return CalendrierTrimestriel(
        trimestres=trimestres,
        flux_total_12m=flux_entrants_12m,
        derive_initiale_pct=derive_initiale,
        derive_finale_pct=derive_finale,
        cout_fiscal_naif=cout_naif,
        cout_fiscal_optimise=cout_optimise,
        economie_realisee=economie,
        classes_ramenees_dans_cible=classes_ramenees_global,
        classes_encore_hors_bandes=classes_encore_hors,
        recommandation=reco,
    )
