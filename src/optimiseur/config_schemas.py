"""
Schémas Pydantic pour la configuration enrichie de l'optimiseur Markowitz (S11-A).

Valide la présence de métadonnées de calibration, sources documentées et
intervalles de confiance pour chaque classe d'actifs.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT / "config"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="allow")


# ─── Métadonnées de calibration ───────────────────────────────────────────────


class PeriodeDonnees(_Strict):
    debut: date
    fin: date
    nb_observations_mensuelles: int = Field(ge=1)


class MethodologieItem(_Strict):
    methode: str
    source: str
    url: str | None = None
    shrinkage_applique: bool | None = None


class Methodologie(_Strict):
    rendements_esperes: MethodologieItem
    volatilites: MethodologieItem
    correlations: MethodologieItem


class CalibrationMetadata(_Strict):
    date_calibration: date
    periode_donnees: PeriodeDonnees
    methodologie: Methodologie
    avertissements: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def avertissements_non_vides(self) -> CalibrationMetadata:
        if not self.avertissements:
            raise ValueError("La liste d'avertissements ne doit pas être vide.")
        for a in self.avertissements:
            if not a.strip():
                raise ValueError("Un avertissement est vide.")
        return self


# ─── Rendements / volatilités documentés ─────────────────────────────────────


class RendementEspere(_Strict):
    valeur: float
    intervalle_confiance_95: tuple[float, float] | None = None
    source_specifique: str

    @model_validator(mode="after")
    def ic_coherent(self) -> RendementEspere:
        if self.intervalle_confiance_95 is not None:
            lo, hi = self.intervalle_confiance_95
            if lo > hi:
                raise ValueError(
                    f"IC 95% incohérent : borne inférieure {lo} > borne supérieure {hi}"
                )
        return self


# ─── Config enrichie complète ─────────────────────────────────────────────────


class ConfigOptimiseurEnrichi(_Strict):
    """
    Configuration complète de l'optimiseur avec métadonnées de calibration (S11-A).

    Valide :
    - Présence des métadonnées (date, période, sources, avertissements)
    - Source documentée pour chaque rendement espéré
    - Symétrie de la matrice de corrélations
    """

    metadonnees: CalibrationMetadata
    rendements_esperes: dict[str, RendementEspere]
    correlations: dict[str, dict[str, float]] | None = None

    # Champs complémentaires hérités (pass-through)
    classes_actifs: dict[str, Any] | None = None
    profils_aversion_risque: dict[str, Any] | None = None
    frais_gestion_enveloppes: dict[str, float] | None = None
    taux_sans_risque: float | None = None
    hypotheses_meta: dict[str, Any] | None = None
    volatilites: dict[str, RendementEspere] | None = None

    @model_validator(mode="after")
    def sources_presentes(self) -> ConfigOptimiseurEnrichi:
        for classe, re in self.rendements_esperes.items():
            if not re.source_specifique or not re.source_specifique.strip():
                raise ValueError(f"La classe '{classe}' n'a pas de source_specifique renseignée.")
        return self

    @model_validator(mode="after")
    def correlations_symetriques(self) -> ConfigOptimiseurEnrichi:
        if self.correlations is None:
            return self
        for ci, row in self.correlations.items():
            for cj, val in row.items():
                # Diagonale doit être 1
                if ci == cj and abs(val - 1.0) > 1e-9:
                    raise ValueError(
                        f"Corrélation diagonale incohérente : correlations[{ci}][{ci}] = {val} ≠ 1"
                    )
                # Valeurs dans [-1, 1]
                if val < -1.0 - 1e-9 or val > 1.0 + 1e-9:
                    raise ValueError(f"Corrélation hors [-1, 1] : correlations[{ci}][{cj}] = {val}")
                # Symétrie
                if cj in self.correlations and ci in self.correlations[cj]:
                    inverse = self.correlations[cj][ci]
                    if abs(val - inverse) > 1e-9:
                        raise ValueError(
                            f"Matrice de corrélation non symétrique : "
                            f"[{ci}][{cj}]={val} mais [{cj}][{ci}]={inverse}"
                        )
        return self


# ─── Chargeur ─────────────────────────────────────────────────────────────────


def charger_config_enrichie(chemin: str | Path | None = None) -> ConfigOptimiseurEnrichi:
    """Charge et valide config/optimiseur.yaml avec les métadonnées S11-A."""
    if chemin is None:
        chemin = CONFIG_DIR / "optimiseur.yaml"
    with open(chemin, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return ConfigOptimiseurEnrichi.model_validate(raw)
