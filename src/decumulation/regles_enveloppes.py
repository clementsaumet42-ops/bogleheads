"""Regles fiscales de retrait par enveloppe — usage en phase de decumulation.

Toutes les fonctions retournent un dict avec :
    {
        "ir": float,
        "ps": float,
        "total": float,
        "net": float,
        "abattement_utilise": float,  # 0 si non applicable
        "taux_effectif": float,
        "details": str,
        "source_legale": str,
    }

References :
    - PEA : Art. 150-0 A CGI
    - AV : Art. 125-0 A CGI
    - CTO : Art. 200 A CGI (PFU)
    - PER : Art. 163 quatervicies CGI
    - PEE : Art. 163 bis B CGI
"""

from __future__ import annotations

from dataclasses import dataclass

from src.fiscalite.constantes import (
    AV_ABATTEMENT_CELIBATAIRE,
    AV_ABATTEMENT_COUPLE,
    AV_DUREE_4_ANS,
    AV_DUREE_8_ANS,
    AV_SEUIL_150K,
    AV_SEUIL_300K,
    AV_TAUX_PFL_7_5,
    PEA_DUREE_2_ANS,
    PEA_DUREE_5_ANS,
    TAUX_PFU_IR,
    TAUX_PS,
)


@dataclass
class ContexteFiscal:
    """Contexte du foyer pour le calcul fiscal d'un retrait."""

    situation: str = "celibataire"  # "celibataire" ou "couple"
    tmi: float = 0.30  # taux marginal d'imposition IR
    abattement_av_deja_utilise_annee: float = 0.0
    encours_av_total_foyer: float = 0.0  # somme valeur tous contrats AV du foyer

    @property
    def abattement_av_annuel(self) -> float:
        return AV_ABATTEMENT_COUPLE if self.situation == "couple" else AV_ABATTEMENT_CELIBATAIRE

    @property
    def seuil_av_encours(self) -> float:
        return AV_SEUIL_300K if self.situation == "couple" else AV_SEUIL_150K


def _resultat_zero(montant_brut: float, source: str, details: str = "") -> dict:
    return {
        "ir": 0.0,
        "ps": 0.0,
        "total": 0.0,
        "net": montant_brut,
        "abattement_utilise": 0.0,
        "taux_effectif": 0.0,
        "details": details,
        "source_legale": source,
    }


def fiscalite_retrait_pea(
    montant_brut: float,
    ratio_pv: float,
    duree_detention_ans: float,
    tmi: float = 0.30,
) -> dict:
    """Fiscalite d'un retrait PEA.

    > 5 ans : 0% IR, PS sur PV (taux effectif typique : 4-5% du brut)
    2-5 ans : 12.8% IR + PS sur PV
    < 2 ans : TMI + PS sur PV
    """
    pv = max(0.0, montant_brut * ratio_pv)
    if duree_detention_ans >= PEA_DUREE_5_ANS:
        ir = 0.0
        details = f"PEA > 5 ans : 0% IR, PS {TAUX_PS:.1%} sur PV ({pv:,.0f} €)"
    elif duree_detention_ans >= PEA_DUREE_2_ANS:
        ir = pv * TAUX_PFU_IR
        details = f"PEA 2-5 ans : 12.8% IR sur PV ({pv:,.0f} €)"
    else:
        ir = pv * tmi
        details = f"PEA < 2 ans : TMI {tmi:.1%} sur PV ({pv:,.0f} €)"

    ps = pv * TAUX_PS
    total = ir + ps
    net = montant_brut - total
    return {
        "ir": ir,
        "ps": ps,
        "total": total,
        "net": net,
        "abattement_utilise": 0.0,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0.0,
        "details": details,
        "source_legale": "Art. 150-0 A CGI",
    }


