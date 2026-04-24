from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ProfilGrableLytton(BaseModel):
    """Profil Grable & Lytton (1999) — 13 questions, scores 1-4."""

    reponses: dict[int, int] = Field(
        description="Dict {num_question: score (1-4)} pour les 13 questions"
    )
    score_brut: int = Field(default=0, ge=13, le=52)  # max théorique : 13×4=52
    categorie: str = Field(
        default="moyenne",
        description="tres_faible | faible | moyenne | elevee | tres_elevee",
    )

    @model_validator(mode="before")
    @classmethod
    def calculer_score_et_categorie(cls, data: dict) -> dict:
        if isinstance(data, dict) and "reponses" in data:
            reponses = data["reponses"]
            if reponses and "score_brut" not in data:
                for q, v in reponses.items():
                    if int(q) not in range(1, 14):
                        raise ValueError(f"Question {q} invalide (1-13 attendu)")
                    if int(v) not in range(1, 5):
                        raise ValueError(f"Score {v} invalide pour q{q} (1-4 attendu)")
                score = sum(int(v) for v in reponses.values())
                data["score_brut"] = score
                if score <= 18:
                    data["categorie"] = "tres_faible"
                elif score <= 22:
                    data["categorie"] = "faible"
                elif score <= 28:
                    data["categorie"] = "moyenne"
                elif score <= 32:
                    data["categorie"] = "elevee"
                else:
                    data["categorie"] = "tres_elevee"
        return data


def calculer_profil_grable_lytton(reponses: dict[int, int]) -> ProfilGrableLytton:
    """
    Calcule le profil Grable & Lytton à partir des réponses.

    Parameters
    ----------
    reponses : dict {num_question (1-13): score (1-4)}

    Returns
    -------
    ProfilGrableLytton
    """
    if len(reponses) != 13:
        raise ValueError(f"13 réponses requises, {len(reponses)} fournies")
    for q in range(1, 14):
        if q not in reponses:
            raise ValueError(f"Question {q} manquante")
    return ProfilGrableLytton(reponses=reponses)
