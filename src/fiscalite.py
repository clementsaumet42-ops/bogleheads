# -*- coding: utf-8 -*-
"""
Module de calcul fiscal — France 2026
Fonctions de calcul PFU, CEHR, CDHR, IS, mark-to-market et contrat capitalisation IS.
Sources : CGI, BOFiP, LF 2025/2026.
"""

from __future__ import annotations
from pathlib import Path
import yaml


# ---------------------------------------------------------------------------
# Chargement des paramètres fiscaux depuis le YAML de configuration
# ---------------------------------------------------------------------------

def _charger_config_fiscalite(chemin: str | Path | None = None) -> dict:
    """Charge la configuration fiscale depuis le fichier YAML.

    Args:
        chemin: Chemin vers le fichier YAML. Si None, utilise le chemin par défaut.

    Returns:
        Dictionnaire de paramètres fiscaux.
    """
    if chemin is None:
        # Remonte depuis src/ jusqu'à la racine du projet
        racine = Path(__file__).resolve().parent.parent
        chemin = racine / "config" / "fiscalite_2026.yaml"
    with open(chemin, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Instance chargée une seule fois au niveau du module
try:
    _CONFIG = _charger_config_fiscalite()
except FileNotFoundError:
    # Valeurs de secours pour éviter un crash si le YAML n'est pas trouvé
    _CONFIG = {}


# ---------------------------------------------------------------------------
# Constantes fiscales (extraites du YAML ou valeurs par défaut)
# ---------------------------------------------------------------------------

def _get(clef_path: str, defaut):
    """Accès sûr à une valeur imbriquée dans _CONFIG.

    Args:
        clef_path: Chemin de clés séparées par des points (ex: 'pfu.taux_total').
        defaut: Valeur par défaut si la clé n'existe pas.

    Returns:
        Valeur trouvée ou défaut.
    """
    parties = clef_path.split(".")
    noeud = _CONFIG
    for partie in parties:
        if not isinstance(noeud, dict) or partie not in noeud:
            return defaut
        noeud = noeud[partie]
    return noeud


# ---------------------------------------------------------------------------
# PFU — Prélèvement Forfaitaire Unique (art. 200 A CGI)
# ---------------------------------------------------------------------------

def calculer_pfu(montant_pv: float, taux_pfu: float | None = None) -> float:
    """Calcule le PFU (Flat Tax) applicable à une plus-value mobilière.

    Le PFU s'élève à 31.4 % : 12.8 % d'IR + 18.6 % de prélèvements sociaux.
    Source : art. 200 A CGI, LF 2018.

    Args:
        montant_pv: Montant de la plus-value (ou dividende) en euros.
        taux_pfu: Taux PFU à appliquer. Si None, utilise le taux du YAML (31.4 %).

    Returns:
        Montant d'impôt PFU en euros.

    Raises:
        ValueError: Si le montant est négatif.

    Examples:
        >>> calculer_pfu(10000)
        3140.0
    """
    if montant_pv < 0:
        raise ValueError("La plus-value ne peut pas être négative pour le calcul PFU.")
    if taux_pfu is None:
        taux_pfu = _get("pfu.taux_total", 0.314)
    return round(montant_pv * taux_pfu, 2)


# ---------------------------------------------------------------------------
# CEHR — Contribution Exceptionnelle sur les Hauts Revenus (art. 223 sexies CGI)
# ---------------------------------------------------------------------------

def calculer_cehr(
    rfr: float,
    situation_familiale: str = "celibataire",
    taux_t1: float | None = None,
    taux_t2: float | None = None,
) -> float:
    """Calcule la Contribution Exceptionnelle sur les Hauts Revenus (CEHR).

    Tranches pour un célibataire (art. 223 sexies CGI) :
    - 3 % sur la fraction du RFR entre 250 000 € et 500 000 €
    - 4 % sur la fraction du RFR au-delà de 500 000 €

    Tranches pour un couple/PACS :
    - 3 % entre 500 000 € et 1 000 000 €
    - 4 % au-delà de 1 000 000 €

    Args:
        rfr: Revenu Fiscal de Référence en euros.
        situation_familiale: 'celibataire' ou 'couple'.
        taux_t1: Taux tranche 1 (défaut : 3 %).
        taux_t2: Taux tranche 2 (défaut : 4 %).

    Returns:
        Montant de CEHR en euros.

    Examples:
        >>> calculer_cehr(600000, 'celibataire')
        11500.0
    """
    if taux_t1 is None:
        taux_t1 = _get("cehr.taux_tranche_1", 0.03)
    if taux_t2 is None:
        taux_t2 = _get("cehr.taux_tranche_2", 0.04)

    situation = situation_familiale.lower()

    if situation in ("celibataire", "célibataire", "seul", "veuf"):
        seuil_t1 = _get("cehr.celibataire.seuil_3pct", 250_000)
        seuil_t2 = _get("cehr.celibataire.seuil_4pct", 500_000)
    elif situation in ("couple", "marie", "marié", "pacs", "pacsé"):
        seuil_t1 = _get("cehr.couple.seuil_3pct", 500_000)
        seuil_t2 = _get("cehr.couple.seuil_4pct", 1_000_000)
    else:
        raise ValueError(
            f"Situation familiale inconnue : '{situation_familiale}'. "
            "Valeurs acceptées : 'celibataire', 'couple'."
        )

    cehr = 0.0

    # Tranche 1 : 3 %
    if rfr > seuil_t1:
        base_t1 = min(rfr, seuil_t2) - seuil_t1
        cehr += base_t1 * taux_t1

    # Tranche 2 : 4 %
    if rfr > seuil_t2:
        base_t2 = rfr - seuil_t2
        cehr += base_t2 * taux_t2

    return round(cehr, 2)


# ---------------------------------------------------------------------------
# CDHR — Contribution Différentielle sur les Hauts Revenus (LF 2025 art. 3)
# Reconduite 2026 sous réserve — À VALIDER sur LF 2026
# ---------------------------------------------------------------------------

def calculer_cdhr(
    rfr: float,
    impot_avant_cdhr: float,
    situation_familiale: str = "celibataire",
    taux_minimal: float | None = None,
) -> float:
    """Calcule la Contribution Différentielle sur les Hauts Revenus (CDHR).

    La CDHR vise à garantir un taux effectif global minimum de 20 % pour les
    contribuables dont le RFR dépasse 250 000 € (célibataire) ou 500 000 € (couple).
    Elle est égale à la différence entre l'impôt minimal cible et l'impôt réellement dû.

    Source : art. 3 LF 2025 — À VALIDER reconduite LF 2026.

    Args:
        rfr: Revenu Fiscal de Référence en euros.
        impot_avant_cdhr: Impôt total dû avant application de la CDHR (IR + CEHR).
        situation_familiale: 'celibataire' ou 'couple'.
        taux_minimal: Taux effectif global minimal (défaut : 20 %).

    Returns:
        Montant de CDHR à payer (0 si le seuil n'est pas atteint ou si le taux
        effectif est déjà supérieur au minimum).

    Examples:
        >>> calculer_cdhr(300000, 40000)  # 40000/300000 = 13.3% < 20% → CDHR due
        20000.0
    """
    if taux_minimal is None:
        taux_minimal = _get("cdhr.taux_minimal", 0.20)

    situation = situation_familiale.lower()
    if situation in ("celibataire", "célibataire", "seul", "veuf"):
        seuil_declenchement = _get("cdhr.seuil_celibataire", 250_000)
    elif situation in ("couple", "marie", "marié", "pacs", "pacsé"):
        seuil_declenchement = _get("cdhr.seuil_couple", 500_000)
    else:
        raise ValueError(f"Situation familiale inconnue : '{situation_familiale}'.")

    # La CDHR ne s'applique qu'au-delà du seuil
    if rfr <= seuil_declenchement:
        return 0.0

    # Calcul de l'impôt minimal théorique
    impot_minimal = rfr * taux_minimal

    # La CDHR est la différence positive (on ne rembourse pas)
    cdhr = max(0.0, impot_minimal - impot_avant_cdhr)
    return round(cdhr, 2)


# ---------------------------------------------------------------------------
# IS — Impôt sur les Sociétés (art. 219 CGI)
# ---------------------------------------------------------------------------

def calculer_is(
    benefice: float,
    seuil_taux_reduit: float | None = None,
    taux_reduit: float | None = None,
    taux_normal: float | None = None,
) -> float:
    """Calcule l'impôt sur les sociétés (IS) selon les taux en vigueur.

    Taux 2026 (sous conditions de PME — art. 219 I b CGI) :
    - 15 % sur les 42 500 premiers euros de bénéfice
    - 25 % sur la fraction au-delà de 42 500 €

    Note : Le taux réduit est conditionné (CA < 10 M€, capital libéré détenu à 75 %
    par des personnes physiques). Cette fonction ne vérifie pas ces conditions.

    Args:
        benefice: Bénéfice imposable en euros (doit être positif).
        seuil_taux_reduit: Plafond du taux réduit (défaut : 42 500 €).
        taux_reduit: Taux réduit PME (défaut : 15 %).
        taux_normal: Taux normal (défaut : 25 %).

    Returns:
        Montant d'IS en euros.

    Examples:
        >>> calculer_is(50000)
        8250.0
    """
    if benefice < 0:
        return 0.0  # En cas de déficit, pas d'IS

    if seuil_taux_reduit is None:
        seuil_taux_reduit = _get("is.seuil_taux_reduit", 42_500)
    if taux_reduit is None:
        taux_reduit = _get("is.taux_reduit", 0.15)
    if taux_normal is None:
        taux_normal = _get("is.taux_normal", 0.25)

    # Fraction au taux réduit
    base_reduite = min(benefice, seuil_taux_reduit)
    is_reduit = base_reduite * taux_reduit

    # Fraction au taux normal
    base_normale = max(0.0, benefice - seuil_taux_reduit)
    is_normal = base_normale * taux_normal

    return round(is_reduit + is_normal, 2)


# ---------------------------------------------------------------------------
# Mark-to-Market IS — art. 209-0 A CGI
# Piège fiscal pour les sociétés IS détenant des OPCVM/ETF en CTO
# ---------------------------------------------------------------------------

def calculer_mark_to_market_is(
    valeur_debut: float,
    valeur_fin: float,
    taux_is: float | None = None,
) -> dict:
    """Calcule la base imposable et l'IS dû au titre du régime mark-to-market.

    Art. 209-0 A CGI : Les OPCVM (dont les ETF UCITS) détenus par une société
    à l'IS en compte-titres ordinaire sont taxés annuellement sur la variation
    de leur valeur liquidative, même en l'absence de cession.

    ATTENTION : Ce régime constitue un piège majeur pour les trésoreries d'entreprise
    investies en ETF via CTO. Préférer le contrat de capitalisation IS.

    Args:
        valeur_debut: Valeur en début d'exercice (ou prix d'acquisition) en euros.
        valeur_fin: Valeur en fin d'exercice en euros.
        taux_is: Taux IS applicable. Si None, utilise le taux normal (25 %).

    Returns:
        Dictionnaire avec 'gain_latent', 'base_imposable', 'is_du'.

    Examples:
        >>> r = calculer_mark_to_market_is(100000, 105000)
        >>> r['base_imposable']
        5000.0
    """
    if taux_is is None:
        taux_is = _get("is.taux_normal", 0.25)

    gain_latent = valeur_fin - valeur_debut
    # La base imposable est le gain latent (positif ou négatif)
    base_imposable = gain_latent
    # L'IS n'est dû que sur les gains positifs (les pertes réduisent le résultat)
    is_du = max(0.0, base_imposable) * taux_is

    return {
        "gain_latent": round(gain_latent, 2),
        "base_imposable": round(base_imposable, 2),
        "is_du": round(is_du, 2),
    }


# ---------------------------------------------------------------------------
# Contrat de Capitalisation IS — Base forfaitaire annuelle
# Art. 38 sexdecies GB Annexe III CGI
# ---------------------------------------------------------------------------

def calculer_base_taxable_contrat_cap_is(
    prime_nette: float,
    tme: float | None = None,
) -> dict:
    """Calcule la base imposable forfaitaire annuelle d'un contrat de capitalisation IS.

    Pour les sociétés à l'IS, la base imposable annuelle d'un contrat de capitalisation
    est calculée de manière forfaitaire :
        Base = 105 % × TME × prime_nette

    Cette approche est bien plus favorable que le mark-to-market de l'art. 209-0 A CGI
    applicable aux ETF détenus en CTO direct.

    Source : art. 38 sexdecies GB Ann. III CGI, BOFiP BIC-BASE-20-20.

    Args:
        prime_nette: Montant des primes nettes versées au contrat en euros.
        tme: Taux Moyen des Emprunts d'État. Si None, utilise la valeur du YAML.

    Returns:
        Dictionnaire avec 'prime_nette', 'tme', 'base_imposable_annuelle', 'is_estime'.

    Examples:
        >>> r = calculer_base_taxable_contrat_cap_is(100000, 0.03)
        >>> r['base_imposable_annuelle']
        3150.0
    """
    if tme is None:
        tme = _get("tme", 0.030)

    # Formule réglementaire : 105 % × TME × prime nette
    base_imposable = 1.05 * tme * prime_nette
    # IS estimé au taux normal (25 %)
    taux_is = _get("is.taux_normal", 0.25)
    is_estime = base_imposable * taux_is

    return {
        "prime_nette": round(prime_nette, 2),
        "tme": tme,
        "base_imposable_annuelle": round(base_imposable, 2),
        "is_estime": round(is_estime, 2),
    }


# ---------------------------------------------------------------------------
# Utilitaire : taux effectif global
# ---------------------------------------------------------------------------

def calculer_taux_effectif(impot_total: float, revenu_total: float) -> float:
    """Calcule le taux effectif d'imposition.

    Args:
        impot_total: Total des impôts et contributions dus en euros.
        revenu_total: Revenu de référence en euros.

    Returns:
        Taux effectif (entre 0 et 1).

    Raises:
        ValueError: Si le revenu total est nul ou négatif.
    """
    if revenu_total <= 0:
        raise ValueError("Le revenu total doit être strictement positif.")
    return round(impot_total / revenu_total, 6)