def fiscalite_retrait_av(
    montant_brut: float,
    ratio_pv: float,
    duree_detention_ans: float,
    contexte: ContexteFiscal,
    versements_avant_2017_ratio: float = 0.0,
) -> dict:
    """Fiscalite d'un rachat partiel d'assurance-vie.

    Repose sur Art. 125-0 A CGI : duree, abattement 4600/9200, seuil 150/300k.
    """
    pv = max(0.0, montant_brut * ratio_pv)

    if pv == 0.0:
        return _resultat_zero(montant_brut, "Art. 125-0 A CGI", "AV : pas de PV")

    # < 4 ans : pas d'abattement, PFU 12.8%
    if duree_detention_ans < AV_DUREE_4_ANS:
        ir = pv * TAUX_PFU_IR
        ps = pv * TAUX_PS
        return {
            "ir": ir,
            "ps": ps,
            "total": ir + ps,
            "net": montant_brut - ir - ps,
            "abattement_utilise": 0.0,
            "taux_effectif": (ir + ps) / montant_brut,
            "details": f"AV < 4 ans : PFU 12.8% sur PV ({pv:,.0f} €)",
            "source_legale": "Art. 125-0 A-I-1 CGI",
        }

    # >= 4 ans : abattement utilisable
    abattement_dispo = max(
        0.0,
        contexte.abattement_av_annuel - contexte.abattement_av_deja_utilise_annee,
    )
    abattement_utilise = min(pv, abattement_dispo)
    pv_imposable = pv - abattement_utilise

    # 4 - 8 ans : PFU 12.8% sur le reste
    if duree_detention_ans < AV_DUREE_8_ANS:
        ir = pv_imposable * TAUX_PFU_IR
        details = (
            f"AV 4-8 ans : abattement {abattement_utilise:,.0f} € "
            f"+ PFU 12.8% sur {pv_imposable:,.0f} €"
        )
    else:
        # > 8 ans : PFL 7.5% sous seuil encours, PFU 12.8% au-dela
        # Prorata versements avant/apres 27/09/2017
        pv_avant = pv_imposable * versements_avant_2017_ratio
        pv_apres = pv_imposable - pv_avant
        ir_avant = pv_avant * AV_TAUX_PFL_7_5
        if contexte.encours_av_total_foyer <= contexte.seuil_av_encours:
            ir_apres = pv_apres * AV_TAUX_PFL_7_5
            taux_apres = "7.5%"
        else:
            ir_apres = pv_apres * TAUX_PFU_IR
            taux_apres = "12.8% (encours > seuil)"
        ir = ir_avant + ir_apres
        details = (
            f"AV > 8 ans : abattement {abattement_utilise:,.0f} €. "
            f"Avant 2017 : {pv_avant:,.0f} € @ 7.5%. "
            f"Apres 2017 : {pv_apres:,.0f} € @ {taux_apres}."
        )

    ps = pv * TAUX_PS  # PS sur PV totale, pas seulement imposable
    total = ir + ps
    return {
        "ir": ir,
        "ps": ps,
        "total": total,
        "net": montant_brut - total,
        "abattement_utilise": abattement_utilise,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0.0,
        "details": details,
        "source_legale": "Art. 125-0 A CGI",
    }


def fiscalite_retrait_cto(
    montant_brut: float,
    ratio_pv: float,
) -> dict:
    """Fiscalite d'une cession sur CTO (compte-titres ordinaire).

    Hypothese : option PFU (regime par defaut), pas de calcul TMI/abattement
    duree de detention car ils sont rarement avantageux pour ETF.
    """
    pv = max(0.0, montant_brut * ratio_pv)
    ir = pv * TAUX_PFU_IR
    ps = pv * TAUX_PS
    total = ir + ps
    return {
        "ir": ir,
        "ps": ps,
        "total": total,
        "net": montant_brut - total,
        "abattement_utilise": 0.0,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0.0,
        "details": f"CTO : PFU 30% sur PV ({pv:,.0f} €)",
        "source_legale": "Art. 200 A CGI",
    }


