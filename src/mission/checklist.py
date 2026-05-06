"""Définition des étapes canoniques d'une mission EC."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Etape:
    cle: str
    titre: str
    description: str
    page_streamlit: str | None
    depends_on: list[str]
    livrables: list[str]
    rdv: str | None
    obligatoire: bool
    phase: str = "Analyse"


# Étapes canoniques validées par lecture de pages/
ETAPES_CANONIQUES: list[Etape] = [
    Etape(
        cle="patrimoine_importe",
        titre="Patrimoine importé depuis PDF",
        description="Relevés PDF traités et patrimoine importé dans la mission.",
        page_streamlit="24_Import_Patrimoine.py",
        depends_on=[],
        livrables=["imports_patrimoine en mission"],
        rdv=None,
        obligatoire=False,
        phase="RDV1",
    ),
    Etape(
        cle="profil_saisi",
        titre="Profil client saisi",
        description="Le formulaire profil client est rempli et validé.",
        page_streamlit="04_Profil.py",
        depends_on=[],
        livrables=["profil_actif en session_state"],
        rdv="RDV1",
        obligatoire=True,
        phase="RDV1",
    ),
    Etape(
        cle="lettre_mission",
        titre="Lettre de mission signée",
        description="DER et lettre de mission CIF générés et signés.",
        page_streamlit=None,  # archivé — pivot EC
        depends_on=["profil_saisi"],
        livrables=["DER signé", "lettre_mission.pdf"],
        rdv="RDV1",
        obligatoire=True,
        phase="RDV1",
    ),
    Etape(
        cle="profilage_mif",
        titre="Profilage MIF II validé",
        description="Questionnaire de profilage risque complété et validé.",
        page_streamlit="03_Profilage.py",
        depends_on=["profil_saisi"],
        livrables=["score MIF II", "profil risque validé"],
        rdv="RDV1",
        obligatoire=True,
        phase="RDV1",
    ),
    Etape(
        cle="allocation_cible",
        titre="Allocation cible calculée",
        description="Allocation cible Markowitz calculée selon profil risque.",
        page_streamlit="05_Allocation.py",
        depends_on=["profilage_mif"],
        livrables=["allocation_cible en session_state"],
        rdv=None,
        obligatoire=True,
        phase="Analyse",
    ),
    Etape(
        cle="audit_patrimonial",
        titre="Audit patrimonial réalisé",
        description="Analyse du patrimoine existant et identification des opportunités.",
        page_streamlit=None,  # archivé — pivot EC
        depends_on=["profil_saisi"],
        livrables=["rapport audit patrimonial"],
        rdv=None,
        obligatoire=False,
        phase="Analyse",
    ),
    Etape(
        cle="asset_location",
        titre="Asset location optimisé",
        description="Optimisation de la localisation fiscale des actifs par enveloppe.",
        page_streamlit="07_Asset_Location.py",
        depends_on=["allocation_cible"],
        livrables=["asset_location en session_state"],
        rdv=None,
        obligatoire=True,
        phase="Analyse",
    ),
    Etape(
        cle="monte_carlo",
        titre="Projection Monte-Carlo générée",
        description="Simulation de projection patrimoniale P10/médiane/P90.",
        page_streamlit=None,  # archivé — pivot EC
        depends_on=["allocation_cible"],
        livrables=["graphique projection MC"],
        rdv=None,
        obligatoire=False,
        phase="Analyse",
    ),
    Etape(
        cle="plan_rebalancement",
        titre="Plan de rebalancement chiffré",
        description="Plan de rebalancement MILP calculé avec flux détaillés.",
        page_streamlit=None,  # archivé — pivot EC
        depends_on=["asset_location"],
        livrables=["plan_rebalancement en session_state"],
        rdv=None,
        obligatoire=True,
        phase="Analyse",
    ),
    Etape(
        cle="allocation_validee",
        titre="Allocation validée par le client",
        description="L'allocation et le plan ont été présentés et validés par le client.",
        page_streamlit="05_Allocation.py",
        depends_on=["allocation_cible", "plan_rebalancement"],
        livrables=["accord client tracé"],
        rdv="RDV2",
        obligatoire=True,
        phase="RDV2",
    ),
    Etape(
        cle="plan_execution",
        titre="Plan d'exécution validé",
        description="Ordres chiffrés, plan de déploiement et calendrier de mise en œuvre.",
        page_streamlit="22_Plan_Execution.py",
        depends_on=["allocation_validee"],
        livrables=["ordres.csv", "plan_deploiement"],
        rdv=None,
        obligatoire=True,
        phase="Livrables",
    ),
    Etape(
        cle="conformite",
        titre="Vérifications conformité",
        description="Rapport d'adéquation et vérifications CIF/MIF II.",
        page_streamlit="21_Conformite_CIF.py",
        depends_on=["allocation_validee"],
        livrables=["rapport_adequation.pdf"],
        rdv=None,
        obligatoire=True,
        phase="Livrables",
    ),
    Etape(
        cle="livrables_pdf_excel",
        titre="Livrables PDF + Excel générés",
        description="Rapport client PDF 16 pages et fichier Excel multi-onglets générés.",
        page_streamlit=None,  # archivé — pivot EC
        depends_on=["conformite", "plan_execution"],
        livrables=["rapport_client.pdf", "rapport_client.xlsx"],
        rdv=None,
        obligatoire=True,
        phase="Livrables",
    ),
    Etape(
        cle="envoi_client",
        titre="Envoi au client",
        description="Livrables transmis au client et accusé de réception obtenu.",
        page_streamlit=None,
        depends_on=["livrables_pdf_excel"],
        livrables=["email envoyé", "accusé réception"],
        rdv=None,
        obligatoire=True,
        phase="Livrables",
    ),
    Etape(
        cle="revue_3_mois",
        titre="Revue M+3 planifiée",
        description="Revue de suivi à 3 mois planifiée avec le client.",
        page_streamlit=None,
        depends_on=["envoi_client"],
        livrables=["RDV M+3 agenda"],
        rdv=None,
        obligatoire=False,
        phase="Suivi",
    ),
]

ETAPES_PAR_CLE: dict[str, Etape] = {e.cle: e for e in ETAPES_CANONIQUES}

PHASES = ["RDV1", "Analyse", "RDV2", "Livrables", "Suivi"]
