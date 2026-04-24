from __future__ import annotations

REFERENCES: dict[str, dict[str, str]] = {
    "ART_L541_1_CMF": {
        "code": "Art. L.541-1 CMF",
        "texte": "Définition du conseiller en investissements financiers",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_L541_8_1_CMF": {
        "code": "Art. L.541-8-1 CMF",
        "texte": "Obligations d'information et de conseil du CIF envers ses clients",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_L222_7_CONSO": {
        "code": "Art. L.222-7 Code consommation",
        "texte": "Droit de rétractation — contrats à distance",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_325_3_RG_AMF": {
        "code": "Art. 325-3 RG AMF",
        "texte": "Connaissance du client — évaluation de l'adéquation",
        "url": "https://www.amf-france.org",
    },
    "ART_325_8_RG_AMF": {
        "code": "Art. 325-8 RG AMF",
        "texte": "Évaluation du profil de risque et adéquation des conseils",
        "url": "https://www.amf-france.org",
    },
    "ART_313_48_RG_AMF": {
        "code": "Art. 313-48 RG AMF",
        "texte": "Gestion des conflits d'intérêts",
        "url": "https://www.amf-france.org",
    },
    "ART_125_0_A_CGI": {
        "code": "Art. 125-0 A CGI",
        "texte": "Fiscalité de l'assurance-vie",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_150_0_A_CGI": {
        "code": "Art. 150-0 A CGI",
        "texte": "Impôt sur les plus-values de cessions de valeurs mobilières",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_787_B_CGI": {
        "code": "Art. 787 B CGI",
        "texte": "Exonération partielle droits de succession — pacte Dutreil",
        "url": "https://www.legifrance.gouv.fr",
    },
    "ART_990_I_CGI": {
        "code": "Art. 990 I CGI",
        "texte": "Prélèvement assurance-vie — clause bénéficiaire",
        "url": "https://www.legifrance.gouv.fr",
    },
    "MIF_II_2014_65_UE": {
        "code": "Directive MIF II 2014/65/UE",
        "texte": "Marchés d'instruments financiers — cadre réglementaire européen",
        "url": "https://eur-lex.europa.eu",
    },
    "AMF_POSITION_2019_03": {
        "code": "Position AMF 2019-03",
        "texte": "Questionnaire de connaissance client MIF II",
        "url": "https://www.amf-france.org",
    },
    "ART_17_RGPD": {
        "code": "Art. 17 RGPD",
        "texte": "Droit à l'effacement des données personnelles",
        "url": "https://eur-lex.europa.eu",
    },
}


def citer(ref_id: str) -> str:
    ref = REFERENCES.get(ref_id)
    if ref is None:
        return f"[{ref_id}]"
    return f"{ref['code']} — {ref['texte']}"
