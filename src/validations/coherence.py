"""Module S18-C — Validations croisées de cohérence du profil client.

Toutes les validations sont NON BLOQUANTES : elles produisent des avertissements
à titre indicatif, jamais des erreurs qui empêchent d'avancer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Avertissement:
    """Avertissement de cohérence, non bloquant."""

    cle: str
    severity: str  # "info" | "warning" | "danger"
    titre: str
    description: str
    suggestion: str | None
    pages_concernees: list[str] = field(default_factory=list)


# ─── Seuils des tranches TMI (barème IR 2026) ────────────────────────────────
# Revenu imposable par part au-delà duquel on entre dans la tranche
_SEUILS_TMI: dict[float, float] = {
    0.00: 0.0,
    0.11: 11_294.0,
    0.30: 28_797.0,
    0.41: 82_341.0,
    0.45: 177_106.0,
}


def _verif_patrimoine_vs_enveloppes(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 1 : Patrimoine total ≠ somme des enveloppes (>1% d'écart)."""
    patrimoine = profil.get("patrimoine_financier_total", 0.0) or 0.0
    enveloppes = profil.get("enveloppes_disponibles") or {}

    if patrimoine <= 0 or not enveloppes:
        return None

    somme_env = 0.0
    for v in enveloppes.values():
        if isinstance(v, (int, float)):
            somme_env += v
        elif isinstance(v, dict):
            somme_env += v.get("montant", 0.0) or 0.0

    if somme_env <= 0:
        return None

    ecart_relatif = abs(patrimoine - somme_env) / patrimoine
    if ecart_relatif > 0.01:
        ecart_eur = abs(patrimoine - somme_env)
        return Avertissement(
            cle="patrimoine_vs_enveloppes",
            severity="warning",
            titre="Écart patrimoine / enveloppes",
            description=(
                f"Le patrimoine total ({patrimoine:,.0f}€) diffère de la somme des enveloppes "
                f"({somme_env:,.0f}€) de {ecart_eur:,.0f}€ ({ecart_relatif:.1%})."
            ),
            suggestion="Vérifier la cohérence entre le patrimoine global et les montants par enveloppe.",
            pages_concernees=["04_Profil.py", "07_Asset_Location.py"],
        )
    return None


