"""Explications pédagogiques pour la cascade fiscale CTO/PEA/AV/PER."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_cascade_fiscale(
    enveloppe: str,
    montant: float,
    tmi: float,
) -> list[Explication]:
    """Retourne les explications pédagogiques de la fiscalité d'une enveloppe.

    Args:
        enveloppe: Identifiant de l'enveloppe ('CTO', 'PEA', 'AV', 'PER', 'PEA_PME').
        montant: Montant de plus-value ou de rachat en euros.
        tmi: Taux marginal d'imposition (ex: 0.30 pour 30 %).

    Returns:
        Liste d'au moins 2 Explication décrivant la cascade fiscale de l'enveloppe.
    """
    enveloppe_upper = enveloppe.upper()
    explications: list[Explication] = []

    if enveloppe_upper == "CTO":
        explications.extend(_expliquer_cto(montant, tmi))
    elif enveloppe_upper in ("PEA", "PEA_PME"):
        explications.extend(_expliquer_pea(montant, tmi))
    elif enveloppe_upper in ("AV", "AV_UC", "ASSURANCE_VIE"):
        explications.extend(_expliquer_av(montant, tmi))
    elif enveloppe_upper == "PER":
        explications.extend(_expliquer_per(montant, tmi))
    else:
        # Enveloppe générique
        explications.append(
            Explication(
                section=f"fiscalite.{enveloppe.lower()}",
                titre=f"Fiscalité enveloppe {enveloppe}",
                texte_court=f"Enveloppe {enveloppe} : règles fiscales spécifiques à analyser.",
                texte_long=(
                    f"L'enveloppe {enveloppe} est soumise à un régime fiscal "
                    "à préciser selon les caractéristiques du détenteur et du contrat. "
                    "Consultez un expert-comptable ou un CIF pour les règles applicables."
                ),
                source="CGI — Code général des impôts.",
            )
        )

    return explications


def _expliquer_cto(montant: float, tmi: float) -> list[Explication]:
    """Explication cascade fiscale CTO (PFU / barème IR)."""
    taux_pfu = 0.30  # 12,8 % IR + 17,2 % PS
    taux_ps = 0.172
    impot_pfu = montant * taux_pfu
    impot_bareme = montant * (tmi + taux_ps)
    option_bareme_avantageuse = tmi < 0.128

    return [
        Explication(
            section="fiscalite.cto_pfu",
            titre=f"CTO — PFU 30 % sur {montant:,.0f} €",
            texte_court=(
                f"Plus-value CTO de {montant:,.0f} € : PFU 30 % = {impot_pfu:,.0f} € d'impôt "
                f"(12,8 % IR + 17,2 % PS — Art. 200 A CGI)."
            ),
            texte_long=(
                f"Le Compte-Titres Ordinaire applique le prélèvement forfaitaire unique (PFU) "
                f"de 30 % sur les plus-values mobilières : 12,8 % d'impôt sur le revenu + "
                f"17,2 % de prélèvements sociaux (Art. 200 A CGI). "
                f"Sur une plus-value de {montant:,.0f} €, cela représente {impot_pfu:,.0f} € d'impôt. "
                f"L'option au barème progressif de l'IR est possible sur option irrévocable "
                f"(Art. 200 A II CGI) : à votre TMI {tmi:.0%}, cela donnerait "
                f"{impot_bareme:,.0f} € — {'avantageuse' if option_bareme_avantageuse else 'moins avantageuse que le PFU'}. "
                "Les moins-values sont imputables sur les plus-values de même nature sur 10 ans."
            ),
            formule="Impôt PFU = PV × (12,8 % + 17,2 %) = PV × 30 %",
            source=(
                "Art. 200 A Code général des impôts (PFU). "
                "Art. 150-0 A CGI (plus-values mobilières). "
                "Art. 150-0 D CGI (imputation des moins-values)."
            ),
            alternative_ecartee=(
                f"Option barème IR {'retenue car avantageuse (TMI < 12,8 %)' if option_bareme_avantageuse else 'écartée : PFU plus avantageux à ce niveau de TMI'}."
            ),
            gain_eur=round(impot_bareme - impot_pfu, 2) if option_bareme_avantageuse else None,
        ),
        Explication(
            section="fiscalite.cto_moins_values",
            titre="Optimisation par imputation des moins-values",
            texte_court=(
                "Les moins-values CTO sont reportables 10 ans — priorité aux cessions "
                "en moins-value pour réduire l'assiette taxable."
            ),
            texte_long=(
                "Lors d'un rebalancement CTO, la stratégie fiscalement optimale consiste "
                "à céder en priorité les lignes en moins-value latente pour créer des déficits "
                "imputables sur les plus-values de l'année ou des 10 années suivantes "
                "(Art. 150-0 D CGI). "
                "Cette technique de « tax-loss harvesting » est particulièrement efficace "
                "en fin d'année fiscale ou lors d'un rebalancement annuel. "
                "Attention : le délai de wash-sale (rachat du même actif dans les 30 jours) "
                "n'est pas encadré en France, mais il convient de changer d'ETF similaire "
                "pour éviter la requalification."
            ),
            source=(
                "Art. 150-0 D Code général des impôts (report moins-values). "
                "BOFIP BOI-RPPM-PVBMI-20-10-40."
            ),
        ),
    ]


def _expliquer_pea(montant: float, tmi: float) -> list[Explication]:
    """Explication cascade fiscale PEA (avant/après 5 ans)."""
    taux_ps = 0.172
    impot_avant_5ans = montant * (tmi + taux_ps)
    impot_apres_5ans = montant * taux_ps
    gain_5ans = impot_avant_5ans - impot_apres_5ans

    return [
        Explication(
            section="fiscalite.pea_apres_5_ans",
            titre=f"PEA après 5 ans — exonération IR sur {montant:,.0f} €",
            texte_court=(
                f"Après 5 ans, plus-values PEA exonérées d'IR. "
                f"PS 17,2 % seulement = {impot_apres_5ans:,.0f} € "
                f"(vs {impot_avant_5ans:,.0f} € avec IR — gain {gain_5ans:,.0f} €)."
            ),
            texte_long=(
                f"Après 5 ans de détention du PEA, les plus-values et dividendes sont "
                f"exonérés d'impôt sur le revenu (Art. 163 quinquies D CGI). "
                f"Seuls les prélèvements sociaux de 17,2 % (CSG 9,2 %, CRDS 0,5 %, "
                f"prélèvement de solidarité 7,5 %) sont dus. "
                f"Sur une plus-value de {montant:,.0f} €, l'impôt total est de {impot_apres_5ans:,.0f} € "
                f"vs {impot_avant_5ans:,.0f} € avant 5 ans (TMI {tmi:.0%} + PS). "
                f"L'économie fiscale est de {gain_5ans:,.0f} €. "
                "Le plafond de versement est de 150 000 € (PEA classique). "
                "Tout retrait avant 5 ans entraîne la clôture et la taxation au PFU 30 %."
            ),
            formule=f"Impôt PEA >5 ans = PV × 17,2 % (vs PV × ({tmi:.0%} + 17,2 %) avant 5 ans)",
            source=(
                "Art. 163 quinquies D Code général des impôts. "
                "Art. L. 221-30 Code monétaire et financier."
            ),
            gain_eur=round(gain_5ans, 2),
        ),
        Explication(
            section="fiscalite.pea_avant_5_ans",
            titre="PEA avant 5 ans — risque de clôture forcée",
            texte_court=(
                "Tout retrait PEA avant 5 ans entraîne la clôture : "
                f"taxation PFU 30 % sur {montant:,.0f} € = {montant * 0.30:,.0f} €."
            ),
            texte_long=(
                "Avant 5 ans, tout retrait (même partiel) entraîne la clôture obligatoire "
                "du PEA (Art. L. 221-32 CMF). La plus-value totale est alors soumise au PFU "
                "de 30 % (12,8 % IR + 17,2 % PS). "
                "Exceptions : licenciement, invalidité, retraite anticipée (Art. 163 quinquies D). "
                "Il est donc essentiel de ne placer dans le PEA que des sommes dont on n'aura "
                "pas besoin avant 5 ans. La date d'ouverture du PEA doit être anticipée : "
                "ouvrir le PEA tôt (même avec 1 €) pour faire courir le délai."
            ),
            source=("Art. L. 221-32 Code monétaire et financier. Art. 163 quinquies D CGI."),
        ),
    ]


def _expliquer_av(montant: float, tmi: float) -> list[Explication]:
    """Explication cascade fiscale assurance-vie."""
    abattement_couple = 9200.0
    taux_ps = 0.172
    taux_pfl = 0.075  # PFL 7,5 % après 8 ans
    montant_imposable = max(0.0, montant - abattement_couple)
    impot_av_8ans = montant_imposable * (taux_pfl + taux_ps)
    impot_cto = montant * (0.128 + taux_ps)
    gain_vs_cto = impot_cto - impot_av_8ans

    return [
        Explication(
            section="fiscalite.av_apres_8_ans",
            titre=f"AV après 8 ans — abattement {abattement_couple:,.0f} € couple",
            texte_court=(
                f"Rachat AV > 8 ans : abattement 9 200 € (couple) puis 7,5 % IR + 17,2 % PS "
                f"sur le gain. Économie estimée {gain_vs_cto:,.0f} € vs CTO."
            ),
            texte_long=(
                "L'assurance-vie de plus de 8 ans bénéficie d'un régime fiscal dérogatoire "
                "(Art. 125-0 A CGI) : abattement annuel de 4 600 € (célibataire) ou 9 200 € "
                "(couple marié/PACS) sur les gains, puis PFL 7,5 % IR + PS 17,2 %. "
                f"Sur un rachat de {montant:,.0f} € (dont {montant * 0.3:,.0f} € de gains estimés), "
                f"après abattement couple ({abattement_couple:,.0f} €), "
                f"l'impôt total est ≈ {impot_av_8ans:,.0f} € "
                f"vs {impot_cto:,.0f} € en CTO. "
                f"Gain fiscal estimé : {gain_vs_cto:,.0f} €. "
                "En transmission, les bénéficiaires désignés profitent d'un abattement de "
                "152 500 € chacun (Art. 990 I CGI) — hors succession."
            ),
            formule=("Impôt AV >8 ans = max(0, Gain − 9 200 €) × (7,5 % + 17,2 %)"),
            source=(
                "Art. 125-0 A Code général des impôts. "
                "Art. 990 I CGI (transmission AV). "
                "BOFIP BOI-RPPM-RCM-20-10-20-50."
            ),
            alternative_ecartee=(
                "Rachat avant 8 ans écarté : PFU 30 % sans abattement. "
                "Préférer attendre la 8e année pour optimiser fiscalement les rachats."
            ),
            gain_eur=round(gain_vs_cto, 2),
        ),
        Explication(
            section="fiscalite.av_transmission",
            titre="AV — levier de transmission patrimoniale",
            texte_court=(
                "Hors succession, abattement 152 500 € / bénéficiaire désigné "
                "(Art. 990 I CGI) — outil majeur de planification successorale."
            ),
            texte_long=(
                "Les capitaux décès versés aux bénéficiaires désignés d'un contrat AV "
                "bénéficient d'un abattement de 152 500 € par bénéficiaire (Art. 990 I CGI). "
                "Au-delà, prélèvement de 20 % jusqu'à 700 k€ puis 31,25 %. "
                "Pour les versements effectués avant 70 ans, cet avantage est total. "
                "Après 70 ans, les primes versées réintègrent l'actif successoral au-delà "
                "de 30 500 € (Art. 757 B CGI), mais les gains restent exonérés. "
                "La clause bénéficiaire doit être rédigée avec soin (démembrement possible)."
            ),
            source=("Art. 990 I CGI. Art. 757 B CGI. BOFIP BOI-ENR-DMTG-10-10-20."),
        ),
    ]


def _expliquer_per(montant: float, tmi: float) -> list[Explication]:
    """Explication cascade fiscale PER (déduction à l'entrée, imposition à la sortie)."""
    plafond_deduction = 35_194.0  # 2026
    economie_entree = min(montant, plafond_deduction) * tmi

    return [
        Explication(
            section="fiscalite.per_deduction",
            titre=f"PER — déduction {montant:,.0f} € du revenu imposable",
            texte_court=(
                f"Versement PER {montant:,.0f} € déductible du revenu imposable : "
                f"économie IR immédiate ≈ {economie_entree:,.0f} € (TMI {tmi:.0%})."
            ),
            texte_long=(
                f"Les versements volontaires sur PER individuel sont déductibles du revenu "
                f"imposable dans la limite de 10 % des revenus professionnels N-1 "
                f"(plafond 2026 : {plafond_deduction:,.0f} €, Art. 163 quatervicies CGI). "
                f"À votre TMI {tmi:.0%}, un versement de {montant:,.0f} € génère une économie "
                f"fiscale immédiate de {economie_entree:,.0f} €. "
                "À la sortie retraite, la rente ou le capital est imposé à l'IR (TMI souvent "
                "inférieure) + PS 17,2 % (taux réduit 7,5 % selon revenus). "
                "L'arbitrage PER vs AV dépend du différentiel TMI entrée/sortie."
            ),
            formule=(f"Économie IR = min(Versement, {plafond_deduction:,.0f} €) × TMI {tmi:.0%}"),
            source=(
                "Art. 163 quatervicies CGI (déduction PER). "
                "Art. L. 224-1 Code monétaire et financier. "
                "BOFIP BOI-RSA-PENS-30-10."
            ),
            gain_eur=round(economie_entree, 2),
        ),
        Explication(
            section="fiscalite.per_sortie",
            titre="PER — fiscalité à la sortie (retraite)",
            texte_court=(
                "À la retraite : capital issu de versements déductibles imposé à l'IR + PS. "
                "Avantage si TMI à la sortie < TMI à l'entrée."
            ),
            texte_long=(
                "À la sortie du PER, les sommes issues de versements déductibles sont "
                "imposées selon leur nature : "
                "(1) Rente viagère : imposée comme une pension de retraite (barème IR + PS 10,1 %). "
                "(2) Capital : fraction correspondant aux versements imposée à l'IR (barème), "
                "fraction correspondant aux gains imposée au PFU 30 % (Art. L. 224-22 CMF). "
                "L'arbitrage temporal (TMI élevée aujourd'hui, TMI réduite à la retraite) "
                "est le principal avantage du PER vs une épargne non défiscalisée. "
                "Cas particulier : déblocage anticipé pour achat résidence principale "
                "(Art. L. 224-4 CMF) — exonération d'IR sur les plus-values."
            ),
            source=(
                "Art. L. 224-22 Code monétaire et financier. "
                "Art. L. 224-4 CMF (déblocage anticipé). "
                "BOFIP BOI-RSA-PENS-30-10."
            ),
        ),
    ]
