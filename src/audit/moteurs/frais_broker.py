"""Moteur 5 — Frais broker (S8.2b).

Audit du broker actuel vs alternatives moins chères pour le profil client
(volume d'ordres, marchés US/EU, frais de change).

Coût annuel = nb_ordres × frais_moyen_par_ordre + frais_garde + frais_change × montant_ordres_us

Règles :
- Seuil de recommandation : delta > 50 €/an
- Top-3 alternatives retournées
- Frais de change comptés uniquement pour la part ordres US (parts_ordres_us_pct)
"""

from __future__ import annotations

import logging

from src.audit.moteurs._constantes import (
    SEUIL_GAIN_BROKER_EUR,
    TAUX_ACTUALISATION_DEFAUT,
)
from src.audit.opportunite import Opportunite, capitaliser_30_ans
from src.schemas import Broker

logger = logging.getLogger(__name__)

_SOURCES = [
    "config/brokers.yaml — données S8.2a",
    "Grilles tarifaires brokers FR 2024 (Bourse Direct, Fortuneo, DEGIRO, Trade Republic)",
]

TOP_N_BROKERS = 3


def _cout_annuel_broker(
    broker: Broker,
    nb_ordres_par_an: int,
    montant_moyen_ordre_eur: float,
    parts_ordres_us_pct: float,
) -> float:
    """Calcule le coût annuel total d'un broker pour un profil client.

    Formule :
        coût = nb_ordres × frais_moyen_par_ordre
               + frais_garde
               + frais_inactivite (si nb_ordres = 0)
               + nb_ordres × parts_us × montant_moyen × frais_change

    Pour frais_moyen_par_ordre :
        Si frais fixes + %, on prend max(frais_fixes, frais_pct × montant).
        Pour simplifier, on prend frais_eur si disponible, sinon frais_pct × montant.

    Args:
        broker: objet Broker depuis brokers.yaml
        nb_ordres_par_an: nombre d'ordres annuels estimés
        montant_moyen_ordre_eur: montant moyen par ordre en €
        parts_ordres_us_pct: fraction des ordres sur actions/ETF US (0 à 1)

    Returns:
        Coût annuel estimé en €.
    """
    # Frais par ordre
    nb_ordres_eu = nb_ordres_par_an * (1 - parts_ordres_us_pct)
    nb_ordres_us = nb_ordres_par_an * parts_ordres_us_pct

    # Frais Euronext
    frais_eu_eur = broker.frais_courtage_actions_euronext_eur or 0.0
    frais_eu_pct = broker.frais_courtage_actions_euronext_pct or 0.0
    cout_eu = max(frais_eu_eur, frais_eu_pct * montant_moyen_ordre_eur)

    # Frais US
    frais_us_eur = broker.frais_courtage_actions_us_eur or 0.0
    frais_us_pct = broker.frais_courtage_actions_us_pct or 0.0
    cout_us_courtage = max(frais_us_eur, frais_us_pct * montant_moyen_ordre_eur)

    # Frais de change sur les ordres US
    montant_total_ordres_us = nb_ordres_us * montant_moyen_ordre_eur
    cout_change = montant_total_ordres_us * broker.frais_change_devise_pct

    # Total ordres
    cout_ordres = nb_ordres_eu * cout_eu + nb_ordres_us * cout_us_courtage + cout_change

    # Frais annuels fixes
    frais_fixes = broker.frais_garde_annuel_eur
    if nb_ordres_par_an == 0:
        frais_fixes += broker.frais_inactivite_annuel_eur

    return cout_ordres + frais_fixes