def _verif_tmi_vs_rfr(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 2 : TMI incohérente avec le RFR déclaré."""
    tmi = profil.get("tmi")
    rfr = profil.get("rfr_annuel") or profil.get("revenu_fiscal_reference")

    if tmi is None or rfr is None or rfr <= 0:
        return None

    # Trouver le seuil minimum pour la TMI déclarée (1 part, célibataire)
    seuil_min = _SEUILS_TMI.get(tmi, 0.0)
    if seuil_min <= 0:
        return None

    if rfr < seuil_min:
        tmi_pct = int(tmi * 100)
        return Avertissement(
            cle="tmi_vs_rfr",
            severity="warning",
            titre="TMI incohérente avec le RFR",
            description=(
                f"La TMI déclarée ({tmi_pct}%) implique un revenu imposable ≥ {seuil_min:,.0f}€, "
                f"mais le RFR est {rfr:,.0f}€."
            ),
            suggestion=(
                f"Vérifier la TMI (devrait être < {tmi_pct}% pour ce RFR) ou corriger le RFR saisi."
            ),
            pages_concernees=["04_Profil.py", "13_Simulateur_Fiscal.py"],
        )
    return None


def _verif_profil_risque_vs_horizon(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 3 : Profil risque incohérent avec l'horizon."""
    profil_risque = profil.get("profil_aversion_risque") or ""
    horizon = profil.get("horizon_annees") or profil.get("horizon")

    if not profil_risque or horizon is None:
        return None

    # "dynamique" avec horizon < 5 ans = incohérence
    profil_lower = profil_risque.lower()
    if "dynamique" in profil_lower and int(horizon) < 5:
        return Avertissement(
            cle="profil_risque_vs_horizon",
            severity="warning",
            titre="Profil risque incohérent avec l'horizon",
            description=(
                f"Un profil dynamique avec un horizon de {horizon} ans est risqué : "
                "horizon insuffisant pour absorber la volatilité actions."
            ),
            suggestion="Envisager un profil prudent ou équilibré pour cet horizon court.",
            pages_concernees=["03_Profilage.py", "05_Allocation.py"],
        )
    return None


def _verif_age_vs_objectif_retraite(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 4 : Âge + objectif retraite incohérents."""
    age = profil.get("age")
    age_retraite = profil.get("age_retraite_cible") or profil.get("age_retraite")

    if age is None or age_retraite is None:
        return None

    if int(age) >= int(age_retraite):
        return Avertissement(
            cle="age_vs_retraite",
            severity="info",
            titre="Objectif retraite déjà atteint",
            description=(
                f"L'âge actuel ({age} ans) est supérieur ou égal à l'âge cible de retraite "
                f"({age_retraite} ans)."
            ),
            suggestion="Vérifier l'objectif de retraite ou passer à une stratégie de décumulation.",
            pages_concernees=["04_Profil.py"],
        )
    return None


def _verif_capital_vs_frais_courtage(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 5 : Capital < frais courtage estimés × 10."""
    capital = profil.get("patrimoine_financier_total", 0.0) or 0.0
    frais = profil.get("frais_courtier_par_transaction", 0.0) or 0.0

    if capital <= 0 or frais <= 0:
        return None

    if capital < frais * 10:
        return Avertissement(
            cle="capital_vs_frais_courtage",
            severity="warning",
            titre="Frais courtage disproportionnés",
            description=(
                f"Le capital ({capital:,.0f}€) est inférieur à 10× les frais de courtage "
                f"({frais:,.0f}€/transaction). Les frais représentent plus de 10% du capital."
            ),
            suggestion="Vérifier la stratégie d'investissement ou négocier les frais de courtage.",
            pages_concernees=["04_Profil.py", "22_Plan_Execution.py"],
        )
    return None


def _verif_monetaire_horizon_long(profil: dict[str, Any]) -> Avertissement | None:
    """Règle 6 : Plus de 80% en monétaire avec horizon > 10 ans."""
    alloc = profil.get("allocation_cible_bogleheads") or {}
    horizon = profil.get("horizon_annees") or profil.get("horizon")

    if not alloc or horizon is None:
        return None

    # Extraire les poids selon structure dict ou objet
    if hasattr(alloc, "__dict__"):
        liquidites = getattr(alloc, "liquidites", 0.0) or 0.0
        obligations = getattr(alloc, "obligations", 0.0) or 0.0
    elif isinstance(alloc, dict):
        liquidites = alloc.get("liquidites", 0.0) or 0.0
        obligations = alloc.get("obligations", 0.0) or 0.0
    else:
        return None

    pct_monetaire = liquidites + obligations

    if pct_monetaire > 0.80 and int(horizon) > 10:
        return Avertissement(
            cle="monetaire_horizon_long",
            severity="warning",
            titre="Rendement réel négatif probable",
            description=(
                f"L'allocation a {pct_monetaire:.0%} en monétaire/obligations avec "
                f"un horizon de {horizon} ans. Compte tenu de l'inflation, le rendement réel "
                "pourrait être négatif."
            ),
            suggestion="Envisager une part actions plus élevée pour un horizon long terme.",
            pages_concernees=["05_Allocation.py"],
        )
    return None


# ─── Règles enregistrées ─────────────────────────────────────────────────────

_REGLES = [
    _verif_patrimoine_vs_enveloppes,
    _verif_tmi_vs_rfr,
    _verif_profil_risque_vs_horizon,
    _verif_age_vs_objectif_retraite,
    _verif_capital_vs_frais_courtage,
    _verif_monetaire_horizon_long,
]


def valider_coherence(profil: Any) -> list[Avertissement]:
    """Lance toutes les règles de cohérence sur le profil.

    Args:
        profil: Objet Profil (Pydantic) ou dict représentant le profil client.

    Returns:
        Liste d'Avertissement. Peut être vide si tout est cohérent.
    """
    # Normalisation : accepte dict ou objet Pydantic
    if hasattr(profil, "model_dump"):
        profil_dict = profil.model_dump()
    elif hasattr(profil, "__dict__"):
        profil_dict = dict(profil.__dict__)
    elif isinstance(profil, dict):
        profil_dict = profil
    else:
        return []

    avertissements: list[Avertissement] = []
    for regle in _REGLES:
        try:
            avert = regle(profil_dict)
            if avert is not None:
                avertissements.append(avert)
        except Exception:
            # Une règle ne doit jamais faire planter la page
            pass

    return avertissements
