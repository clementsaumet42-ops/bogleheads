"""Optimiseur d'ordre de retrait fiscal-optimal pour la decumulation.

Algorithme glouton :
    Pour atteindre un besoin annuel NET, retire d'abord sur l'enveloppe au
    taux marginal effectif le plus bas. Quand celle-ci est epuisee (ou que
    son taux marginal change), passe a la suivante.

Ne fait PAS de planification multi-annuelle (cf. simulateur_annuel.py pour
la projection 5/10/20 ans).

Principe-cle : on RECALCULE le taux marginal a chaque etape. Exemple :
- AV > 8 ans dans abattement : 17.2% (PS seuls)
- AV > 8 ans hors abattement, sous seuil 150k : 7.5% IR + 17.2% PS = 24.7%
- AV > 8 ans hors abattement, sur seuil 150k : 12.8% IR + 17.2% PS = 30%
Donc la meme enveloppe AV passe par 3 regimes successifs au cours du retrait.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.decumulation.regles_enveloppes import (
    ContexteFiscal,
    fiscalite_retrait,
)


@dataclass
class EnveloppeDecumulation:
    """Etat d'une enveloppe en phase de retrait."""

    nom: str  # libelle libre, ex. "PEA Antoine Bourse Direct"
    type_: str  # "PEA", "AV", "CTO", "PER", "PEE", "PERCOL"
    valeur: float  # valeur actuelle €
    versements_cumules: float  # base capital (pour ratio_pv)
    duree_detention_ans: float = 0.0
    versements_deduits_ratio: float = 1.0  # PER : part deduite a l'entree
    versements_avant_2017_ratio: float = 0.0  # AV : part avant 27/09/2017
    pee_debloque: bool = True

    @property
    def pv_latente(self) -> float:
        return max(0.0, self.valeur - self.versements_cumules)

    @property
    def ratio_pv(self) -> float:
        return self.pv_latente / self.valeur if self.valeur > 0 else 0.0

    def appliquer_retrait(self, montant_brut: float) -> EnveloppeDecumulation:
        """Renvoie une copie de l'enveloppe apres retrait (FIFO simplifie).

        On retire au prorata capital/PV : la base et la valeur diminuent
        proportionnellement. C'est l'hypothese standard pour AV et CTO ETF.
        """
        if montant_brut <= 0 or self.valeur <= 0:
            return self
        montant_brut = min(montant_brut, self.valeur)
        ratio_retrait = montant_brut / self.valeur
        return EnveloppeDecumulation(
            nom=self.nom,
            type_=self.type_,
            valeur=self.valeur - montant_brut,
            versements_cumules=self.versements_cumules * (1 - ratio_retrait),
            duree_detention_ans=self.duree_detention_ans,
            versements_deduits_ratio=self.versements_deduits_ratio,
            versements_avant_2017_ratio=self.versements_avant_2017_ratio,
            pee_debloque=self.pee_debloque,
        )


@dataclass
class Retrait:
    """Une operation de retrait sur une enveloppe."""

    enveloppe: str
    type_enveloppe: str
    montant_brut: float
    impot_ir: float
    prelevements_sociaux: float
    montant_net: float
    abattement_utilise: float
    taux_effectif: float
    details: str
    source_legale: str


@dataclass
class PlanDecumulation:
    """Plan annuel de retraits fiscal-optimal."""

    besoin_net_cible: float
    total_brut: float
    total_ir: float
    total_ps: float
    total_net: float
    cout_fiscal_total: float
    taux_effectif_global: float
    retraits: list[Retrait] = field(default_factory=list)
    enveloppes_finales: list[EnveloppeDecumulation] = field(default_factory=list)
    abattement_av_consomme: float = 0.0
    couverture_atteinte: bool = True
    deficit_residuel: float = 0.0
    avertissements: list[str] = field(default_factory=list)


def _taux_marginal(env: EnveloppeDecumulation, contexte: ContexteFiscal, pas: float) -> float:
    """Estime le taux effectif d'un retrait incremental sur cette enveloppe."""
    pas = min(pas, env.valeur)
    if pas <= 0:
        return float("inf")
    res = fiscalite_retrait(
        env.type_,
        pas,
        env.ratio_pv,
        contexte,
        env.duree_detention_ans,
        env.versements_deduits_ratio,
        env.versements_avant_2017_ratio,
        env.pee_debloque,
    )
    return res["taux_effectif"]


def _retirer_sur_enveloppe(
    env: EnveloppeDecumulation,
    contexte: ContexteFiscal,
    montant_brut: float,
) -> tuple[Retrait, EnveloppeDecumulation, ContexteFiscal]:
    """Effectue un retrait, renvoie l'op + nouvel etat env + nouveau contexte."""
    montant_brut = min(montant_brut, env.valeur)
    res = fiscalite_retrait(
        env.type_,
        montant_brut,
        env.ratio_pv,
        contexte,
        env.duree_detention_ans,
        env.versements_deduits_ratio,
        env.versements_avant_2017_ratio,
        env.pee_debloque,
    )
    nouvelle_env = env.appliquer_retrait(montant_brut)
    nouveau_contexte = ContexteFiscal(
        situation=contexte.situation,
        tmi=contexte.tmi,
        abattement_av_deja_utilise_annee=(
            contexte.abattement_av_deja_utilise_annee + res["abattement_utilise"]
        ),
        encours_av_total_foyer=contexte.encours_av_total_foyer
        - (montant_brut if env.type_ == "AV" else 0.0),
    )
    retrait = Retrait(
        enveloppe=env.nom,
        type_enveloppe=env.type_,
        montant_brut=montant_brut,
        impot_ir=res["ir"],
        prelevements_sociaux=res["ps"],
        montant_net=res["net"],
        abattement_utilise=res["abattement_utilise"],
        taux_effectif=res["taux_effectif"],
        details=res["details"],
        source_legale=res["source_legale"],
    )
    return retrait, nouvelle_env, nouveau_contexte


