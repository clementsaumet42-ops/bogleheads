# -*- coding: utf-8 -*-
"""
Module de gestion des enveloppes d'investissement — France 2026.
Charge les enveloppes depuis le fichier enveloppes.yaml et fournit
des classes de calcul fiscal pour chaque enveloppe.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


# ---------------------------------------------------------------------------
# Chargement de la configuration des enveloppes
# ---------------------------------------------------------------------------

def charger_enveloppes(chemin: str | Path | None = None) -> list[dict]:
    """Charge la liste des enveloppes depuis le fichier YAML.

    Args:
        chemin: Chemin vers le fichier enveloppes.yaml. Si None, utilise le chemin par défaut.

    Returns:
        Liste de dictionnaires décrivant chaque enveloppe.
    """
    if chemin is None:
        racine = Path(__file__).resolve().parent.parent
        chemin = racine / "config" / "enveloppes.yaml"
    with open(chemin, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data.get("enveloppes", [])


# ---------------------------------------------------------------------------
# Dataclass Enveloppe
# ---------------------------------------------------------------------------

@dataclass
class Enveloppe:
    """Représentation d'une enveloppe d'investissement.

    Attributes:
        id: Identifiant unique de l'enveloppe (ex: 'pea', 'cto_perso').
        nom: Nom complet de l'enveloppe.
        type_juridique: Base légale et type juridique.
        plafond: Plafond de versements en euros (None si pas de plafond).
        eligibilite_etf: Description des ETFs éligibles.
        blocage: Indique si les fonds sont bloqués.
        duree_blocage_ans: Durée de blocage en années (0 si pas de blocage).
        taux_sortie: Taux d'imposition effectif à la sortie (pour calculs simplifiés).
        meta: Dictionnaire brut complet issu du YAML.
    """

    id: str
    nom: str
    type_juridique: str
    plafond: float | None
    eligibilite_etf: str
    blocage: bool
    duree_blocage_ans: int
    taux_sortie: float       # Taux effectif approximatif à la sortie
    meta: dict = field(default_factory=dict, repr=False)

    @classmethod
    def depuis_dict(cls, data: dict) -> "Enveloppe":
        """Construit une Enveloppe depuis un dictionnaire YAML.

        Args:
            data: Dictionnaire issu du YAML.

        Returns:
            Instance Enveloppe.
        """
        # Détermination du taux de sortie approximatif selon l'enveloppe
        taux_sortie = _extraire_taux_sortie(data)

        return cls(
            id=data.get("id", "inconnu"),
            nom=data.get("nom", ""),
            type_juridique=data.get("type_juridique", ""),
            plafond=data.get("plafond"),
            eligibilite_etf=data.get("eligibilite_etf", ""),
            blocage=bool(data.get("blocage", False)),
            duree_blocage_ans=int(data.get("duree_blocage_ans", 0)),
            taux_sortie=taux_sortie,
            meta=data,
        )

    def calculer_impot_sortie(self, gain: float, tmi: float = 0.30) -> float:
        """Calcule l'impôt à la sortie pour un gain donné.

        La fiscalité de sortie varie selon l'enveloppe :
        - CTO perso : PFU 31.4 %
        - CTO IS : IS 25 %
        - Contrat capi IS : IS sur PV réelle (approximatif)
        - PEA (après 5 ans) : PS 17.2 % (IR exonéré)
        - PER (avec déduction à l'entrée) : TMI + PS 10.3 % sur gains
        - PEE : PS 17.2 % uniquement (IR exonéré)

        Args:
            gain: Montant de la plus-value ou du gain en euros.
            tmi: Tranche Marginale d'Imposition du titulaire (utilisée pour PER).

        Returns:
            Montant d'impôt estimé en euros.
        """
        if gain <= 0:
            return 0.0

        env_id = self.id

        if env_id == "cto_perso":
            # PFU 31.4 % sur plus-value réalisée
            return round(gain * 0.314, 2)

        elif env_id == "cto_is":
            # IS 25 % (mark-to-market déjà payé annuellement — cet appel est pour la sortie nette)
            return round(gain * 0.25, 2)

        elif env_id == "contrat_capi_is":
            # IS sur PV réelle à la sortie (base forfaitaire déjà décomptée annuellement)
            return round(gain * 0.25, 2)

        elif env_id == "pea":
            # Après 5 ans : IR exonéré, PS 17.2 % (ou 18.6 % — À VALIDER)
            taux_ps = self.meta.get("fiscalite_sortie", {}).get("taux_effectif_sortie_apres_5ans", 0.172)
            return round(gain * taux_ps, 2)

        elif env_id == "per":
            # Avec déduction à l'entrée : TMI sur capital + PS 10.3 % sur gains
            # Approximation : TMI sur gains uniquement pour simplifier
            taux_ir_sortie = tmi
            taux_ps_per = 0.103
            return round(gain * (taux_ir_sortie + taux_ps_per), 2)

        elif env_id == "pee":
            # IR exonéré, PS 17.2 % uniquement
            taux_sortie_pee = self.meta.get("fiscalite_sortie", {}).get("taux_effectif_sortie", 0.172)
            return round(gain * taux_sortie_pee, 2)

        else:
            # Fallback : utilisation du taux de sortie générique
            return round(gain * self.taux_sortie, 2)

    def est_eligible_etf(self, isin: str | None = None, domicile: str | None = None) -> bool:
        """Vérifie si un ETF est potentiellement éligible à cette enveloppe.

        Note : Vérification simplifiée — une analyse complète nécessiterait
        de croiser avec les règles d'éligibilité détaillées (synthétique PEA, etc.).

        Args:
            isin: ISIN de l'ETF (non utilisé pour l'instant).
            domicile: Domicile de l'ETF (France, Irlande, Luxembourg…).

        Returns:
            True si potentiellement éligible.
        """
        # Vérification basique basée sur le domicile pour le PEA
        if self.id == "pea" and domicile and domicile.lower() not in (
            "france", "luxembourg", "irlande", "ireland", "belgique",
        ):
            # Hors UE — probablement non éligible sauf structure synthétique
            return False
        return True


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def _extraire_taux_sortie(data: dict) -> float:
    """Extrait le taux de sortie approximatif depuis les données YAML.

    Args:
        data: Dictionnaire YAML d'une enveloppe.

    Returns:
        Taux effectif de sortie (entre 0 et 1).
    """
    fiscalite_sortie = data.get("fiscalite_sortie", {})
    if isinstance(fiscalite_sortie, dict):
        # Recherche du taux effectif dans les clés possibles
        for clef in ("taux_effectif_moyen", "taux_effectif_sortie", "taux_effectif_sortie_apres_5ans"):
            valeur = fiscalite_sortie.get(clef)
            if valeur is not None and isinstance(valeur, (int, float)):
                return float(valeur)
    # Valeur par défaut : PFU 31.4 %
    return 0.314


def charger_toutes_enveloppes(chemin: str | Path | None = None) -> dict[str, Enveloppe]:
    """Charge toutes les enveloppes et les retourne dans un dictionnaire indexé par ID.

    Args:
        chemin: Chemin vers le fichier YAML. Si None, utilise le chemin par défaut.

    Returns:
        Dictionnaire {id_enveloppe: Enveloppe}.
    """
    enveloppes_raw = charger_enveloppes(chemin)
    return {
        env["id"]: Enveloppe.depuis_dict(env)
        for env in enveloppes_raw
        if "id" in env
    }


def calculer_avantage_fiscal_vs_cto(
    enveloppe: Enveloppe,
    gain: float,
    tmi: float = 0.30,
) -> dict:
    """Calcule l'avantage fiscal d'une enveloppe par rapport au CTO personne physique.

    Permet de quantifier le gain fiscal en choisissant une enveloppe optimisée
    plutôt que le CTO standard (référence naïve).

    Args:
        enveloppe: Enveloppe à évaluer.
        gain: Gain (plus-value) hypothétique en euros.
        tmi: TMI du contribuable (pour le PER).

    Returns:
        Dictionnaire avec impôt CTO, impôt enveloppe et économie réalisée.
    """
    # Référence : PFU 31.4 % en CTO perso
    impot_cto = round(gain * 0.314, 2)
    impot_enveloppe = enveloppe.calculer_impot_sortie(gain, tmi)
    economie = round(impot_cto - impot_enveloppe, 2)

    return {
        "enveloppe": enveloppe.nom,
        "gain": gain,
        "impot_cto_reference": impot_cto,
        "impot_enveloppe": impot_enveloppe,
        "economie_fiscale": economie,
        "taux_effectif_enveloppe": round(impot_enveloppe / gain, 4) if gain > 0 else 0.0,
    }
