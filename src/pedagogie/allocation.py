"""Explications pédagogiques pour le module d'allocation cible."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_allocation(
    poids: dict[str, float],
    profil: str,
    mode: str,
    contexte: dict[str, str] | None = None,
) -> list[Explication]:
    """Retourne les explications pédagogiques de l'allocation cible.

    Args:
        poids: Dictionnaire {classe_actif: poids} issu de l'optimiseur.
        profil: Profil d'aversion au risque (defensif, equilibre, dynamique, agressif).
        mode: Mode d'allocation ('simple' ou 'granulaire').
        contexte: Données contextuelles facultatives {nom_client, patrimoine_total, …}.

    Returns:
        Liste de 2 à 4 Explication selon le mode et les classes présentes.
    """
    ctx = contexte or {}
    explications: list[Explication] = []

    # ─── Explication 1 : choix du mode ───────────────────────────────────────
    if mode == "simple":
        poids_acwi = poids.get("actions_monde", poids.get("actions", 0.0))
        texte_court_mode = (
            f"Mode ACWI mondial choisi : {poids_acwi:.0%} sur un seul ETF monde "
            f"capi-pondéré pour le profil {profil}."
        )
        texte_long_mode = (
            f"Le mode Simple concentre l'exposition actions sur un unique ETF MSCI ACWI "
            f"(ou FTSE All-World), répliquant la capitalisation boursière mondiale : "
            f"~60 % États-Unis, ~28 % pays développés hors US, ~12 % marchés émergents. "
            f"Pour un profil {profil}, cette approche maximise la diversification à "
            f"moindre coût (TER ~0,12-0,22 %) sans nécessiter de rééquilibrage régional. "
            f"C'est l'approche recommandée par Vanguard et la philosophie Boglehead : "
            f"« Don't try to outguess the market's collective wisdom. »"
        )
        alt = (
            "Mode Granulaire (3 lignes US / Dev ex-US / EM) écarté : plus de flexibilité "
            "sur les contraintes régionales, mais complexité accrue et aucun avantage "
            "empirique démontré pour un profil standard."
        )
    else:
        texte_court_mode = (
            f"Mode Granulaire choisi : 3 lignes régionales (US / Développés ex-US / EM) "
            f"pour appliquer des contraintes personnalisées — profil {profil}."
        )
        texte_long_mode = (
            f"Le mode Granulaire décompose l'exposition mondiale en trois blocs : "
            f"actions US (S&P 500 / MSCI USA), actions développées hors US (MSCI World ex-USA) "
            f"et marchés émergents (MSCI EM). Ce mode est justifié lorsque l'investisseur "
            f"souhaite limiter la concentration US ou les marchés émergents. "
            f"Pour le profil {profil}, les contraintes personnalisées ont été intégrées "
            f"dans l'optimisation Markowitz."
        )
        alt = (
            "Mode Simple (ACWI 1 ligne) écarté car des contraintes régionales explicites "
            "sont définies dans le profil client."
        )

    explications.append(
        Explication(
            section="allocation.mode",
            titre=f"Pourquoi le mode {'Simple ACWI' if mode == 'simple' else 'Granulaire'} ?",
            texte_court=texte_court_mode,
            texte_long=texte_long_mode,
            source="Bogle, J. (2017). The Little Book of Common Sense Investing. Wiley.",
            alternative_ecartee=alt,
            variables_contexte=ctx,
        )
    )

    # ─── Explication 2 : poids actions ───────────────────────────────────────
    classes_actions = {
        "actions_monde",
        "actions_us",
        "actions_dev_ex_us",
        "actions_emergents",
        "actions",
        "immobilier_cote",
    }
    total_actions = sum(v for k, v in poids.items() if k in classes_actions)

    profil_descriptions = {
        "defensif": "protection du capital, horizon court terme",
        "equilibre": "compromis rendement/risque, horizon moyen terme",
        "dynamique": "croissance long terme, tolérance au risque élevée",
        "agressif": "maximisation du rendement, horizon > 15 ans",
    }
    descr = profil_descriptions.get(profil, "profil personnalisé")

    explications.append(
        Explication(
            section="allocation.poids_actions",
            titre=f"Pourquoi {total_actions:.0%} d'actions ?",
            texte_court=(
                f"L'exposition actions totale est de {total_actions:.0%} "
                f"pour un profil {profil} ({descr})."
            ),
            texte_long=(
                f"L'optimisation Markowitz — variance moyenne — a déterminé une exposition "
                f"actions de {total_actions:.0%} pour maximiser le ratio rendement/risque "
                f"dans les bornes du profil {profil} ({descr}). "
                f"Cette allocation respecte la règle Boglehead du glide-path : réduire "
                f"progressivement les actions avec l'âge (règle indicative : (âge − 10) / 100 "
                f"en obligations). "
                f"La diversification mondiale évite le biais domestique (home bias) "
                f"documenté par French & Poterba (1991)."
            ),
            formule="E[R_p] = Σ w_i · E[R_i], σ²_p = Σ_i Σ_j w_i · w_j · σ_ij",
            source=(
                "Markowitz, H. (1952). Portfolio Selection. "
                "Journal of Finance, 7(1), 77-91. "
                "French, K. & Poterba, J. (1991). Investor Diversification and International "
                "Equity Markets. American Economic Review, 81(2), 222-226."
            ),
            variables_contexte=ctx,
        )
    )

    # ─── Explication 3 : obligations si présentes ─────────────────────────────
    poids_oblig = poids.get("obligations_monde", poids.get("obligations", 0.0))
    if poids_oblig > 0.01:
        explications.append(
            Explication(
                section="allocation.obligations",
                titre=f"Pourquoi {poids_oblig:.0%} d'obligations ?",
                texte_court=(
                    f"Les obligations ({poids_oblig:.0%}) amortissent la volatilité "
                    f"et offrent une décorrélation en régime de crise."
                ),
                texte_long=(
                    f"Une poche obligataire de {poids_oblig:.0%} (obligations monde agrégées, "
                    f"couvertes en EUR) remplit deux rôles : réducteur de volatilité globale "
                    f"du portefeuille et actif refuge en régime « risk-off » (krach actions). "
                    f"La corrélation actions/obligations est historiquement négative en période "
                    f"de stress (−0,25 à −0,40 depuis 2000 selon Barclays Aggregate Index). "
                    f"Cette poche est idéalement logée en assurance-vie pour bénéficier "
                    f"de l'abattement annuel sur les intérêts (9 200 € couple, Art. 125-0 A CGI)."
                ),
                source=(
                    "Ilmanen, A. (2011). Expected Returns. Wiley. "
                    "Art. 125-0 A Code général des impôts."
                ),
                alternative_ecartee=(
                    "Obligations d'entreprises High Yield écartées : rendement supérieur "
                    "mais corrélation actions trop forte en période de stress."
                ),
                variables_contexte=ctx,
            )
        )

    # ─── Explication 4 : alternative 100 % US écartée ─────────────────────────
    if mode == "simple":
        explications.append(
            Explication(
                section="allocation.alternative_100_us",
                titre="Pourquoi pas 100 % US ?",
                texte_court=(
                    "L'allocation 100 % US offre +0,3 % d'espérance mais ajoute "
                    "+4 % de volatilité et un risque de change concentré."
                ),
                texte_long=(
                    "Sur les 15 dernières années (2009-2024), le S&P 500 a surperformé le "
                    "MSCI ACWI d'environ +2 % / an. Extrapoler cette surperformance serait "
                    "un biais de récence (recency bias) documenté par Kahneman & Tversky (1974). "
                    "Une concentration de 100 % sur les US implique : risque de change USD/EUR "
                    "non couvert, valorisation CAPE Shiller historiquement élevée (~35x en 2024) "
                    "et absence d'exposition aux marchés développés ex-US et émergents en phase "
                    "de rattrapage potentiel. "
                    f"Pour un profil {profil}, la diversification mondiale est préférable."
                ),
                source=(
                    "Kahneman, D. & Tversky, A. (1974). Judgment under Uncertainty: "
                    "Heuristics and Biases. Science, 185(4157), 1124-1131. "
                    "Shiller, R. (2000). Irrational Exuberance. Princeton University Press."
                ),
                alternative_ecartee=(
                    "100 % S&P 500 : rendement espéré légèrement supérieur historiquement, "
                    "écarté pour concentration géographique et risque de change."
                ),
                variables_contexte=ctx,
            )
        )

    return explications
