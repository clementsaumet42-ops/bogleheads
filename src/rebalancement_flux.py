"""
Rebalancement par flux (cash flow rebalancing).

Stratégie : orienter les nouveaux versements vers les classes sous-pondérées
pour ramener vers l'allocation cible, SANS VENDRE les positions existantes.
Avantage : aucune fiscalité déclenchée.

Compatible avec src/projection.py et src/glide_path.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class EtatPortefeuille:
    """Répartition actuelle du portefeuille par classe d'actifs (en €)."""
    actions_monde: float = 0.0
    actions_usa: float = 0.0
    actions_europe: float = 0.0
    actions_emergents: float = 0.0
    obligations: float = 0.0
    monetaire: float = 0.0
    or_: float = 0.0
    immobilier: float = 0.0
    matieres_premieres: float = 0.0

    @property
    def total(self) -> float:
        return sum(self.as_dict().values())

    def as_dict(self) -> dict[str, float]:
        return {
            "actions_monde": self.actions_monde,
            "actions_usa": self.actions_usa,
            "actions_europe": self.actions_europe,
            "actions_emergents": self.actions_emergents,
            "obligations": self.obligations,
            "monetaire": self.monetaire,
            "or_": self.or_,
            "immobilier": self.immobilier,
            "matieres_premieres": self.matieres_premieres,
        }

    def poids_actuels(self) -> dict[str, float]:
        """Poids ∈ [0, 1] de chaque classe."""
        if self.total <= 0:
            return {k: 0.0 for k in self.as_dict()}
        return {k: v / self.total for k, v in self.as_dict().items()}


@dataclass
class Ecart:
    """Écart entre poids actuel et poids cible d'une classe."""
    classe: str
    poids_actuel: float
    poids_cible: float
    montant_actuel: float
    montant_cible: float
    ecart_pct: float          # poids_cible - poids_actuel (peut être négatif si surpondéré)
    ecart_montant: float      # montant_cible - montant_actuel
    sous_pondere: bool        # True si ecart_pct > 0
    hors_bandes: bool         # True si dépasse les tolérances de Swedroe


@dataclass
class RepartitionFlux:
    """Répartition recommandée d'un versement entre les classes."""
    versement_total: float
    repartition: dict[str, float]          # {classe: montant à verser}
    ecarts_residuels: dict[str, float]     # écart restant après versement
    allocation_finale: dict[str, float]    # nouveaux poids après versement
    classes_rebalancees: list[str]
    classes_encore_hors_bandes: list[str]
    recommandation: str                    # texte explicatif
    necessite_vente: bool                  # True si flux insuffisant → vente conseillée


@dataclass
class ComparaisonFiscale:
    """Comparaison du coût fiscal rebalancement par flux vs par vente."""
    cout_fiscal_vente: float       # € d'impôts en cas de rebalancement par vente
    cout_fiscal_flux: float        # € d'impôts en cas de rebalancement par flux (= 0)
    economie_fiscale: float        # différence
    hypothese_pv_latente_pct: float
    enveloppe_consideree: str


def charger_config(
    chemin: str | Path = "config/rebalancement_flux.yaml",
) -> dict:
    """Charge les paramètres de rebalancement par flux."""
    return yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))


def calculer_ecarts(
    portefeuille: EtatPortefeuille,
    allocation_cible: dict[str, float],    # {classe: poids_cible ∈ [0,1]}
    config: dict | None = None,
) -> list[Ecart]:
    """
    Calcule les écarts classe par classe entre poids actuel et poids cible.
    Renvoie les écarts triés par magnitude décroissante.
    """
    cfg = config or charger_config()
    tol_abs = cfg["bandes_tolerance"]["tolerance_absolue"]
    tol_rel = cfg["bandes_tolerance"]["tolerance_relative"]

    poids_actuels = portefeuille.poids_actuels()
    montants_actuels = portefeuille.as_dict()
    total = portefeuille.total
    ecarts: list[Ecart] = []

    for classe, p_cible in allocation_cible.items():
        p_actuel = poids_actuels.get(classe, 0.0)
        montant_actuel = montants_actuels.get(classe, 0.0)
        montant_cible = total * p_cible
        ecart_pct = p_cible - p_actuel
        hors_bandes = (
            abs(ecart_pct) > tol_abs
            or (p_cible > 0 and abs(ecart_pct) / p_cible > tol_rel)
        )
        ecarts.append(Ecart(
            classe=classe,
            poids_actuel=p_actuel,
            poids_cible=p_cible,
            montant_actuel=montant_actuel,
            montant_cible=montant_cible,
            ecart_pct=ecart_pct,
            ecart_montant=montant_cible - montant_actuel,
            sous_pondere=ecart_pct > 0,
            hors_bandes=hors_bandes,
        ))

    ecarts.sort(key=lambda e: abs(e.ecart_pct), reverse=True)
    return ecarts


