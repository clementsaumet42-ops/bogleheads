from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionComportementale(BaseModel):
    """Questions comportementales complémentaires au Grable-Lytton."""

    reaction_baisse_declaree: str = Field(
        default="conserver",
        description="vendre_tout | vendre_partie | conserver | acheter_plus",
    )
    reaction_baisse_observee: str = Field(
        default="conserver",
        description="vendre_tout | vendre_partie | conserver | acheter_plus",
    )
    horizon_emotionnel_ans: int = Field(default=5, ge=0, le=50)
    biais_ancrage: bool = Field(default=False)
    biais_recence: bool = Field(default=False)
    biais_overconfidence: bool = Field(default=False)

    def horizon_emotionnel_proxy(self) -> str:
        if self.horizon_emotionnel_ans <= 2:
            return "court_terme"
        elif self.horizon_emotionnel_ans <= 7:
            return "moyen_terme"
        else:
            return "long_terme"

    def score_coherence_comportementale(self) -> float:
        """
        Score de cohérence comportementale entre 0 et 1.

        1 = comportement cohérent, 0 = incohérent.
        """
        _order = {
            "vendre_tout": 0,
            "vendre_partie": 1,
            "conserver": 2,
            "acheter_plus": 3,
        }
        decl = _order.get(self.reaction_baisse_declaree, 2)
        obs = _order.get(self.reaction_baisse_observee, 2)
        diff = abs(decl - obs)
        coherence = max(0.0, 1.0 - diff / 3.0)
        nb_biais = sum([self.biais_ancrage, self.biais_recence, self.biais_overconfidence])
        malus = nb_biais * 0.1
        return max(0.0, coherence - malus)
