"""Explications pédagogiques pour le choix d'un ETF."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_choix_etf(
    etf: dict,
    alternatives_ecartees: list[dict] | None = None,
) -> Explication:
    """Retourne l'explication pédagogique du choix d'un ETF.

    Args:
        etf: Dictionnaire décrivant l'ETF retenu (ticker, ter, domicile,
             methode_replication, eligibilite, aum_mds, td_3y, …).
        alternatives_ecartees: Liste de dict décrivant les ETF non retenus
                               avec au moins {ticker, raison}.

    Returns:
        Une Explication détaillant le choix de l'ETF.
    """
    ticker = etf.get("ticker", "—")
    ter = etf.get("ter", 0.0)
    domicile = etf.get("domicile", "—")
    replication = etf.get("methode_replication", "physique")
    aum_mds = etf.get("aum_mds")
    td_3y = etf.get("td_3y")

    # Éligibilité
    eligibilite = etf.get("eligibilite", {})
    enveloppes = [k for k, v in eligibilite.items() if v] if isinstance(eligibilite, dict) else []
    enveloppes_str = ", ".join(enveloppes) if enveloppes else "CTO"

    # Texte
    aum_str = f", AUM {aum_mds:.1f} Mds€" if aum_mds is not None else ""
    td_str = f", tracking difference 3 ans : {td_3y:+.2%}" if td_3y is not None else ""

    texte_court = (
        f"{ticker} retenu : TER {ter:.2%}, domicile {domicile}, "
        f"réplication {replication}. Éligible : {enveloppes_str}."
    )

    texte_long = (
        f"L'ETF {ticker} est sélectionné sur la base de quatre critères objectifs. "
        f"(1) Coût total (TER) : {ter:.2%}{aum_str}{td_str}. "
        f"(2) Domicile fiscal {domicile} : convention de retenue à la source optimisée "
        f"(traité fiscal France / pays d'émission). "
        f"(3) Méthode de réplication {replication} : traçabilité du panier, "
        f"risque de contrepartie minimal. "
        f"(4) Éligibilité enveloppes fiscales : {enveloppes_str} — "
        f"permet l'optimisation de l'asset location (PEA, AV, PER)."
    )

    # Alternatives écartées
    if alternatives_ecartees:
        raisons = "; ".join(
            f"{a.get('ticker', '—')} ({a.get('raison', 'non précisé')})"
            for a in alternatives_ecartees
        )
        alt_str: str | None = f"Alternatives analysées et écartées : {raisons}."
    else:
        alt_str = None

    return Explication(
        section="etf.choix",
        titre=f"Pourquoi {ticker} ?",
        texte_court=texte_court,
        texte_long=texte_long,
        source=(
            "AMF — Comprendre les ETF (2023). "
            "ESMA — Guidelines on ETFs and other UCITS issues (2014/937). "
            "Sharpe, W. (1991). The Arithmetic of Active Management. "
            "Financial Analysts Journal, 47(1), 7-9."
        ),
        alternative_ecartee=alt_str,
    )


def expliquer_ter(etf: dict) -> Explication:
    """Explication pédagogique du TER et de son impact sur le capital long terme."""
    ticker = etf.get("ticker", "—")
    ter = etf.get("ter", 0.0)
    ter_moyen_actif = 0.0165  # ~1,65 % pour une gestion active type OPCVM France

    gain_10_ans = (1 + ter_moyen_actif - ter) ** 10 - 1  # différentiel sur 100k€ base
    gain_eur_indicatif = 100_000 * gain_10_ans

    return Explication(
        section="etf.ter",
        titre=f"Impact du TER {ter:.2%} sur 10 ans",
        texte_court=(
            f"Le TER de {ter:.2%} est {ter_moyen_actif - ter:.2%} moins cher "
            f"qu'un OPCVM actif moyen ({ter_moyen_actif:.2%})."
        ),
        texte_long=(
            f"Le Total Expense Ratio (TER) de {ticker} s'élève à {ter:.2%} par an. "
            f"Un OPCVM à gestion active facture en moyenne {ter_moyen_actif:.2%} "
            f"(source : AMF rapport 2023 sur les frais des OPC). "
            f"Sur 100 000 € investis et 10 ans, l'écart de frais représente "
            f"≈ {gain_eur_indicatif:,.0f} € de capital supplémentaire. "
            f"Sharpe (1991) démontre que, avant frais, la gestion active est un jeu à somme "
            f"nulle ; après frais, la gestion passive surperforme mécaniquement en moyenne."
        ),
        formule=f"Gain frais = 100 000 × [(1 + {ter_moyen_actif:.4f} − {ter:.4f})^10 − 1]",
        source=(
            "Sharpe, W. (1991). The Arithmetic of Active Management. "
            "Financial Analysts Journal, 47(1), 7-9. "
            "AMF (2023). Rapport annuel sur les frais des OPC en France."
        ),
        gain_eur=round(gain_eur_indicatif, 2),
        alternative_ecartee=(
            f"OPCVM actif à {ter_moyen_actif:.2%} de frais écarté : "
            f"aucune preuve empirique robuste de surperformance nette de frais à long terme."
        ),
    )
