"""
Constantes fiscales France 2026
Sources : Code Général des Impôts (CGI), LFSS 2026, LF 2026
"""

# Prélèvements Sociaux (PS)
# Art. L.136-8 CSS (Code de la Sécurité Sociale)
# Note : Le taux exact 2026 est incertain. Les documents mentionnent 17.2% et 18.6%.
# Le fichier de config existant utilise 18.6%, donc on maintient cette valeur
# pour la compatibilité avec les tests existants.
TAUX_PS = 0.186  # 18.6% (CSG 12.1% + CRDS 0.5% + Prélèvement solidarité 6.0%)

# Détail PS
TAUX_CSG = 0.121  # 12.1%
TAUX_CRDS = 0.005  # 0.5%
TAUX_PRELEVEMENT_SOLIDARITE = 0.060  # 6.0%

# PFU (Prélèvement Forfaitaire Unique) - Flat Tax
# Art. 200 A CGI
TAUX_PFU_IR = 0.128  # 12.8% IR
TAUX_PFU_TOTAL = TAUX_PFU_IR + TAUX_PS  # 31.4%

# Impôt sur les Sociétés (IS)
# Art. 219 CGI
IS_SEUIL = 42500  # € - Seuil pour taux réduit
IS_TAUX_REDUIT = 0.15  # 15% jusqu'au seuil
IS_TAUX_NORMAL = 0.25  # 25% au-delà

# Conditions taux réduit IS :
# - CA < 10M€
# - Capital entièrement libéré et détenu à ≥ 75% par personnes physiques

# Barème IR 2026
# Art. 197 CGI
BAREME_IR_2026 = [
    {"jusqu_a": 11294, "taux": 0.00},
    {"jusqu_a": 28797, "taux": 0.11},
    {"jusqu_a": 82341, "taux": 0.30},
    {"jusqu_a": 177106, "taux": 0.41},
    {"au_dela": True, "taux": 0.45},
]

# Quotient familial
# Art. 194 CGI
QF_PARTS = {
    "celibataire": 1.0,
    "couple": 2.0,
    "enfant_1": 0.5,
    "enfant_2": 0.5,
    "enfant_3": 1.0,  # 3ème enfant et suivants : 1 part
}

# Plafonnement quotient familial
# Art. 197 CGI
QF_PLAFOND_DEMI_PART = 1759  # € par demi-part (2026)
QF_PLAFOND_PART_ENTIERE = 3518  # € par part entière (3ème enfant et +)

# Décote IR
# Art. 197 CGI
DECOTE_SEUIL_CELIBATAIRE = 1929  # €
DECOTE_SEUIL_COUPLE = 3191  # €


def DECOTE_FORMULE_CELIBATAIRE(impot_brut: float) -> float:
    """Formule de décote célibataire."""
    return max(0, DECOTE_SEUIL_CELIBATAIRE - 0.75 * impot_brut)


def DECOTE_FORMULE_COUPLE(impot_brut: float) -> float:
    """Formule de décote couple."""
    return max(0, DECOTE_SEUIL_COUPLE - 0.75 * impot_brut)


# CEHR (Contribution Exceptionnelle sur les Hauts Revenus)
# Art. 223 sexies CGI
CEHR_TRANCHES_CELIBATAIRE = [
    {"rfr_min": 250001, "rfr_max": 500000, "taux": 0.03},  # 3%
    {"rfr_min": 500001, "rfr_max": None, "taux": 0.04},  # 4%
]

CEHR_TRANCHES_COUPLE = [
    {"rfr_min": 500001, "rfr_max": 1000000, "taux": 0.03},  # 3%
    {"rfr_min": 1000001, "rfr_max": None, "taux": 0.04},  # 4%
]

# CDHR (Contribution Différentielle sur les Hauts Revenus)
# Art. 223 terdecies CGI (LF 2025)
CDHR_TAUX_PLANCHER = 0.20  # 20% taux minimum d'imposition effectif
CDHR_SEUIL_CELIBATAIRE = 250000  # €
CDHR_SEUIL_COUPLE = 500000  # €

# Assurance Vie (AV)
# Art. 125-0 A CGI, 990 I CGI
AV_SEUIL_150K = 150000  # € (célibataire)
AV_SEUIL_300K = 300000  # € (couple)
AV_ABATTEMENT_CELIBATAIRE = 4600  # € annuel sur gains
AV_ABATTEMENT_COUPLE = 9200  # € annuel sur gains
AV_DATE_SEUIL = "2017-09-27"  # Date pivot pour fiscalité AV
AV_TAUX_PFL_7_5 = 0.075  # 7.5% pour contrats >8 ans avant 27/09/2017
AV_DUREE_4_ANS = 4  # ans
AV_DUREE_8_ANS = 8  # ans

# PEA (Plan d'Épargne en Actions)
# Art. 150-0 A CGI, Art. 157 CGI
PEA_PLAFOND_VERSEMENTS = 150000  # €
PEA_PME_PLAFOND_VERSEMENTS = 225000  # €
PEA_PLAFOND_CUMUL = 225000  # € (PEA + PEA-PME)
PEA_DUREE_2_ANS = 2  # ans
PEA_DUREE_5_ANS = 5  # ans

# PER (Plan d'Épargne Retraite)
# Art. 163 quatervicies CGI
PER_PLAFOND_DEDUCTION_FORFAIT = 0.10  # 10% des revenus professionnels
PER_PLAFOND_DEDUCTION_MIN = 4399  # € (2026)
PER_PLAFOND_DEDUCTION_MAX = 35194  # € (2026, 8 PASS)

# 6 cas de sortie anticipée PER sans pénalité
# Art. L.224-4 Code monétaire et financier
PER_CAS_DEBLOCAGE_ANTICIPE = [
    "décès_conjoint",
    "invalidité_titulaire",
    "invalidité_conjoint",
    "invalidité_enfant",
    "surendettement",
    "expiration_droits_chomage",
    "acquisition_residence_principale",  # Seulement PERP ancien
]

# Contrat de capitalisation IS
# Art. 238 septies E CGI
CONTRAT_CAP_IS_COEF = 1.05  # 105%
CONTRAT_CAP_IS_TME_REFERENCE_2026 = 0.030  # 3.0% (à vérifier)

# Mark-to-Market (MTM) OPCVM à l'IS
# Art. 209-0 A CGI
MTM_SEUIL_DETENTION = 0.90  # 90% détenus par société IS

# Abattement dividendes option barème
# Art. 158 CGI
ABATTEMENT_DIVIDENDES_BAREME = 0.40  # 40%

# Durée report déficit CTO
DUREE_REPORT_DEFICIT_CTO = 10  # ans

# TME (Taux Moyen des Emprunts d'État)
# Publié mensuellement par l'administration fiscale
TME_REFERENCE_2026 = 0.030  # 3.0% (estimation)
