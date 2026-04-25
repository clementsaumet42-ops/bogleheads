"""Module S11-C — Drag fiscal intra-NAV des ETF.

Calcule le TER effectif = TER affiché + drag de withholding intra-NAV.

La retenue à la source (withholding tax) est prélevée dans la valeur
liquidative de l'ETF physique, de manière transparente pour le détenteur.
Elle ne figure ni sur le relevé client ni dans la 2042 : c'est un drag
silencieux de 0 à 60 bps/an selon (domicile × réplication × exposition_geo).

Sources :
  - Traité IE-US (15 % US → Irlande, au lieu du taux standard 30 %)
  - Directive UCITS + pratique marché ETF physique Europe
  - Synthétiques swap : le swap annule la withholding côté réplication (0 %)
  - Données de yield par défaut : justETF / MSCI factsheets 2024

Nota bene : ce module ne touche pas à la fiscalité du détenteur direct
(dividendes bruts, case 2DC, conventions bilatérales) — hors scope S11-C.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ─── Constantes ──────────────────────────────────────────────────────────────

# Drag de réplication (tracking error structurel) — placeholder pour S12
# Peut être alimenté ultérieurement avec un tracking error historique moyen.
DRAG_REPLICATION_BPS: float = 0.0

# Yields par défaut par exposition géographique (% annuel brut, source MSCI 2024)
_YIELDS_DEFAUT: dict[str, float] = {
    "US": 1.5,
    "Monde_dev": 1.8,
    "Monde_ACWI": 1.9,
    "Emergents": 2.5,
    "Europe": 3.0,
    "France": 3.0,
    "Japon": 2.0,
}

# Table de retenues effectives (%) selon domicile × exposition_geo
# Pour les physiques :
#   - IE × US  → 15 % (traité bilatéral Irlande-USA, Art. 10.2 CDI 1997)
#   - LU × US  → 30 % (pas de traité comparable à IE pour dividendes US)
#   - FR × US  → 15 % (CDI France-USA 1994, taux réduit pour OPCVM)
#   - DE × US  → 15 % (CDI Allemagne-USA, taux équivalent)
#   - * × Europe/France → 0 % (UCITS européen sur sous-jacents EUR, pas de WHT)
#   - * × Emergents → 10 % pondéré (mélange traités Chine/Inde/Brésil)
#   - * × Monde_dev → 15 % pondéré (~65 % US à 15 % + 35 % Europe/Japon)
#   - * × Monde_ACWI → 14 % pondéré (idem Monde_dev + part EM ~10 % à 10 %)
#   - * × Japon → 15 % (CDI Irlande/LU/FR/DE - Japon, taux réduit standard)
# Les synthétiques (swap) → 0 % sur la jambe répliquée
_RETENUE_PHYSIQUE: dict[tuple[str, str], float] = {
    # (domicile_iso, exposition_geo) : retenue effective en %
    ("IE", "US"): 15.0,
    ("LU", "US"): 30.0,
    ("FR", "US"): 15.0,
    ("DE", "US"): 15.0,
    ("IE", "Europe"): 0.0,
    ("LU", "Europe"): 0.0,
    ("FR", "Europe"): 0.0,
    ("DE", "Europe"): 0.0,
    ("IE", "France"): 0.0,
    ("LU", "France"): 0.0,
    ("FR", "France"): 0.0,
    ("DE", "France"): 0.0,
    ("IE", "Emergents"): 10.0,
    ("LU", "Emergents"): 10.0,
    ("FR", "Emergents"): 10.0,
    ("DE", "Emergents"): 10.0,
    ("IE", "Monde_dev"): 15.0,
    ("LU", "Monde_dev"): 15.0,
    ("FR", "Monde_dev"): 15.0,
    ("DE", "Monde_dev"): 15.0,
    ("IE", "Monde_ACWI"): 14.0,
    ("LU", "Monde_ACWI"): 14.0,
    ("FR", "Monde_ACWI"): 14.0,
    ("DE", "Monde_ACWI"): 14.0,
    ("IE", "Japon"): 15.0,
    ("LU", "Japon"): 15.0,
    ("FR", "Japon"): 15.0,
    ("DE", "Japon"): 15.0,
}

# Domiciles reconnus
_DOMICILES_PHYSIQUES = {"IE", "LU", "FR", "DE"}

# Réplications synthétiques → drag = 0
_REPLICATIONS_SYNTHETIQUES = {"synthetique_swap"}

# Réplications physiques reconnues
_REPLICATIONS_PHYSIQUES = {"physique_full", "physique_sampling"}


# ─── Fonction principale ─────────────────────────────────────────────────────


def calculer_drag_fiscal_etf(
    replication: str | None,
    domicile: str | None,
    exposition_geo: str | None,
    yield_brut_estime_pct: float | None = None,
    inclure_drag_replication: bool = True,
) -> float:
    """Retourne le drag fiscal annuel estimé (en bps) dû à la withholding tax
    intra-NAV non récupérée par l'enveloppe ETF.

    Les ETF synthétiques (swap) annulent la withholding sur la jambe répliquée
    → drag = 0 sur la part synthétique.

    Les ETF physiques domiciliés en Irlande bénéficient du traité IE-US (15 %
    au lieu de 30 %) sur les dividendes US.

    Les ETF physiques domiciliés au Luxembourg subissent généralement 30 %
    sur dividendes US (pas de traité favorable comparable).

    Arguments
    ---------
    replication : str | None
        "physique_full", "physique_sampling" ou "synthetique_swap".
        Si None : retourne 0.0 + warning.
    domicile : str | None
        Code ISO 2 lettres du domicile : "IE", "LU", "FR", "DE".
        Si None : retourne 0.0 + warning.
    exposition_geo : str | None
        "US", "Europe", "Monde_dev", "Monde_ACWI", "Emergents", "France",
        "Japon". Si None : retourne 0.0 + warning.
    yield_brut_estime_pct : float | None
        Override du yield brut (%). Si None, utilise la table par défaut.
    inclure_drag_replication : bool
        Anticipation S12 — sera utilisé pour ajouter DRAG_REPLICATION_BPS au
        résultat (tracking error structurel). Sans effet pour l'instant
        (DRAG_REPLICATION_BPS = 0). Conservé pour la stabilité de l'API.

    Retourne
    --------
    float : drag en bps (points de base). 0.0 si données manquantes.
    """
    # Vérification des champs obligatoires
    if replication is None or domicile is None or exposition_geo is None:
        logger.warning(
            "calculer_drag_fiscal_etf : champ(s) manquant(s) "
            "(replication=%r, domicile=%r, exposition_geo=%r) → drag = 0",
            replication,
            domicile,
            exposition_geo,
        )
        return 0.0

    # Normalisation
    replication_norm = str(replication).strip().lower()
    domicile_norm = str(domicile).strip().upper()
    exposition_norm = str(exposition_geo).strip()

    # ETF synthétique → drag withholding = 0
    if replication_norm in _REPLICATIONS_SYNTHETIQUES:
        return 0.0

    # ETF physique (full ou sampling) — calcul de la retenue
    if replication_norm not in _REPLICATIONS_PHYSIQUES:
        logger.warning(
            "calculer_drag_fiscal_etf : réplication inconnue %r → drag = 0",
            replication,
        )
        return 0.0

    if domicile_norm not in _DOMICILES_PHYSIQUES:
        logger.warning(
            "calculer_drag_fiscal_etf : domicile inconnu %r → drag = 0",
            domicile,
        )
        return 0.0

    # Lookup retenue effective
    retenue_pct = _RETENUE_PHYSIQUE.get((domicile_norm, exposition_norm))
    if retenue_pct is None:
        logger.warning(
            "calculer_drag_fiscal_etf : combinaison (domicile=%r, "
            "exposition_geo=%r) non trouvée → drag = 0",
            domicile,
            exposition_geo,
        )
        return 0.0

    # Yield brut (% annuel)
    if yield_brut_estime_pct is not None:
        yield_pct = float(yield_brut_estime_pct)
    else:
        yield_pct = _YIELDS_DEFAUT.get(exposition_norm, 0.0)

    # drag_bps = retenue_effective (%) × yield_brut (%) × 100
    # = (retenue/100) × (yield/100) × 10000
    drag_bps = (retenue_pct / 100.0) * (yield_pct / 100.0) * 10_000.0
    # DRAG_REPLICATION_BPS sera ajouté ici en S12 si inclure_drag_replication=True
    if inclure_drag_replication:
        drag_bps += DRAG_REPLICATION_BPS
    return round(drag_bps, 2)
