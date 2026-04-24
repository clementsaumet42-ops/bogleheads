"""
Assurance Vie (AV) — Fiscalité complexe
Art. 125-0 A CGI, Art. 990 I CGI
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .cascade import ResultatFiscal
from .constantes import (
    AV_ABATTEMENT_CELIBATAIRE,
    AV_ABATTEMENT_COUPLE,
    AV_DATE_SEUIL,
    AV_DUREE_4_ANS,
    AV_DUREE_8_ANS,
    AV_SEUIL_150K,
    AV_SEUIL_300K,
    AV_TAUX_PFL_7_5,
    TAUX_PFU_IR,
    TAUX_PS,
)
from .prelevements_sociaux import calculer_ps_av


class VersementAV(BaseModel):
    """Un versement sur un contrat d'assurance vie."""

    date: str = Field(..., description="Date du versement (YYYY-MM-DD)")
    montant: float = Field(..., description="Montant versé en €")


class RachatAV(BaseModel):
    """Un rachat sur un contrat d'assurance vie."""

    date: str = Field(..., description="Date du rachat (YYYY-MM-DD)")
    montant_brut: float = Field(..., description="Montant total du rachat en €")
    gains: float = Field(..., description="Part de plus-value dans le rachat")
    capital: float = Field(..., description="Part de capital dans le rachat")


class ContratAV(BaseModel):
    """Un contrat d'assurance vie."""

    date_ouverture: str = Field(..., description="Date d'ouverture (YYYY-MM-DD)")
    versements: list[VersementAV] = Field(default_factory=list)
    valeur_actuelle: float = Field(default=0.0, description="Valeur actuelle du contrat")
    type_fonds: str = Field(
        default="uc", description="Type de fonds : 'euro' ou 'uc' (unités de compte)"
    )
    assureur_pays: str = Field(
        default="france", description="Pays de l'assureur : 'france' ou 'luxembourg'"
    )

    def duree_detention(self, date_rachat: str | None = None) -> float:
        """Calcule la durée de détention en années."""
        if date_rachat is None:
            date_rachat = datetime.now().strftime("%Y-%m-%d")

        date_ouv = datetime.strptime(self.date_ouverture, "%Y-%m-%d")
        date_rach = datetime.strptime(date_rachat, "%Y-%m-%d")
        delta = date_rach - date_ouv
        return delta.days / 365.25

    def total_versements(self) -> float:
        """Calcule le total des versements."""
        return sum(v.montant for v in self.versements)

    def versements_avant_27_09_2017(self) -> float:
        """Calcule le montant des versements avant le 27/09/2017."""
        date_seuil = datetime.strptime(AV_DATE_SEUIL, "%Y-%m-%d")
        total = 0.0
        for v in self.versements:
            date_v = datetime.strptime(v.date, "%Y-%m-%d")
            if date_v < date_seuil:
                total += v.montant
        return total

    def versements_apres_27_09_2017(self) -> float:
        """Calcule le montant des versements après le 27/09/2017."""
        return self.total_versements() - self.versements_avant_27_09_2017()


