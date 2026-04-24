"""Explications pédagogiques pour l'audit patrimonial — S8.2c.

Ce module fournit :
- expliquer_concept_bps() : l'Explication du concept de "points de base" et capitalisation
- expliquer_opportunite(opp) : script de restitution EC→client pour une opportunité
"""

from __future__ import annotations

from src.audit.opportunite import Opportunite
from src.pedagogie.base import Explication


def expliquer_concept_bps() -> Explication:
    """Retourne l'explication pédagogique du concept de 'points de base' et capitalisation.

    Returns:
        Explication avec titre, texte court/long, formule, source et alternative_ecartee.
    """
    return Explication(
        section="audit.concept_bps",
        titre="Pourquoi les points de base (bps) comptent-ils sur 30 ans ?",
        texte_court=(
            "1 point de base = 0,01 %/an. Sur 30 ans, 10 bps d'économie annuelle "
            "sur 100 000 € représente plus de 5 600 € capitalisés."
        ),
        texte_long=(
            "Un point de base (bps) représente 0,01 % par an. C'est une unité de mesure "
            "standard en gestion de patrimoine pour comparer les frais et drag fiscaux.\n\n"
            "Le levier de capitalisation transforme ces petites économies annuelles en montants "
            "significatifs sur une longue période. Exemple canonique :\n"
            "- 10 bps/an d'économie sur 100 000 € = 100 €/an\n"
            "- Capitalisés sur 30 ans à 4 % = 5 609 €\n"
            "- Sur 500 000 € (portefeuille moyen de nos clients) = 28 045 €\n\n"
            "L'objectif de cet audit est d'identifier chaque levier actionnable — "
            "tracking difference, withholding tax, frais de contrat AV, frais broker, "
            "optimisation distribuant/capitalisant — et de les chiffrer avec précision "
            "pour permettre une décision éclairée."
        ),
        formule=(
            "Gain capitalisé = gain_annuel × ((1 + i)^N - 1) / i "
            "(annuité, taux i = 4%, horizon N = 30 ans)"
        ),
        source=(
            "Bogle, J. (2017). The Little Book of Common Sense Investing. Wiley. "
            "— Principe de l'investisseur passif : chaque fraction de coût compte"
        ),
        alternative_ecartee=(
            "Comparer uniquement les TER (frais de gestion affichés) sous-estime "
            "le coût réel. La tracking difference et la withholding tax ne sont pas "
            "reflétées dans le TER mais pèsent autant sur la performance nette."
        ),
    )


def expliquer_opportunite(opp: Opportunite) -> str:
    """Génère un script de restitution EC→client pour une opportunité.

    Le script est conçu pour être lu à haute voix lors d'une restitution client.
    Il intègre les données chiffrées de l'opportunité et la justification pédagogique.

    Args:
        opp: L'opportunité à expliquer.

    Returns:
        Texte du script de restitution (prêt à lire, en français).
    """
    levier_labels = {
        "tracking_difference": "tracking difference (écart de réplication)",
        "withholding_tax": "retenue à la source sur dividendes",
        "dist_vs_cap": "optimisation distribuant → capitalisant en CTO",
        "frais_contrat_av": "frais du contrat d'assurance-vie",
        "frais_broker": "frais de courtage",
    }
    levier_label = levier_labels.get(opp.levier, opp.levier)

    complexite_labels = {
        "faible": "simple à réaliser",
        "moyenne": "nécessite quelques démarches",
        "elevee": "démarche complexe mais documentée",
    }
    complexite_label = complexite_labels.get(opp.complexite, opp.complexite)

    confiance_label = {
        "haute": "chiffrage fiable",
        "moyenne": "estimation raisonnée",
        "basse": "ordre de grandeur",
    }.get(opp.confiance, opp.confiance)

    delai = opp.delai_mise_en_oeuvre_jours
    delai_label = f"{delai} jours environ" if delai <= 30 else f"environ {delai // 30} mois"

    script = (
        f"Sur le levier '{levier_label}', j'ai identifié l'opportunité suivante : "
        f"{opp.titre}.\n\n"
        f"En termes d'impact : {opp.gain_annuel_eur:,.0f} €/an d'économie, "
        f"soit {opp.gain_30ans_eur:,.0f} € capitalisés sur 30 ans à 4 % "
        f"(base de calcul : {opp.montant_concerne_eur:,.0f} €).\n\n"
        f"Comment on y arrive : {opp.formule}\n\n"
        f"Cette recommandation est {complexite_label} et actionnable en {delai_label}. "
        f"Le chiffrage est un {confiance_label}."
    )

    if opp.note_ec:
        script += f"\n\nPoint d'attention : {opp.note_ec}"

    if opp.contraintes:
        contraintes_str = " ; ".join(opp.contraintes[:3])
        script += f"\n\nConditions à vérifier : {contraintes_str}."

    return script