def fiscalite_retrait_per_capital(
    montant_brut: float,
    ratio_pv: float,
    versements_deduits_ratio: float,
    tmi: float = 0.30,
) -> dict:
    """Fiscalite d'une sortie en capital sur PER.

    Versements deduits :
        - capital : IR au TMI (sur la part capital)
        - gains : PFU 12.8% + PS
    Versements non deduits :
        - capital : exonere
        - gains : PFU 12.8% + PS
    """
    pv = max(0.0, montant_brut * ratio_pv)
    capital = montant_brut - pv

    # Prorata capital deduit / non deduit
    capital_deduit = capital * versements_deduits_ratio
    # capital_non_deduit = capital - capital_deduit  # exonere

    ir_capital = capital_deduit * tmi
    ir_pv = pv * TAUX_PFU_IR
    ir = ir_capital + ir_pv
    ps = pv * TAUX_PS
    total = ir + ps
    return {
        "ir": ir,
        "ps": ps,
        "total": total,
        "net": montant_brut - total,
        "abattement_utilise": 0.0,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0.0,
        "details": (
            f"PER capital : capital deduit {capital_deduit:,.0f} € @ TMI {tmi:.1%}, "
            f"PV {pv:,.0f} € @ PFU 12.8%"
        ),
        "source_legale": "Art. 163 quatervicies CGI",
    }


def fiscalite_retrait_pee(
    montant_brut: float,
    ratio_pv: float,
    debloque: bool = True,
) -> dict:
    """Fiscalite d'un retrait PEE / PERCO debloque (5 ans atteints).

    Si debloque : 0% IR, PS sur gains. Sinon : pas de retrait possible
    sauf cas legaux.
    """
    if not debloque:
        return _resultat_zero(0.0, "Art. 163 bis B CGI", "PEE non debloque : retrait impossible")
    pv = max(0.0, montant_brut * ratio_pv)
    ir = 0.0
    ps = pv * TAUX_PS
    total = ir + ps
    return {
        "ir": ir,
        "ps": ps,
        "total": total,
        "net": montant_brut - total,
        "abattement_utilise": 0.0,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0.0,
        "details": f"PEE debloque : 0% IR, PS {TAUX_PS:.1%} sur PV ({pv:,.0f} €)",
        "source_legale": "Art. 163 bis B CGI",
    }


def fiscalite_retrait(
    type_enveloppe: str,
    montant_brut: float,
    ratio_pv: float,
    contexte: ContexteFiscal,
    duree_detention_ans: float = 0.0,
    versements_deduits_ratio: float = 1.0,
    versements_avant_2017_ratio: float = 0.0,
    pee_debloque: bool = True,
) -> dict:
    """Dispatch le calcul fiscal selon le type d'enveloppe."""
    type_norm = type_enveloppe.upper()
    if type_norm == "PEA":
        return fiscalite_retrait_pea(montant_brut, ratio_pv, duree_detention_ans, contexte.tmi)
    if type_norm == "AV":
        return fiscalite_retrait_av(
            montant_brut,
            ratio_pv,
            duree_detention_ans,
            contexte,
            versements_avant_2017_ratio,
        )
    if type_norm == "CTO":
        return fiscalite_retrait_cto(montant_brut, ratio_pv)
    if type_norm == "PER":
        return fiscalite_retrait_per_capital(
            montant_brut, ratio_pv, versements_deduits_ratio, contexte.tmi
        )
    if type_norm in ("PEE", "PERCOL"):
        return fiscalite_retrait_pee(montant_brut, ratio_pv, pee_debloque)
    raise ValueError(f"Type d'enveloppe inconnu : {type_enveloppe}")


def cout_marginal_retrait(
    type_enveloppe: str,
    pas_test: float,
    ratio_pv: float,
    contexte: ContexteFiscal,
    duree_detention_ans: float = 0.0,
    versements_deduits_ratio: float = 1.0,
    versements_avant_2017_ratio: float = 0.0,
    pee_debloque: bool = True,
) -> float:
    """Estime le taux marginal effectif d'un retrait incremental.

    Sert a trier les enveloppes par cout fiscal croissant.
    Renvoie le taux d'imposition effectif (impots / brut) sur le pas_test.
    """
    res = fiscalite_retrait(
        type_enveloppe,
        pas_test,
        ratio_pv,
        contexte,
        duree_detention_ans,
        versements_deduits_ratio,
        versements_avant_2017_ratio,
        pee_debloque,
    )
    return res["taux_effectif"]
