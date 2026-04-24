from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionnaireMIF2(BaseModel):
    """Questionnaire MIF2 — connaissance et expérience client (Art. 325-3 RG AMF)."""

    connait_actions: bool = False
    connait_obligations: bool = False
    connait_opcvm_etf: bool = False
    connait_produits_derives: bool = False
    a_deja_investi: bool = False
    formation_financiere: str = Field(
        default="aucune",
        description="aucune | notions | specialisee | professionnel",
    )
    annees_experience: str = Field(
        default="jamais",
        description="jamais | moins_2 | 2_a_5 | plus_5",
    )
    frequence_operations: str = Field(
        default="jamais",
        description="jamais | rarement | regulierement | tres_frequent",
    )

    def niveau_connaissance_global(self) -> str:
        score = sum(
            [
                self.connait_actions,
                self.connait_obligations,
                self.connait_opcvm_etf,
                self.connait_produits_derives,
                self.a_deja_investi,
            ]
        )
        exp_score = {"jamais": 0, "moins_2": 1, "2_a_5": 2, "plus_5": 3}.get(
            self.annees_experience, 0
        )
        total = score + exp_score
        if total <= 2:
            return "debutant"
        elif total <= 5:
            return "intermediaire"
        else:
            return "avance"
