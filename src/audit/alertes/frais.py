from __future__ import annotations

import logging

from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R1", famille="Frais excessifs")
def detecter_R1(profil) -> Alerte | None:
    """Fondement : ACPR Recommandation 2013-R-01, frais sur UC AV."""
    try:
        contrats = getattr(profil, "assurances_vie", None) or []

        pire_frais = 0.0
        pire_contrat = None
        encours_total = 0.0

        for c in contrats:
            if isinstance(c, dict):
                frais_uc = c.get("frais_uc", 0) or 0
                encours = c.get("encours", 0) or 0
            else:
                frais_uc = getattr(c, "frais_uc", 0) or 0
                encours = getattr(c, "encours", 0) or 0
            if frais_uc > 0.01 and encours > 30000 and frais_uc > pire_frais:
                pire_frais = frais_uc
                pire_contrat = c
                encours_total = encours

        if pire_contrat is None:
            return None

        gain = encours_total * (pire_frais - 0.005)
        return Alerte(
            code="R1",
            famille="Frais excessifs",
            severite=Severite.ROUGE,
            titre="Frais UC assurance-vie excessifs (>1%)",
            description=(
                f"Vos frais UC en assurance-vie sont de {pire_frais:.1%} sur un encours de "
                f"{encours_total:,.0f} €. Des contrats en ligne proposent 0,5% de frais UC."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Comparer avec des contrats AV en ligne (Linxea, Lucya Cardif, Spirica) à 0,5% de frais UC.",
            sources=["ACPR Recommandation 2013-R-01"],
        )
    except Exception as e:
        logger.info(f"R1 skip: {e}")
        return None


@regle("R2", famille="Frais excessifs")
def detecter_R2(profil) -> Alerte | None:
    """Fondement : AMF, Directive OPCVM art. 10 — surcoût ETF en AV vs CTO."""
    try:
        positions = getattr(profil, "positions_detaillees", None) or []

        encours_av_etf = 0.0
        for pos in positions:
            if isinstance(pos, dict):
                env = pos.get("enveloppe", "")
                montant = pos.get("montant_actuel", 0)
            else:
                env = getattr(pos, "enveloppe", "")
                montant = getattr(pos, "montant_actuel", 0)
            if "AV" in str(env).upper() or "ASSURANCE" in str(env).upper():
                encours_av_etf += montant or 0

        if encours_av_etf < 10000:
            return None

        # frais AV UC typical 0.6% + TER ETF 0.2% = 0.8% vs 0.2% direct CTO
        frais_total = 0.008
        gain = encours_av_etf * (frais_total - 0.002)

        return Alerte(
            code="R2",
            famille="Frais excessifs",
            severite=Severite.JAUNE,
            titre="ETF en AV : surcoût vs CTO direct",
            description=(
                f"Détenir des ETF en assurance-vie coûte environ 0,6% de frais de gestion UC "
                f"+ TER ETF vs 0,2% en CTO direct. Sur {encours_av_etf:,.0f} € d'ETF en AV."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Arbitrer les ETF purs vers un CTO (si enveloppe fiscale non prioritaire) ou choisir un contrat AV sans frais UC.",
            sources=["AMF, Directive OPCVM art. 10"],
        )
    except Exception as e:
        logger.info(f"R2 skip: {e}")
        return None


@regle("R3", famille="Frais excessifs")
def detecter_R3(profil) -> Alerte | None:
    """Fondement : AMF instruction DOC-2011-23 — frais d'entrée SCPI."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        scpi_montants = []
        for ligne in composition:
            if isinstance(ligne, dict):
                classe = ligne.get("classe_actif", "")
                libelle = ligne.get("libelle_libre", "")
                montant = ligne.get("montant_eur", 0)
            else:
                classe = getattr(ligne, "classe_actif", "")
                libelle = getattr(ligne, "libelle_libre", "")
                montant = getattr(ligne, "montant_eur", 0)
            if "SCPI" in str(classe).upper() or "SCPI" in str(libelle or "").upper():
                scpi_montants.append(montant or 0)

        if not scpi_montants:
            return None

        total_scpi = sum(scpi_montants)

        frais_entree = getattr(profil, "frais_entree_scpi", None)
        if frais_entree is not None and frais_entree <= 0.08:
            return None

        gain = total_scpi * 0.08 / 10
        return Alerte(
            code="R3",
            famille="Frais excessifs",
            severite=Severite.JAUNE,
            titre="SCPI : frais d'entrée élevés (>8%)",
            description=(
                "Les SCPI en direct affichent des frais d'entrée de 8 à 10%. "
                "Le marché secondaire et les SCPI sans frais d'entrée existent."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(total_scpi * 0.08, 0),
            action_concrete="Explorer les SCPI sans frais d'entrée (Remake Live, Iroko Zen) ou l'achat sur marché secondaire.",
            sources=["AMF instruction DOC-2011-23"],
        )
    except Exception as e:
        logger.info(f"R3 skip: {e}")
        return None


@regle("R4", famille="Frais excessifs")
def detecter_R4(profil) -> Alerte | None:
    """Fondement : AMF, Règlement OPCVM — TER fonds actifs excessif."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        fonds_actifs_montants = []
        for ligne in composition:
            if isinstance(ligne, dict):
                classe = ligne.get("classe_actif", "")
                libelle = ligne.get("libelle_libre", "")
                montant = ligne.get("montant_eur", 0)
            else:
                classe = getattr(ligne, "classe_actif", "")
                libelle = getattr(ligne, "libelle_libre", "")
                montant = getattr(ligne, "montant_eur", 0)
            classe_str = str(classe or "").lower()
            libelle_str = str(libelle or "").lower()
            if any(
                k in classe_str or k in libelle_str
                for k in ["fonds actif", "opcvm", "sicav", "fcp", "fonds_actif"]
            ):
                fonds_actifs_montants.append(montant or 0)

        if not fonds_actifs_montants:
            return None

        total = sum(fonds_actifs_montants)
        ter_moyen = getattr(profil, "ter_fonds_actifs", None)
        if ter_moyen is None or ter_moyen <= 0.02:
            return None

        gain = total * (ter_moyen - 0.002)
        return Alerte(
            code="R4",
            famille="Frais excessifs",
            severite=Severite.ROUGE,
            titre="Fonds actifs OPCVM avec TER > 2%",
            description=(
                f"Les fonds actifs affichent un TER de {ter_moyen:.1%} vs 0,2% pour les ETF équivalents. "
                f"Sur {total:,.0f} €, cela représente {gain:,.0f} €/an de surcoût."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Remplacer les fonds actifs par des ETF indiciels équivalents (Amundi, iShares, Vanguard).",
            sources=["AMF, Règlement OPCVM"],
        )
    except Exception as e:
        logger.info(f"R4 skip: {e}")
        return None


@regle("R5", famille="Frais excessifs")
def detecter_R5(profil) -> Alerte | None:
    """Fondement : MIF2, Directive 2014/65/UE — frais de courtage excessifs."""
    try:
        frais_par_ordre = getattr(profil, "frais_courtier_par_transaction", 0) or 0
        if frais_par_ordre <= 1.0:
            return None

        volume = getattr(profil, "volume_ordres_annuel", None)
        nb_ordres = 12  # assume monthly rebalancing
        if volume is not None and volume > 0:
            nb_ordres = int(volume / 1000) + 1

        gain = (frais_par_ordre - 1.0) * nb_ordres
        return Alerte(
            code="R5",
            famille="Frais excessifs",
            severite=Severite.JAUNE,
            titre="Frais de courtage excessifs (>1€/ordre)",
            description=(
                f"Vos frais de courtage sont de {frais_par_ordre:.2f} €/ordre vs 1€ chez les courtiers en ligne "
                f"(Trade Republic, Degiro). Estimé {nb_ordres} ordres/an."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Migrer vers un courtier à faibles frais : Trade Republic (1€), Degiro (1€+), Interactive Brokers.",
            sources=["MIF2, Directive 2014/65/UE"],
        )
    except Exception as e:
        logger.info(f"R5 skip: {e}")
        return None


@regle("R6", famille="Frais excessifs")
def detecter_R6(profil) -> Alerte | None:
    """Fondement : AMF recommandation 2014-12 — double couche de frais (fond de fonds)."""
    try:
        fond_de_fonds = getattr(profil, "fond_de_fonds", None)
        if not fond_de_fonds:
            return None

        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        gain = patrimoine * 0.005

        return Alerte(
            code="R6",
            famille="Frais excessifs",
            severite=Severite.ROUGE,
            titre="Double couche de frais (fonds de fonds)",
            description=(
                "Un fonds de fonds génère deux niveaux de frais : les frais du fonds chapeau + les frais des fonds sous-jacents. "
                "Coût additionnel typique : 0,5%/an."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Investir directement dans les fonds sous-jacents ou utiliser des ETF indiciels.",
            sources=["AMF recommandation 2014-12"],
        )
    except Exception as e:
        logger.info(f"R6 skip: {e}")
        return None
