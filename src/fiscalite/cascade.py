"""
Cascade fiscale — Modèles Pydantic et orchestrateur principal
Calcul détaillé ligne par ligne avec sources juridiques
"""

from pydantic import BaseModel, Field


class LigneCalcul(BaseModel):
    """Une ligne de calcul fiscal avec formule et source juridique."""

    libelle: str = Field(..., description="Description de la ligne")
    montant: float = Field(..., description="Montant en €")
    formule: str = Field(..., description="Formule de calcul")
    source: str = Field(..., description="Article de loi (CGI, CMF, CSS)")


class ResultatFiscal(BaseModel):
    """Résultat fiscal complet d'une opération."""

    montant_brut: float = Field(..., description="Montant brut avant impôts")
    impot_ir: float = Field(default=0.0, description="Impôt sur le revenu")
    prelevements_sociaux: float = Field(default=0.0, description="Prélèvements sociaux")
    cehr: float = Field(default=0.0, description="Contribution exceptionnelle hauts revenus")
    cdhr: float = Field(default=0.0, description="Contribution différentielle hauts revenus")
    total_impots: float = Field(..., description="Total des impôts et prélèvements")
    montant_net: float = Field(..., description="Montant net après impôts")
    taux_effectif: float = Field(..., description="Taux d'imposition effectif")
    cascade: list[LigneCalcul] = Field(default_factory=list, description="Détail ligne par ligne")
    articles_cites: list[str] = Field(default_factory=list, description="Articles de loi cités")
    avertissements: list[str] = Field(default_factory=list, description="Avertissements fiscaux")

    def ajouter_ligne(self, libelle: str, montant: float, formule: str, source: str) -> None:
        """Ajoute une ligne à la cascade."""
        self.cascade.append(
            LigneCalcul(libelle=libelle, montant=montant, formule=formule, source=source)
        )
        if source not in self.articles_cites:
            self.articles_cites.append(source)

    def ajouter_avertissement(self, message: str) -> None:
        """Ajoute un avertissement."""
        if message not in self.avertissements:
            self.avertissements.append(message)


def calculer_fiscalite_operation(
    operation: dict, profil: dict, annee_fiscale: int = 2026
) -> ResultatFiscal:
    """
    Orchestrateur principal : calcule la fiscalité d'une opération.

    Args:
        operation: dict décrivant l'opération
            - type: "rachat_av", "cession_cto", "retrait_pea", "sortie_per"
            - montant_brut: float
            - details: dict spécifique au type d'opération
        profil: dict du contribuable
            - situation: "celibataire" | "couple"
            - rfr: float (Revenu Fiscal de Référence)
            - tmi: float (Taux Marginal d'Imposition)
        annee_fiscale: int (2026 par défaut)

    Returns:
        ResultatFiscal avec cascade complète
    """
    type_operation = operation.get("type")
    montant_brut = operation.get("montant_brut", 0.0)

    # Import local pour éviter imports circulaires
    from .assurance_vie import calculer_fiscalite_rachat
    from .cto_ir import calculer_fiscalite_cession_cto
    from .pea import calculer_fiscalite_retrait_pea
    from .per import calculer_fiscalite_sortie_per

    if type_operation == "rachat_av":
        return calculer_fiscalite_rachat(operation, profil)
    elif type_operation == "cession_cto":
        return calculer_fiscalite_cession_cto(operation, profil)
    elif type_operation == "retrait_pea":
        return calculer_fiscalite_retrait_pea(operation, profil)
    elif type_operation == "sortie_per":
        return calculer_fiscalite_sortie_per(operation, profil)
    else:
        # Par défaut : PFU simple
        from .pfu import calculer_pfu_complet

        return calculer_pfu_complet(montant_brut, profil)
