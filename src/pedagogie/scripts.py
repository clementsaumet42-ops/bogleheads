"""Chargement et rendu des scripts de restitution EC→client."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).parent.parent.parent
_SCRIPTS_YAML_PATH = _ROOT / "config" / "scripts_restitution.yaml"

# Clés utilisées par le code — toute clé manquante dans le YAML provoque un fail-fast.
_CLES_REQUISES: frozenset[str] = frozenset(
    [
        "profilage.introduction",
        "profilage.convergence_claire",
        "profilage.divergence_detectee",
        "allocation.mode_simple_acwi",
        "allocation.obligations",
        "allocation.alternative_ecartee_all_us",
        "etf.pourquoi_cet_etf",
        "etf.pourquoi_pas_alternative",
        "asset_location.obligations_en_av",
        "asset_location.actions_en_pea",
        "fiscalite.cto_pfu",
        "fiscalite.pea_apres_5_ans",
        "rebalancement.etape_1_gratuit",
        "rebalancement.etape_2_flux",
        "rebalancement.etape_3_ventes",
    ]
)

_cache: dict | None = None


def charger_scripts_restitution() -> dict:
    """Charge et valide le fichier config/scripts_restitution.yaml.

    Returns:
        Dictionnaire plat {section.cle: texte_template}.

    Raises:
        FileNotFoundError: Si le fichier YAML est absent.
        KeyError: Si une clé requise par le code est absente du YAML.
    """
    global _cache
    if _cache is not None:
        return _cache

    if not _SCRIPTS_YAML_PATH.exists():
        raise FileNotFoundError(
            f"Fichier de scripts de restitution introuvable : {_SCRIPTS_YAML_PATH}"
        )

    with _SCRIPTS_YAML_PATH.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    scripts_raw: dict = raw.get("scripts", {})

    # Aplatir la structure imbriquée {section: {cle: texte}} → {"section.cle": texte}
    flat: dict[str, str] = {}
    for section, entries in scripts_raw.items():
        if isinstance(entries, dict):
            for cle, texte in entries.items():
                flat[f"{section}.{cle}"] = str(texte)
        else:
            flat[section] = str(entries)

    # Fail-fast : vérifier que toutes les clés requises sont présentes
    manquantes = _CLES_REQUISES - flat.keys()
    if manquantes:
        raise KeyError(
            f"Clés manquantes dans config/scripts_restitution.yaml : "
            f"{sorted(manquantes)}. "
            "Ajoutez ces clés avant d'utiliser le module src.pedagogie."
        )

    _cache = flat
    return _cache


def rendre_script(cle: str, variables: dict[str, object] | None = None) -> str:
    """Retourne un script de restitution avec les variables substituées.

    Args:
        cle: Clé du script au format "section.sous_cle" (ex: "allocation.mode_simple_acwi").
        variables: Dictionnaire de variables à substituer dans le template.
                   Les variables non trouvées dans le template sont ignorées silencieusement.

    Returns:
        Texte du script avec toutes les variables substituées.
        Les placeholders non substituables restent tels quels (pas d'exception).

    Raises:
        KeyError: Si la clé n'existe pas dans les scripts chargés.
    """
    scripts = charger_scripts_restitution()

    if cle not in scripts:
        raise KeyError(
            f"Script '{cle}' introuvable dans config/scripts_restitution.yaml. "
            f"Clés disponibles : {sorted(scripts.keys())}"
        )

    template = scripts[cle]

    if not variables:
        return template.strip()

    # Substitution permissive : les clés absentes du template sont ignorées,
    # les placeholders sans variable restent tels quels.
    try:
        return template.format_map(_SafeFormatMap(variables)).strip()
    except Exception:
        return template.strip()


class _SafeFormatMap(dict):
    """dict.format_map() permissif : les clés manquantes sont conservées telles quelles."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
