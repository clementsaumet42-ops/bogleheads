"""Moteur de backtest mensuel pour portefeuilles Bogle."""

from __future__ import annotations

import logging
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel

from .donnees_historiques import aligner_series, charger_serie
from .fiscalite_backtest import (
    ConfigFiscalite,
    calculer_fiscalite_optimisee,
    calculer_impot_dividendes_cto,
    calculer_impot_rebalancement_cto,
)
from .frais import ConfigFrais
from .metriques import (
    calculer_cagr,
    calculer_calmar,
    calculer_max_drawdown,
    calculer_sharpe,
    calculer_sortino,
    calculer_volatilite_annuelle,
)
from .portefeuilles_bogle import PortefeuilleBogle

logger = logging.getLogger(__name__)


class ResultatBacktest(BaseModel):
    portefeuille_nom: str
    mode: str
    capital_initial: float
    capital_final: float
    cagr: float
    volatilite_annuelle: float
    sharpe: float
    max_drawdown: float
    sortino: float
    calmar: float
    serie_valeur_mensuelle: list[tuple[str, float]]
    frais_totaux_eur: float
    fiscalite_totale_eur: float
    nb_rebalancements: int
    detail_annuel: list[dict]


def _charger_series_portefeuille(
    portefeuille: PortefeuilleBogle,
) -> dict[str, pd.Series | None]:
    """Charge les séries pour chaque classe du portefeuille. Fallback None si absente."""
    series: dict[str, pd.Series | None] = {}
    for classe in portefeuille.allocations:
        try:
            series[classe] = charger_serie(classe)
        except (FileNotFoundError, Exception) as exc:
            logger.warning("Série absente pour '%s': %s — utilisation de zéro.", classe, exc)
            series[classe] = None
    return series