def calculer_fiscalite_rachat(operation: dict, profil: dict) -> ResultatFiscal:
    """
    Calcule la fiscalité d'un rachat d'assurance vie.

    Règles complexes selon :
    - Durée du contrat (<4 ans, 4-8 ans, >8 ans)
    - Date des versements (avant/après 27/09/2017)
    - Montant total des contrats (seuil 150k€ célibataire / 300k€ couple)
    - Option PFU vs barème IR
    - Abattements (4600€ / 9200€)

    Args:
        operation: dict avec
            - contrat: ContratAV (Pydantic)
            - montant_brut: float (montant du rachat)
            - gains: float (part de plus-value)
            - date_rachat: str (date du rachat)
            - option_bareme: bool (option IR au barème, sinon PFU)
            - total_contrats_foyer: float (somme de tous les contrats AV du foyer)
            - abattement_deja_utilise: float (abattement déjà utilisé cette année)
        profil: dict avec situation, tmi, rfr

    Returns:
        ResultatFiscal avec cascade détaillée

    Source: Art. 125-0 A CGI, Art. 990 I CGI
    """
    # Extraction paramètres
    contrat_dict = operation.get("contrat", {})
    contrat = ContratAV(**contrat_dict) if isinstance(contrat_dict, dict) else contrat_dict

    montant_brut = operation.get("montant_brut", 0.0)
    gains = operation.get("gains", 0.0)
    date_rachat = operation.get("date_rachat", datetime.now().strftime("%Y-%m-%d"))
    option_bareme = operation.get("option_bareme", False)
    total_contrats_foyer = operation.get("total_contrats_foyer", contrat.valeur_actuelle)
    abattement_deja_utilise = operation.get("abattement_deja_utilise", 0.0)

    situation = profil.get("situation", "celibataire")
    tmi = profil.get("tmi", 0.30)

    resultat = ResultatFiscal(
        montant_brut=montant_brut,
        impot_ir=0.0,
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # Durée de détention
    duree = contrat.duree_detention(date_rachat)

    resultat.ajouter_ligne(
        libelle="Rachat assurance vie",
        montant=montant_brut,
        formule=f"Durée : {duree:.1f} ans",
        source="Art. 125-0 A CGI",
    )

    # Contrat < 4 ans : PFU 12.8% + PS (pas d'abattement)
    if duree < AV_DUREE_4_ANS:
        ir = gains * TAUX_PFU_IR
        resultat.impot_ir = ir
        resultat.ajouter_ligne(
            libelle="IR (PFU 12.8%, contrat < 4 ans)",
            montant=ir,
            formule=f"{gains:,.2f} × {TAUX_PFU_IR:.1%}",
            source="Art. 125-0 A-I-1° CGI",
        )
        resultat.ajouter_avertissement("Contrat < 4 ans : pas d'abattement, fiscalité défavorable")

    # Contrat 4-8 ans : PFU 12.8% + PS (abattement possible)
    elif duree < AV_DUREE_8_ANS:
        # Abattement
        if situation == "couple":
            abattement_annuel = AV_ABATTEMENT_COUPLE
        else:
            abattement_annuel = AV_ABATTEMENT_CELIBATAIRE

        abattement_disponible = max(0, abattement_annuel - abattement_deja_utilise)
        gains_apres_abattement = max(0, gains - abattement_disponible)
        abattement_utilise = min(gains, abattement_disponible)

        if abattement_utilise > 0:
            resultat.ajouter_ligne(
                libelle=f"Abattement AV ({situation})",
                montant=-abattement_utilise,
                formule=f"min({gains:,.2f}, {abattement_disponible:,.2f})",
                source="Art. 125-0 A-II CGI",
            )

        ir = gains_apres_abattement * TAUX_PFU_IR
        resultat.impot_ir = ir
        resultat.ajouter_ligne(
            libelle="IR (PFU 12.8%, contrat 4-8 ans)",
            montant=ir,
            formule=f"{gains_apres_abattement:,.2f} × {TAUX_PFU_IR:.1%}",
            source="Art. 125-0 A-I-1° CGI",
        )

    # Contrat > 8 ans : fiscalité complexe selon date versements et montant total
    else:
        # Abattement
        if situation == "couple":
            abattement_annuel = AV_ABATTEMENT_COUPLE
            seuil_encours = AV_SEUIL_300K
        else:
            abattement_annuel = AV_ABATTEMENT_CELIBATAIRE
            seuil_encours = AV_SEUIL_150K

        abattement_disponible = max(0, abattement_annuel - abattement_deja_utilise)
        gains_apres_abattement = max(0, gains - abattement_disponible)
        abattement_utilise = min(gains, abattement_disponible)

        if abattement_utilise > 0:
            resultat.ajouter_ligne(
                libelle=f"Abattement AV >8 ans ({situation})",
                montant=-abattement_utilise,
                formule=f"min({gains:,.2f}, {abattement_disponible:,.2f})",
                source="Art. 125-0 A-II CGI",
            )

        # Calcul prorata versements avant/après 27/09/2017
        versements_avant = contrat.versements_avant_27_09_2017()
        versements_apres = contrat.versements_apres_27_09_2017()
        total_versements = contrat.total_versements()

        if total_versements > 0:
            prorata_avant = versements_avant / total_versements
            prorata_apres = versements_apres / total_versements
        else:
            prorata_avant = 0.0
            prorata_apres = 1.0

        gains_avant = gains_apres_abattement * prorata_avant
        gains_apres = gains_apres_abattement * prorata_apres

        # Gains avant 27/09/2017 : PFL 7.5% ou option barème
        if gains_avant > 0:
            if option_bareme:
                ir_avant = gains_avant * tmi
                resultat.ajouter_ligne(
                    libelle=f"IR sur gains avant 27/09/2017 (barème, TMI {tmi:.1%})",
                    montant=ir_avant,
                    formule=f"{gains_avant:,.2f} × {tmi:.1%}",
                    source="Art. 125-0 A-I-3° CGI",
                )
            else:
                ir_avant = gains_avant * AV_TAUX_PFL_7_5
                resultat.ajouter_ligne(
                    libelle="IR sur gains avant 27/09/2017 (PFL 7.5%)",
                    montant=ir_avant,
                    formule=f"{gains_avant:,.2f} × {AV_TAUX_PFL_7_5:.1%}",
                    source="Art. 125-0 A-I-3° CGI",
                )
            resultat.impot_ir += ir_avant

        # Gains après 27/09/2017 : selon encours total
        if gains_apres > 0:
            if total_contrats_foyer > seuil_encours:
                # Au-delà du seuil : PFU 12.8%
                ir_apres = gains_apres * TAUX_PFU_IR
                resultat.ajouter_ligne(
                    libelle=f"IR sur gains après 27/09/2017 (PFU 12.8%, encours > {seuil_encours:,.0f}€)",
                    montant=ir_apres,
                    formule=f"{gains_apres:,.2f} × {TAUX_PFU_IR:.1%}",
                    source="Art. 125-0 A-I-2° CGI",
                )
                resultat.ajouter_avertissement(
                    f"Encours total > {seuil_encours:,.0f}€ : taux IR 12.8% au lieu de 7.5%"
                )
            else:
                # Sous le seuil : PFL 7.5%
                ir_apres = gains_apres * AV_TAUX_PFL_7_5
                resultat.ajouter_ligne(
                    libelle=f"IR sur gains après 27/09/2017 (PFL 7.5%, encours < {seuil_encours:,.0f}€)",
                    montant=ir_apres,
                    formule=f"{gains_apres:,.2f} × {AV_TAUX_PFL_7_5:.1%}",
                    source="Art. 125-0 A-I-2° CGI",
                )
            resultat.impot_ir += ir_apres

    # Prélèvements sociaux
    ps_result = calculer_ps_av(gains, type_fonds=contrat.type_fonds)
    resultat.prelevements_sociaux = ps_result["ps"]
    resultat.ajouter_ligne(
        libelle=f"Prélèvements sociaux ({contrat.type_fonds})",
        montant=ps_result["ps"],
        formule=f"{gains:,.2f} × {TAUX_PS:.1%}" if ps_result["ps"] > 0 else "PS déjà prélevés",
        source="Art. L.136-7 CSS",
    )

    if ps_result.get("note"):
        resultat.ajouter_avertissement(ps_result["note"])

    # AV Luxembourg : même fiscalité française
    if contrat.assureur_pays == "luxembourg":
        resultat.ajouter_avertissement(
            "Contrat AV Luxembourg : fiscalité française identique (conformité directive européenne)"
        )

    # Total
    resultat.total_impots = resultat.impot_ir + resultat.prelevements_sociaux
    resultat.montant_net = montant_brut - resultat.total_impots
    resultat.taux_effectif = resultat.total_impots / montant_brut if montant_brut > 0 else 0.0

    resultat.ajouter_ligne(
        libelle="TOTAL IMPÔTS",
        montant=resultat.total_impots,
        formule="IR + PS",
        source="",
    )
    resultat.ajouter_ligne(
        libelle="NET APRÈS IMPÔTS",
        montant=resultat.montant_net,
        formule=f"{montant_brut:,.2f} - {resultat.total_impots:,.2f}",
        source="",
    )

    return resultat