def repartir_versement(
    portefeuille: EtatPortefeuille,
    allocation_cible: dict[str, float],
    versement: float,
    config: dict | None = None,
) -> RepartitionFlux:
    """
    Répartit un versement entre les classes sous-pondérées de manière optimale.

    Algorithme :
    1. Calcule les écarts à l'allocation cible.
    2. Liste les classes sous-pondérées (ecart_pct > 0) triées par magnitude.
    3. Attribue le versement priorité par priorité :
       - Rattrape d'abord les classes les plus éloignées de la cible
       - Quand une classe atteint sa cible, passe à la suivante
    4. Si le versement dépasse le déficit cumulé (cas rare), répartit le surplus
       selon l'allocation_cible (cohérent avec un achat "proportionnel").
    5. Si le versement est insuffisant pour sortir toutes les classes des bandes
       → marque `necessite_vente=True` si dérive > seuil_derive_vente_absolue.

    Notes :
    - Ne vend JAMAIS. Si une classe est surpondérée, on ne touche pas.
    - Accepte `versement=0` (retourne simplement l'état actuel).
    """
    cfg = config or charger_config()
    ecarts = calculer_ecarts(portefeuille, allocation_cible, cfg)

    # Classes sous-pondérées uniquement
    sous_ponderees = [e for e in ecarts if e.sous_pondere and e.ecart_montant > 0]

    repartition: dict[str, float] = {c: 0.0 for c in portefeuille.as_dict()}

    if versement <= 0 or not sous_ponderees:
        # Rien à répartir, ou pas de classe sous-pondérée
        allocation_finale = portefeuille.poids_actuels().copy()
        return RepartitionFlux(
            versement_total=versement,
            repartition=repartition,
            ecarts_residuels={e.classe: e.ecart_montant for e in ecarts},
            allocation_finale=allocation_finale,
            classes_rebalancees=[],
            classes_encore_hors_bandes=[e.classe for e in ecarts if e.hors_bandes],
            recommandation=(
                "Aucune classe sous-pondérée, ou versement nul."
                if versement <= 0
                else "Pas de classe sous-pondérée détectée."
            ),
            necessite_vente=False,
        )

    deficit_total = sum(e.ecart_montant for e in sous_ponderees)
    restant = versement
    classes_rebalancees: list[str] = []

    if versement <= deficit_total:
        # Cas standard : on rattrape proportionnellement selon la magnitude de l'écart
        for e in sous_ponderees:
            part = e.ecart_montant / deficit_total
            attribue = min(versement * part, e.ecart_montant)
            repartition[e.classe] = attribue
            restant -= attribue
            if attribue >= e.ecart_montant * 0.95:
                classes_rebalancees.append(e.classe)
    else:
        # Versement > déficit : on comble tous les écarts, puis on répartit le surplus
        for e in sous_ponderees:
            repartition[e.classe] += e.ecart_montant
            restant -= e.ecart_montant
            classes_rebalancees.append(e.classe)
        # Surplus réparti selon allocation cible
        for classe, p_cible in allocation_cible.items():
            repartition[classe] += restant * p_cible

    # État final
    montants_finaux = {
        c: portefeuille.as_dict()[c] + repartition[c]
        for c in portefeuille.as_dict()
    }
    total_final = sum(montants_finaux.values())
    allocation_finale = {c: m / total_final for c, m in montants_finaux.items()}

    # Écarts résiduels
    ecarts_residuels = {
        c: (allocation_cible.get(c, 0.0) - allocation_finale[c]) * total_final
        for c in portefeuille.as_dict()
    }

    # Classes encore hors bandes après versement
    tol_abs = cfg["bandes_tolerance"]["tolerance_absolue"]
    tol_rel = cfg["bandes_tolerance"]["tolerance_relative"]
    classes_encore_hors = []
    for c, p_cible in allocation_cible.items():
        p_f = allocation_finale.get(c, 0.0)
        ecart = abs(p_cible - p_f)
        if ecart > tol_abs or (p_cible > 0 and ecart / p_cible > tol_rel):
            classes_encore_hors.append(c)

    # Recommandation textuelle
    seuil_vente = cfg.get("seuil_derive_vente_absolue", 0.15)
    derive_max = max((abs(e.ecart_pct) for e in ecarts), default=0.0)
    necessite_vente = derive_max > seuil_vente and bool(classes_encore_hors)

    if not classes_rebalancees:
        reco = "Aucune classe n'a pu être rebalancée."
    elif not classes_encore_hors:
        reco = (
            f"✅ Rebalancement optimal par flux. "
            f"{len(classes_rebalancees)} classe(s) ramenée(s) dans la cible."
        )
    elif necessite_vente:
        reco = (
            f"⚠️ Dérive max {derive_max:.1%} > seuil {seuil_vente:.0%}. "
            "Versements insuffisants : envisager un rebalancement par vente."
        )
    else:
        reco = (
            f"ℹ️ Versement réparti. {len(classes_encore_hors)} classe(s) "
            "encore hors bandes — sera résolu lors des prochains versements."
        )

    return RepartitionFlux(
        versement_total=versement,
        repartition=repartition,
        ecarts_residuels=ecarts_residuels,
        allocation_finale=allocation_finale,
        classes_rebalancees=classes_rebalancees,
        classes_encore_hors_bandes=classes_encore_hors,
        recommandation=reco,
        necessite_vente=necessite_vente,
    )


