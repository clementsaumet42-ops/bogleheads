"""Moteur 3 — Distribution vs Capitalisation en CTO (S8.2b).

Pour les ETF détenus en CTO uniquement (pas en AV/PEA où le report est natif),
identifie si une variante capitalisante existe et chiffre le gain de report
d'imposition.

Hypothèse mathématique (documentée) :
    Sur un horizon de N ans avec :
    - Rendement total r = 7%/an (dont d = 1.8% en dividende)
    - Taux d'imposition τ sur les dividendes (PFU 30% ou TMI+PS)
    - Montant investi : M

    Approche simplifiée :
    - Scénario DIST : chaque année, les dividendes M×d sont taxés à τ,
      soit un drag fiscal annuel de M×d×τ.
      Le capital net après N ans = M×(1+r-d×τ)^N

    - Scénario ACC : les dividendes se réinvestissent sans taxation,
      capital brut = M×(1+r)^N ; seule la plus-value finale est taxée.
      Capital net après N ans ≈ M×(1+r)^N - (M×(1+r)^N - M)×τ_pv

    Gain de report = Capital_ACC_net - Capital_DIST_net

    Note : τ_pv (taux imposition plus-value à terme) = PFU 30%.
    Confiance = moyenne par défaut (hypothèses de rendement fortes).
"""

from __future__ import annotations

import logging
import warnings

from src.audit.moteurs._constantes import (
    PFU_TAUX,
    PS_TAUX,
    RENDEMENT_DIVIDENDE_PAR_CATEGORIE,
    RENDEMENT_TOTAL_ACTIONS,
    SOUS_CLASSE_VERS_INDICE,
    TAUX_ACTUALISATION_DEFAUT,
)
from src.audit.opportunite import LigneEtf, Opportunite
from src.schemas import ETFEnrichi

logger = logging.getLogger(__name__)

_SOURCES = [
    "config/univers_etf.yaml — données S8.2a",
    "art. 200 A CGI — Prélèvement Forfaitaire Unique 30%",
    "Dimson-Marsh-Staunton 2024 — rendements actions historiques (hypothèse 7%/an)",
]

# Enveloppes où le report d'imposition est déjà natif — ne pas proposer de switch
# Note : CTO_IS (CTO d'une société soumise à l'IS) n'est PAS dans cette liste car
# le report d'imposition n'est pas natif — l'IS est dû annuellement sur les revenus
# et les plus-values réalisées (pas de report jusqu'à cession comme en AV/PEA).
ENVELOPPES_REPORT_NATIF = frozenset({"PEA", "AV", "PER", "PEE", "Contrat_Cap_IS"})

# Seuil minimum de gain pour créer une opportunité
SEUIL_GAIN_ANNUEL_EUR = 100.0

# Horizon de capitalisation pour comparaison interne (distinct de l'horizon 30 ans de capitaliser_30_ans)
HORIZON_ANS = 30


def _gain_report_imposition(
    montant_eur: float,
    rendement_dividende: float,
    rendement_total: float,
    taux_imposition_div: float,
    horizon_ans: int = HORIZON_ANS,
) -> float:
    """Calcule le gain de report d'imposition (ACC vs DIST en CTO).

    Modèle mathématique :
        Scénario DIST :
            Chaque année, les dividendes = M × d sont taxés à τ_div.
            On modélise par un rendement net effectif : r_net = r_total - d × τ_div
            Capital_DIST = M × (1 + r_net)^N
            Taxation PV finale : (Capital_DIST - M) × τ_pv
            Capital_DIST_net = Capital_DIST - (Capital_DIST - M) × τ_pv

        Scénario ACC :
            Aucune taxation intermédiaire.
            Capital_ACC = M × (1 + r_total)^N
            Taxation PV finale : (Capital_ACC - M) × τ_pv
            Capital_ACC_net = Capital_ACC - (Capital_ACC - M) × τ_pv

        Gain = Capital_ACC_net - Capital_DIST_net

    Args:
        montant_eur: montant investi en CTO
        rendement_dividende: rendement en dividendes annuel (ex: 0.018)
        rendement_total: rendement total hypothétique (ex: 0.07)
        taux_imposition_div: PFU ou TMI+PS appliqué aux dividendes
        horizon_ans: horizon en années

    Returns:
        Gain total en € sur l'horizon (positif = ACC meilleur que DIST).
    """
    taux_pv = PFU_TAUX  # imposition PV finale identique dans les deux cas

    # Scénario DIST : drag annuel sur dividendes
    r_net = rendement_total - rendement_dividende * taux_imposition_div
    capital_dist = montant_eur * (1 + r_net) ** horizon_ans
    capital_dist_net = capital_dist - (capital_dist - montant_eur) * taux_pv

    # Scénario ACC : report complet
    capital_acc = montant_eur * (1 + rendement_total) ** horizon_ans
    capital_acc_net = capital_acc - (capital_acc - montant_eur) * taux_pv

    return capital_acc_net - capital_dist_net


