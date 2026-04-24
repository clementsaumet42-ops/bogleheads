"""Explications pédagogiques pour l'asset location (placement par enveloppe)."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_asset_location(
    matrice: list[dict],
    tmi: float,
) -> list[Explication]:
    """Retourne les explications pédagogiques de l'asset location.

    Args:
        matrice: Liste de dict {classe, enveloppe, montant, gain_eur} décrivant
                 la ventilation optimisée classe × enveloppe.
        tmi: Taux marginal d'imposition du client (ex: 0.30 pour 30 %).

    Returns:
        Liste d'au moins 2 Explication (obligations en AV, actions en PEA, …).
    """
    explications: list[Explication] = []

    # ─── Détection des placements significatifs dans la matrice ──────────────
    lignes_av = [
        e for e in matrice if e.get("enveloppe", "").upper() in ("AV", "AV_UC", "ASSURANCE_VIE")
    ]
    lignes_pea = [e for e in matrice if e.get("enveloppe", "").upper() == "PEA"]
    lignes_cto = [
        e for e in matrice if e.get("enveloppe", "").upper() in ("CTO", "CTO_PERSO", "CTO_IS")
    ]
    lignes_per = [e for e in matrice if e.get("enveloppe", "").upper() == "PER"]

    # Gain moyen estimé si non fourni
    def _gain(lignes: list[dict]) -> float:
        gains = [e.get("gain_eur", 0.0) for e in lignes if e.get("gain_eur")]
        return sum(gains) / len(gains) if gains else 0.0

    # ─── Explication 1 : obligations en AV ───────────────────────────────────
    classes_oblig_av = [
        e
        for e in lignes_av
        if "obligation" in e.get("classe", "").lower() or "bond" in e.get("classe", "").lower()
    ]
    gain_oblig_av = _gain(classes_oblig_av) if classes_oblig_av else _gain(lignes_av)

    explications.append(
        Explication(
            section="asset_location.obligations_av",
            titre="Pourquoi les obligations en assurance-vie ?",
            texte_court=(
                "Les coupons obligataires en AV > 8 ans bénéficient de l'abattement "
                f"annuel de 4 600 € (9 200 € couple) — quasi-exonération à votre TMI {tmi:.0%}."
            ),
            texte_long=(
                "En assurance-vie de plus de 8 ans, les gains (intérêts et plus-values) "
                "supportent le prélèvement forfaitaire libératoire de 7,5 % (IR) + PS 17,2 % "
                "après abattement annuel de 4 600 € (célibataire) ou 9 200 € (couple marié/PACS), "
                "en vertu de l'article 125-0 A du CGI. "
                f"À votre TMI de {tmi:.0%}, loger les obligations en AV plutôt qu'en CTO "
                f"génère une économie fiscale estimée à {gain_oblig_av:,.0f} € / an. "
                "De plus, la transmission hors succession (art. 990 I CGI) amplifie "
                "l'avantage pour la planification patrimoniale."
            ),
            source=(
                "Art. 125-0 A Code général des impôts. "
                "Art. 990 I CGI (transmission AV). "
                "BOFIP BOI-RPPM-RCM-20-10-20-50."
            ),
            alternative_ecartee=(
                "CTO (PFU 30 %) écarté pour les obligations : imposition annuelle des coupons "
                "sans abattement ni report, moins efficace fiscalement qu'une AV > 8 ans."
            ),
            gain_eur=round(gain_oblig_av, 2) if gain_oblig_av else None,
        )
    )

    # ─── Explication 2 : actions en PEA ──────────────────────────────────────
    gain_pea = _gain(lignes_pea)
    explications.append(
        Explication(
            section="asset_location.actions_pea",
            titre="Pourquoi les actions éligibles dans le PEA ?",
            texte_court=(
                "Après 5 ans, les plus-values PEA sont exonérées d'IR (PS 17,2 % seulement) "
                f"vs PFU 30 % en CTO — gain fiscal {gain_pea:,.0f} € estimé."
                if gain_pea
                else (
                    "Après 5 ans, les plus-values PEA sont exonérées d'IR "
                    "(PS 17,2 % seulement) vs PFU 30 % en CTO."
                )
            ),
            texte_long=(
                "Le Plan d'Épargne en Actions (PEA) offre une exonération d'impôt sur le revenu "
                "sur les plus-values et dividendes après 5 ans de détention "
                "(Art. 163 quinquies D CGI). Seuls les prélèvements sociaux de 17,2 % s'appliquent. "
                f"Pour un contribuable à {tmi:.0%} de TMI + PS, le différentiel vs CTO (PFU 30 %) "
                f"atteint {tmi:.0%} × plus-value. "
                "Le plafond de versement est de 150 000 € (PEA classique) + 75 000 € (PEA-PME). "
                "Les ETF éligibles doivent être domiciliés en UE/EEE et exposés à ≥ 75 % d'actions "
                "européennes (ou synthétiques éligibles via swap)."
            ),
            source=(
                "Art. 163 quinquies D Code général des impôts (PEA). "
                "Art. L. 221-30 Code monétaire et financier."
            ),
            alternative_ecartee=(
                "CTO écarté pour les actions éligibles PEA : imposition PFU 30 % dès cession, "
                "sans capitalisation fiscalement différée."
            ),
            gain_eur=round(gain_pea, 2) if gain_pea else None,
        )
    )

    # ─── Explication 3 : CTO en dernier recours ──────────────────────────────
    if lignes_cto:
        explications.append(
            Explication(
                section="asset_location.cto_dernier_recours",
                titre="Pourquoi certains actifs restent en CTO ?",
                texte_court=(
                    "Le CTO accueille les actifs non éligibles PEA/AV et les positions "
                    "excédant les plafonds. La PFU 30 % s'applique à la cession."
                ),
                texte_long=(
                    "Le Compte-Titres Ordinaire est l'enveloppe résiduelle, sans plafond de "
                    "versement ni contrainte d'éligibilité. Il accueille les ETF non éligibles PEA "
                    "(ex. ETF actions hors UE, matières premières, obligations hors zone €), "
                    "les positions excédant le plafond PEA (150 k€), et les actifs d'un investisseur "
                    "personne morale (IS). "
                    "La fiscalité applicable est le PFU 12,8 % IR + PS 17,2 % = 30 % "
                    "(Art. 200 A CGI), avec option barème IR si TMI < 12,8 %."
                ),
                source=(
                    "Art. 200 A Code général des impôts (PFU). "
                    "Art. 150-0 A CGI (plus-values mobilières)."
                ),
            )
        )

    # ─── Explication 4 : PER si présent ──────────────────────────────────────
    if lignes_per:
        gain_per = _gain(lignes_per)
        explications.append(
            Explication(
                section="asset_location.per_deduction",
                titre="Pourquoi utiliser le PER pour la retraite ?",
                texte_court=(
                    f"Les versements PER sont déductibles jusqu'à {tmi:.0%} de votre "
                    "revenu imposable — levier fiscal immédiat."
                ),
                texte_long=(
                    "Le Plan d'Épargne Retraite (PER individuel, art. L. 224-1 CMF) permet "
                    f"de déduire les versements du revenu imposable (plafond 10 % des revenus, "
                    f"max 35 194 € en 2026). À votre TMI {tmi:.0%}, chaque euro versé génère "
                    f"{tmi:.0%} d'économie fiscale immédiate. "
                    "À la sortie (retraite), les rentes sont imposées à l'IR (souvent TMI réduite) "
                    "+ PS 17,2 %. Le différé de fiscalité est favorable si le TMI à l'entrée "
                    "dépasse le TMI à la sortie."
                ),
                source=(
                    "Art. L. 224-1 Code monétaire et financier (PER). "
                    "Art. 163 quatervicies CGI (déduction versements PER). "
                    "BOFIP BOI-RSA-PENS-30-10."
                ),
                gain_eur=round(gain_per, 2) if gain_per else None,
            )
        )

    return explications