def backtester(
    portefeuille: PortefeuilleBogle,
    capital_initial_eur: float,
    date_debut: str,
    date_fin: str,
    config_frais: ConfigFrais,
    config_fiscalite: ConfigFiscalite,
    mode: Literal["brut", "net_frais", "net_fiscal_cto", "net_optimise"],
    profil_pour_optim: Any | None = None,
) -> ResultatBacktest:
    """Simule un backtest mensuel du portefeuille sur la période donnée."""
    # 1. Charger les séries
    series_brutes = _charger_series_portefeuille(portefeuille)
    classes = list(portefeuille.allocations.keys())

    # 2. Aligner les séries disponibles — créer une série zéro pour les absentes
    series_valides = {k: v for k, v in series_brutes.items() if v is not None}
    if series_valides:
        try:
            df_aligne = aligner_series(*series_valides.values())
        except ValueError:
            idx = pd.date_range(date_debut, date_fin, freq="ME")
            df_aligne = pd.DataFrame(0.0, index=idx, columns=list(series_valides.keys()))
    else:
        idx = pd.date_range(date_debut, date_fin, freq="ME")
        df_aligne = pd.DataFrame(0.0, index=idx, columns=classes)

    # Ajouter les colonnes manquantes (séries absentes) avec zéro
    for classe in classes:
        if classe not in df_aligne.columns:
            df_aligne[classe] = 0.0

    # 3. Filtrer par date_debut / date_fin
    df_aligne = df_aligne.loc[date_debut:date_fin, classes]
    if df_aligne.empty:
        return ResultatBacktest(
            portefeuille_nom=portefeuille.nom,
            mode=mode,
            capital_initial=capital_initial_eur,
            capital_final=capital_initial_eur,
            cagr=0.0,
            volatilite_annuelle=0.0,
            sharpe=0.0,
            max_drawdown=0.0,
            sortino=0.0,
            calmar=0.0,
            serie_valeur_mensuelle=[],
            frais_totaux_eur=0.0,
            fiscalite_totale_eur=0.0,
            nb_rebalancements=0,
            detail_annuel=[],
        )

    # 4. Simulation mensuelle
    allocations = portefeuille.allocations
    poids = {k: allocations[k] for k in classes}

    valeurs: dict[str, float] = {k: capital_initial_eur * poids[k] for k in classes}
    prix_revient: dict[str, float] = dict(valeurs)

    serie_valeur: list[tuple[str, float]] = []
    rendements_portefeuille: list[float] = []
    frais_totaux = 0.0
    fiscalite_totale = 0.0
    nb_rebalancements = 0
    detail_annuel: list[dict] = []

    annee_courante = df_aligne.index[0].year
    capital_debut_annee = capital_initial_eur

    # Ventilation enveloppes pour optimisé (simplifiée : PEA pour actions, AV sinon)
    ventilation_enveloppes: dict[str, str] = {}
    for classe in classes:
        if "actions" in classe:
            ventilation_enveloppes[classe] = "PEA"
        elif "obligations" in classe or "cash" in classe:
            ventilation_enveloppes[classe] = "AV"
        else:
            ventilation_enveloppes[classe] = "CTO"

    for date_idx, row in df_aligne.iterrows():
        annee = date_idx.year

        # Fin d'année : rebalancement + fiscalité
        if annee != annee_courante:
            # Frais enveloppe annuels
            if mode in ("net_frais", "net_fiscal_cto", "net_optimise"):
                for classe in classes:
                    enveloppe = ventilation_enveloppes.get(classe, "CTO")
                    taux_env = config_frais.frais_enveloppe_annuel_pct.get(enveloppe, 0.0)
                    frais_env = valeurs[classe] * taux_env
                    valeurs[classe] -= frais_env
                    frais_totaux += frais_env

            # Fiscalité dividendes
            if mode == "net_fiscal_cto":
                impot_div = calculer_impot_dividendes_cto(valeurs, config_fiscalite)
                total_val = sum(valeurs.values())
                if total_val > 0:
                    for classe in classes:
                        valeurs[classe] -= impot_div * (valeurs[classe] / total_val)
                fiscalite_totale += impot_div

            elif mode == "net_optimise":
                impot_opt = calculer_fiscalite_optimisee(
                    valeurs, ventilation_enveloppes, config_fiscalite
                )
                total_val = sum(valeurs.values())
                if total_val > 0:
                    for classe in classes:
                        valeurs[classe] -= impot_opt * (valeurs[classe] / total_val)
                fiscalite_totale += impot_opt

            # Rebalancement annuel
            capital_total = sum(valeurs.values())
            poids_actuels = {
                k: valeurs[k] / capital_total if capital_total > 0 else poids[k] for k in classes
            }
            need_rebalance = any(
                abs(poids_actuels[k] - poids[k]) > portefeuille.seuil_rebalancement_pct
                for k in classes
            )
            if need_rebalance and capital_total > 0:
                ventes: dict[str, float] = {}
                for k in classes:
                    cible = capital_total * poids[k]
                    if valeurs[k] > cible:
                        ventes[k] = valeurs[k] - cible

                # Impôt sur plus-values de rebalancement CTO
                if mode == "net_fiscal_cto" and ventes:
                    impot_reb = calculer_impot_rebalancement_cto(
                        ventes, config_fiscalite, prix_revient
                    )
                    fiscalite_totale += impot_reb
                    capital_total -= impot_reb

                # Frais de transaction
                if mode in ("net_frais", "net_fiscal_cto", "net_optimise"):
                    nb_ordres = sum(1 for v in ventes.values() if v > 0)
                    frais_reb = nb_ordres * config_frais.courtage_par_ordre_eur
                    for _k, v in ventes.items():
                        frais_reb += v * config_frais.spread_bps / 10_000
                    capital_total -= frais_reb
                    frais_totaux += frais_reb

                for k in classes:
                    valeurs[k] = capital_total * poids[k]
                    prix_revient[k] = valeurs[k]

                nb_rebalancements += 1

            # Détail annuel
            detail_annuel.append(
                {
                    "annee": annee_courante,
                    "capital_debut": capital_debut_annee,
                    "capital_fin": sum(valeurs.values()),
                    "rendement": (
                        (sum(valeurs.values()) / capital_debut_annee - 1)
                        if capital_debut_annee > 0
                        else 0.0
                    ),
                }
            )

            annee_courante = annee
            capital_debut_annee = sum(valeurs.values())

        # Rendements mensuels
        rendement_pf = 0.0
        for classe in classes:
            r = float(row[classe])
            valeurs[classe] *= 1 + r

            # TER mensuel
            if mode in ("net_frais", "net_fiscal_cto", "net_optimise"):
                ter = config_frais.ter_par_classe.get(classe, 0.0)
                if ter > 0:
                    frais_ter = valeurs[classe] * (1 - (1 - ter) ** (1 / 12))
                    valeurs[classe] -= frais_ter
                    frais_totaux += frais_ter

            rendement_pf += poids[classe] * r

        capital_actuel = sum(valeurs.values())
        serie_valeur.append((str(date_idx.date()), capital_actuel))
        rendements_portefeuille.append(rendement_pf)

    # Ajouter dernier détail annuel
    detail_annuel.append(
        {
            "annee": annee_courante,
            "capital_debut": capital_debut_annee,
            "capital_fin": sum(valeurs.values()),
            "rendement": (
                (sum(valeurs.values()) / capital_debut_annee - 1)
                if capital_debut_annee > 0
                else 0.0
            ),
        }
    )

    # 5. Calculer les métriques
    capital_final = sum(valeurs.values())
    n_mois = len(df_aligne)
    n_annees = n_mois / 12.0

    serie_val_pd = pd.Series(
        [v for _, v in serie_valeur],
        index=pd.to_datetime([d for d, _ in serie_valeur]),
    )
    rend_pd = pd.Series(rendements_portefeuille)

    cagr = calculer_cagr(capital_initial_eur, capital_final, n_annees)
    vol = calculer_volatilite_annuelle(rend_pd)
    sharpe = calculer_sharpe(rend_pd)
    mdd = calculer_max_drawdown(serie_val_pd)
    sortino = calculer_sortino(rend_pd)
    calmar = calculer_calmar(cagr, mdd)

    return ResultatBacktest(
        portefeuille_nom=portefeuille.nom,
        mode=mode,
        capital_initial=capital_initial_eur,
        capital_final=capital_final,
        cagr=cagr,
        volatilite_annuelle=vol,
        sharpe=sharpe,
        max_drawdown=mdd,
        sortino=sortino,
        calmar=calmar,
        serie_valeur_mensuelle=serie_valeur,
        frais_totaux_eur=frais_totaux,
        fiscalite_totale_eur=fiscalite_totale,
        nb_rebalancements=nb_rebalancements,
        detail_annuel=detail_annuel,
    )