def _rendement_dividende_pour(sous_classe: str | None) -> float:
    indice = SOUS_CLASSE_VERS_INDICE.get(sous_classe or "", "_DEFAUT")
    return RENDEMENT_DIVIDENDE_PAR_CATEGORIE.get(
        indice, RENDEMENT_DIVIDENDE_PAR_CATEGORIE["_DEFAUT"]
    )


def detecter_opportunites_dist_vs_cap(
    portefeuille_actuel: list[LigneEtf],
    univers: list[ETFEnrichi],
    tmi_client: float = 0.30,
) -> list[Opportunite]:
    """Détecte les gains de report d'imposition en passant DIST → ACC en CTO.

    Pour chaque ETF distribuant détenu en CTO :
    1. Identifie la variante ACC du même indice/émetteur.
    2. Calcule le gain de report fiscal sur 30 ans.
    3. Crée Opportunite si gain > 100 €/an équivalent.

    Note : skip automatique si l'enveloppe n'est pas CTO (PEA/AV/PER ont report natif).

    Args:
        portefeuille_actuel: lignes ETF du client.
        univers: liste des ETFEnrichi depuis univers_etf.yaml.
        tmi_client: TMI du client (0.30 par défaut = PFU).

    Returns:
        Liste d'Opportunite triée par gain décroissant.
    """
    index_isin: dict[str, ETFEnrichi] = {etf.isin: etf for etf in univers}
    opportunites: list[Opportunite] = []

    for ligne in portefeuille_actuel:
        # Skip si enveloppe avec report natif
        if ligne.enveloppe in ENVELOPPES_REPORT_NATIF:
            logger.debug(
                "Ligne %s en enveloppe %s — report natif, skip dist_vs_cap",
                ligne.isin,
                ligne.enveloppe,
            )
            continue

        etf_actuel = index_isin.get(ligne.isin)
        if etf_actuel is None:
            warnings.warn(
                f"ISIN {ligne.isin} absent de l'univers ETF — ligne ignorée",
                stacklevel=2,
            )
            continue

        # Vérifier que c'est un ETF distribuant
        dist_cap = etf_actuel.distribuant_capitalisant
        if dist_cap == "ACC":
            logger.debug("ETF %s est déjà capitalisant — skip", etf_actuel.ticker)
            continue
        if dist_cap is None and etf_actuel.capitalisant:
            logger.debug("ETF %s capitalisant (champ capitalisant=True) — skip", etf_actuel.ticker)
            continue

        # Chercher variante ACC du même indice/émetteur
        indice_actuel = SOUS_CLASSE_VERS_INDICE.get(etf_actuel.sous_classe or "")
        meilleure_alt: ETFEnrichi | None = None

        for alt in univers:
            if alt.isin == etf_actuel.isin:
                continue
            # Même indice
            indice_alt = SOUS_CLASSE_VERS_INDICE.get(alt.sous_classe or "")
            if indice_alt != indice_actuel or indice_actuel is None:
                continue
            # Doit être capitalisant
            alt_is_acc = alt.distribuant_capitalisant == "ACC" or (
                alt.distribuant_capitalisant is None and alt.capitalisant
            )
            if not alt_is_acc:
                continue
            # Préférer même émetteur
            if (
                meilleure_alt is None
                or alt.emetteur == etf_actuel.emetteur
                and meilleure_alt.emetteur != etf_actuel.emetteur
            ):
                meilleure_alt = alt

        if meilleure_alt is None:
            logger.debug("ETF %s : aucune variante ACC trouvée dans l'univers", etf_actuel.ticker)
            continue

        rendement_div = _rendement_dividende_pour(etf_actuel.sous_classe)
        # Taux d'imposition effectif sur dividendes en CTO
        # Utiliser TMI si > PFU (option barème), sinon PFU
        taux_div = max(tmi_client + PS_TAUX, PFU_TAUX)

        gain_total_30ans = _gain_report_imposition(
            ligne.montant_eur,
            rendement_div,
            RENDEMENT_TOTAL_ACTIONS,
            taux_div,
            HORIZON_ANS,
        )

        # Convertir en gain annuel équivalent pour la comparaison seuil
        # gain_annuel_equiv = gain_total_30ans / annuity_factor
        if TAUX_ACTUALISATION_DEFAUT > 0:
            annuity_factor = (
                (1 + TAUX_ACTUALISATION_DEFAUT) ** HORIZON_ANS - 1
            ) / TAUX_ACTUALISATION_DEFAUT
        else:
            annuity_factor = HORIZON_ANS
        gain_annuel_equiv = gain_total_30ans / annuity_factor if annuity_factor > 0 else 0

        if gain_annuel_equiv < SEUIL_GAIN_ANNUEL_EUR:
            continue

        gain_bps = rendement_div * taux_div * 10_000

        note_ec = (
            f"Hypothèses : rendement total {RENDEMENT_TOTAL_ACTIONS * 100:.0f}%/an, "
            f"dont {rendement_div * 100:.1f}% en dividende, "
            f"taux imposition dividende {taux_div * 100:.1f}%, "
            f"horizon {HORIZON_ANS} ans. "
            f"Confiance = moyenne (hypothèses de rendement fortes)."
        )

        contraintes = [
            "ETF distribuant en CTO uniquement — ne pas appliquer en AV/PEA/PER",
            "Vérifier l'option barème vs PFU pour le client",
            "Le switch implique la vente du DIST → friction fiscale immédiate si plus-value latente",
        ]

        opp = Opportunite(
            id=f"etf.dist_vs_cap.{etf_actuel.ticker}_vers_{meilleure_alt.ticker}",
            levier="dist_vs_cap",
            titre=f"Passer {etf_actuel.ticker} (DIST) → {meilleure_alt.ticker} (ACC) en CTO pour gain report fiscal",
            gain_annuel_bps=round(gain_bps, 2),
            gain_annuel_eur=round(gain_annuel_equiv, 2),
            gain_30ans_eur=round(gain_total_30ans, 0),
            montant_concerne_eur=ligne.montant_eur,
            avant={
                "ticker": etf_actuel.ticker,
                "isin": etf_actuel.isin,
                "type": "DIST",
                "rendement_dividende_estime": rendement_div,
                "taux_imposition_div": taux_div,
                "drag_fiscal_annuel_eur": round(ligne.montant_eur * rendement_div * taux_div, 2),
            },
            apres={
                "ticker": meilleure_alt.ticker,
                "isin": meilleure_alt.isin,
                "type": "ACC",
                "drag_fiscal_annuel_eur": 0.0,
                "note": "Report total — taxation uniquement à la cession",
            },
            formule=(
                f"Gain_report = Capital_ACC_net - Capital_DIST_net sur {HORIZON_ANS} ans ; "
                f"r_total={RENDEMENT_TOTAL_ACTIONS * 100:.0f}%, d={rendement_div * 100:.1f}%, "
                f"τ_div={taux_div * 100:.0f}%, τ_pv={PFU_TAUX * 100:.0f}% ; "
                f"Capital_DIST : M×(1+r-d×τ_div)^N après PV finale ; "
                f"Capital_ACC : M×(1+r)^N après PV finale ; "
                f"économie modélisée à hypothèses constantes"
            ),
            sources=_SOURCES,
            complexite="moyenne",
            delai_mise_en_oeuvre_jours=14,
            contraintes=contraintes,
            confiance="moyenne",
            note_ec=note_ec,
        )
        opportunites.append(opp)

    opportunites.sort(key=lambda o: o.gain_30ans_eur, reverse=True)
    return opportunites