def optimiser_retraits_annuels(
    besoin_net_annuel: float,
    enveloppes: list[EnveloppeDecumulation],
    contexte: ContexteFiscal | None = None,
    pas_test_eur: float = 1_000.0,
    pas_iteration_eur: float = 5_000.0,
) -> PlanDecumulation:
    """Genere le plan de retraits annuel fiscal-optimal.

    Args:
        besoin_net_annuel : montant NET cible apres impots et PS (€).
        enveloppes : etats actuels des enveloppes disponibles.
        contexte : contexte foyer (situation, TMI, abattement deja utilise).
        pas_test_eur : montant utilise pour estimer le taux marginal.
        pas_iteration_eur : taille du retrait elementaire a chaque iteration.

    Returns:
        PlanDecumulation : sequence ordonnee de retraits.

    Algo :
        1. Pour chaque enveloppe disponible, calcule le taux marginal pour
           un pas test.
        2. Choisit l'enveloppe au taux le plus bas.
        3. Retire pas_iteration_eur dessus (ou solde si plus petit).
        4. Verifie si le NET cumule >= besoin_net_annuel. Si oui, stop.
        5. Sinon, recalcule les taux marginaux (le contexte AV a evolue
           car l'abattement annuel se consomme) et continue.
    """
    if besoin_net_annuel <= 0:
        return PlanDecumulation(
            besoin_net_cible=besoin_net_annuel,
            total_brut=0.0,
            total_ir=0.0,
            total_ps=0.0,
            total_net=0.0,
            cout_fiscal_total=0.0,
            taux_effectif_global=0.0,
            retraits=[],
            enveloppes_finales=list(enveloppes),
            couverture_atteinte=True,
            deficit_residuel=0.0,
        )

    contexte = contexte or ContexteFiscal()
    # Initialise encours_av_total_foyer si non fourni
    if contexte.encours_av_total_foyer == 0.0:
        contexte = ContexteFiscal(
            situation=contexte.situation,
            tmi=contexte.tmi,
            abattement_av_deja_utilise_annee=contexte.abattement_av_deja_utilise_annee,
            encours_av_total_foyer=sum(e.valeur for e in enveloppes if e.type_ == "AV"),
        )

    enveloppes_courantes = [EnveloppeDecumulation(**e.__dict__) for e in enveloppes]
    retraits: list[Retrait] = []
    total_net = 0.0
    avertissements: list[str] = []

    # Boucle d'iteration jusqu'a atteinte du besoin net
    max_iterations = int(besoin_net_annuel / pas_iteration_eur) * 4 + 50
    iteration = 0
    while total_net < besoin_net_annuel and iteration < max_iterations:
        iteration += 1
        # Calcule les taux marginaux pour chaque enveloppe non vide
        taux_par_env = []
        for idx, env in enumerate(enveloppes_courantes):
            if env.valeur <= 0.01:
                continue
            taux = _taux_marginal(env, contexte, pas_test_eur)
            taux_par_env.append((taux, idx))
        if not taux_par_env:
            avertissements.append(
                f"Toutes enveloppes epuisees, deficit residuel : "
                f"{besoin_net_annuel - total_net:,.0f} €"
            )
            break

        taux_par_env.sort(key=lambda t: t[0])
        _, idx_choisi = taux_par_env[0]
        env = enveloppes_courantes[idx_choisi]

        # Determine la taille du retrait : min(pas, solde, brut necessaire pour combler)
        # Estimation du brut necessaire = (besoin_restant) / (1 - taux_marginal)
        besoin_restant_net = besoin_net_annuel - total_net
        taux_marginal = taux_par_env[0][0]
        brut_estime = besoin_restant_net / max(0.01, 1 - taux_marginal)
        montant = min(pas_iteration_eur, env.valeur, brut_estime)

        if montant < 0.01:
            break

        retrait, nouvelle_env, nouveau_contexte = _retirer_sur_enveloppe(env, contexte, montant)
        retraits.append(retrait)
        enveloppes_courantes[idx_choisi] = nouvelle_env
        contexte = nouveau_contexte
        total_net += retrait.montant_net

    # Agregation
    total_brut = sum(r.montant_brut for r in retraits)
    total_ir = sum(r.impot_ir for r in retraits)
    total_ps = sum(r.prelevements_sociaux for r in retraits)
    cout_fiscal = total_ir + total_ps
    abattement_total = sum(r.abattement_utilise for r in retraits)
    couverture = total_net >= besoin_net_annuel * 0.999
    deficit = max(0.0, besoin_net_annuel - total_net)

    if not couverture:
        avertissements.append(
            f"Patrimoine insuffisant pour couvrir {besoin_net_annuel:,.0f} € net : "
            f"deficit {deficit:,.0f} €"
        )

    if abattement_total >= contexte.abattement_av_annuel * 0.99:
        avertissements.append(
            f"Abattement AV annuel ({contexte.abattement_av_annuel:,.0f} €) consomme integralement."
        )

    return PlanDecumulation(
        besoin_net_cible=besoin_net_annuel,
        total_brut=total_brut,
        total_ir=total_ir,
        total_ps=total_ps,
        total_net=total_net,
        cout_fiscal_total=cout_fiscal,
        taux_effectif_global=cout_fiscal / total_brut if total_brut > 0 else 0.0,
        retraits=retraits,
        enveloppes_finales=enveloppes_courantes,
        abattement_av_consomme=abattement_total,
        couverture_atteinte=couverture,
        deficit_residuel=deficit,
        avertissements=avertissements,
    )