def simuler_versements_recurrents(
    portefeuille: EtatPortefeuille,
    allocation_cible: dict[str, float],
    versement_mensuel: float,
    nb_mois: int,
    config: dict | None = None,
) -> list[RepartitionFlux]:
    """
    Simule N mois de versements par flux successifs.
    Utile pour estimer en combien de mois on sort des bandes de tolérance.
    """
    cfg = config or charger_config()
    etat = EtatPortefeuille(**portefeuille.as_dict())
    historique: list[RepartitionFlux] = []
    for _ in range(nb_mois):
        rep = repartir_versement(etat, allocation_cible, versement_mensuel, cfg)
        # Mise à jour de l'état
        nouveaux = {
            c: etat.as_dict()[c] + rep.repartition[c]
            for c in etat.as_dict()
        }
        etat = EtatPortefeuille(**nouveaux)
        historique.append(rep)
    return historique


def comparer_cout_fiscal(
    montant_a_arbitrer: float,
    enveloppe: str,
    config: dict | None = None,
) -> ComparaisonFiscale:
    """
    Compare le coût fiscal d'un rebalancement par vente vs par flux.
    Pour le flux : coût = 0 (pas de cession).
    Pour la vente : coût = montant_a_arbitrer × pv_latente_pct × taux_fiscalite.
    """
    cfg = config or charger_config()
    pv_pct = cfg["hypothese_plus_value_latente_pct"]
    taux_table = cfg["taux_fiscalite_par_enveloppe"]
    taux = taux_table.get(enveloppe, 0.314)   # défaut : PFU CTO perso

    cout_vente = montant_a_arbitrer * pv_pct * taux
    return ComparaisonFiscale(
        cout_fiscal_vente=cout_vente,
        cout_fiscal_flux=0.0,
        economie_fiscale=cout_vente,
        hypothese_pv_latente_pct=pv_pct,
        enveloppe_consideree=enveloppe,
    )