def detecter_opportunites_frais_broker(
    broker_actuel: Broker,
    nb_ordres_par_an_estim: int,
    montant_moyen_ordre_eur: float,
    parts_ordres_us_pct: float,
    brokers_marche: list[Broker],
) -> list[Opportunite]:
    """Identifie les alternatives broker moins chères pour le profil client.

    1. Calcule le coût annuel actuel.
    2. Pour chaque broker alternatif : calcule coût annuel équivalent.
    3. Si delta > 50 €/an, crée une Opportunite top-3.

    Args:
        broker_actuel: broker actuel du client.
        nb_ordres_par_an_estim: nombre d'ordres annuels estimés.
        montant_moyen_ordre_eur: montant moyen par ordre en €.
        parts_ordres_us_pct: fraction des ordres US (0 à 1).
        brokers_marche: liste des brokers alternatifs.

    Returns:
        Liste d'Opportunite (max TOP_N_BROKERS) triée par gain décroissant.
    """
    cout_actuel = _cout_annuel_broker(
        broker_actuel,
        nb_ordres_par_an_estim,
        montant_moyen_ordre_eur,
        parts_ordres_us_pct,
    )

    opportunites: list[Opportunite] = []

    for candidat in brokers_marche:
        if candidat.id == broker_actuel.id:
            continue

        cout_candidat = _cout_annuel_broker(
            candidat,
            nb_ordres_par_an_estim,
            montant_moyen_ordre_eur,
            parts_ordres_us_pct,
        )

        gain_annuel = cout_actuel - cout_candidat
        if gain_annuel < SEUIL_GAIN_BROKER_EUR:
            continue

        gain_30ans = capitaliser_30_ans(gain_annuel, TAUX_ACTUALISATION_DEFAUT)
        gain_bps = (
            gain_annuel / (nb_ordres_par_an_estim * montant_moyen_ordre_eur) * 10_000
            if (nb_ordres_par_an_estim * montant_moyen_ordre_eur > 0)
            else 0.0
        )

        contraintes = ["Transfert de portefeuille : délai ~2-4 semaines, formulaire de transfert"]
        if parts_ordres_us_pct > 0:
            contraintes.append(
                f"Vérifier disponibilité des marchés US chez {candidat.nom} "
                f"({parts_ordres_us_pct * 100:.0f}% des ordres)"
            )
        if not candidat.pea_disponible and broker_actuel.pea_disponible:
            contraintes.append(
                f"{candidat.nom} ne propose pas de PEA — garder PEA chez {broker_actuel.nom}"
            )

        note_ec = (
            f"Coût annuel estimé sur {nb_ordres_par_an_estim} ordres "
            f"de {montant_moyen_ordre_eur:,.0f}€ dont {parts_ordres_us_pct * 100:.0f}% US. "
            f"Hypothèses : grille tarifaire 2024, frais de change {candidat.frais_change_devise_pct * 100:.2f}%."
        )

        opp = Opportunite(
            id=f"broker.frais.{broker_actuel.id}_vers_{candidat.id}",
            levier="frais_broker",
            titre=f"Changer broker {broker_actuel.nom} → {candidat.nom} (-{gain_annuel:,.0f}€/an)",
            gain_annuel_bps=round(gain_bps, 2),
            gain_annuel_eur=round(gain_annuel, 2),
            gain_30ans_eur=round(gain_30ans, 0),
            montant_concerne_eur=nb_ordres_par_an_estim * montant_moyen_ordre_eur,
            avant={
                "broker_id": broker_actuel.id,
                "broker_nom": broker_actuel.nom,
                "cout_annuel_eur": round(cout_actuel, 2),
                "frais_courtage_eu_eur": broker_actuel.frais_courtage_actions_euronext_eur,
                "frais_courtage_us_eur": broker_actuel.frais_courtage_actions_us_eur,
                "frais_change_pct": broker_actuel.frais_change_devise_pct,
                "frais_garde_eur": broker_actuel.frais_garde_annuel_eur,
            },
            apres={
                "broker_id": candidat.id,
                "broker_nom": candidat.nom,
                "cout_annuel_eur": round(cout_candidat, 2),
                "frais_courtage_eu_eur": candidat.frais_courtage_actions_euronext_eur,
                "frais_courtage_us_eur": candidat.frais_courtage_actions_us_eur,
                "frais_change_pct": candidat.frais_change_devise_pct,
                "frais_garde_eur": candidat.frais_garde_annuel_eur,
            },
            formule=(
                f"cout_annuel = nb_ordres_eu × cout_eu + nb_ordres_us × cout_us + frais_change + frais_garde ; "
                f"actuel={cout_actuel:,.0f}€/an → candidat={cout_candidat:,.0f}€/an ; "
                f"économie = {gain_annuel:,.0f}€/an"
            ),
            sources=_SOURCES,
            complexite="faible",
            delai_mise_en_oeuvre_jours=30,
            contraintes=contraintes,
            confiance="haute",
            note_ec=note_ec,
        )
        opportunites.append(opp)

    opportunites.sort(key=lambda o: o.gain_30ans_eur, reverse=True)
    return opportunites[:TOP_N_BROKERS]
