"""
CTO société IS — Mark-to-Market (MTM) OPCVM
Art. 209-0 A CGI
"""

from .cascade import ResultatFiscal
from .constantes import IS_SEUIL, IS_TAUX_NORMAL, IS_TAUX_REDUIT, MTM_SEUIL_DETENTION


def detecter_piege_mtm(position: dict, regime_detenteur: str) -> dict | None:
    """
    Détecte le piège Mark-to-Market sur OPCVM détenus par une société IS.

    Art. 209-0 A CGI : Les OPCVM (dont ETF) dont > 90% de l'actif est détenu
    par des sociétés IS sont soumis à réévaluation annuelle obligatoire.
    Les plus-values latentes sont imposées chaque année, même sans cession.

    Args:
        position: dict avec
            - type_actif: str ("opcvm", "etf", "action", "obligation", etc.)
            - valeur_marche: float
            - prix_acquisition: float
            - pourcent_detention_is: float (ex: 0.95 pour 95%)
        regime_detenteur: "ir" (particulier) ou "is" (société)

    Returns:
        dict avec alerte si MTM applicable, None sinon

    Source: Art. 209-0 A CGI
    """
    if regime_detenteur != "is":
        return None

    type_actif = position.get("type_actif", "").lower()
    if type_actif not in ["opcvm", "etf", "sicav", "fcp"]:
        return None

    pourcent_detention_is = position.get("pourcent_detention_is", 0.0)
    if pourcent_detention_is <= MTM_SEUIL_DETENTION:
        return None

    # MTM applicable
    valeur_marche = position.get("valeur_marche", 0.0)
    prix_acquisition = position.get("prix_acquisition", 0.0)
    pv_latente = valeur_marche - prix_acquisition

    if pv_latente > IS_SEUIL:
        is_du = IS_SEUIL * IS_TAUX_REDUIT + (pv_latente - IS_SEUIL) * IS_TAUX_NORMAL
    else:
        is_du = pv_latente * IS_TAUX_REDUIT if pv_latente > 0 else 0.0

    return {
        "alerte": "PIÈGE MTM DÉTECTÉ",
        "type_actif": type_actif,
        "pourcent_detention_is": pourcent_detention_is,
        "valeur_marche": valeur_marche,
        "prix_acquisition": prix_acquisition,
        "pv_latente": pv_latente,
        "is_du_annuel": is_du,
        "article": "Art. 209-0 A CGI",
        "consequence": "PV latentes imposées CHAQUE ANNÉE, même sans vente",
        "solution": "Privilégier contrat de capitalisation IS (taxation forfaitaire 105% × TME)",
    }


def calculer_mtm_annuel(positions: list[dict], annee: int) -> ResultatFiscal:
    """
    Calcule l'imposition MTM annuelle pour un portefeuille CTO IS.

    Args:
        positions: liste de dict position (cf. detecter_piege_mtm)
        annee: année fiscale

    Returns:
        ResultatFiscal avec cascade MTM
    """
    resultat = ResultatFiscal(
        montant_brut=0.0,
        impot_ir=0.0,  # IS, pas IR
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    total_pv_latentes = 0.0
    total_is = 0.0
    nb_positions_mtm = 0

    for position in positions:
        alerte_mtm = detecter_piege_mtm(position, "is")
        if alerte_mtm:
            nb_positions_mtm += 1
            pv_latente = alerte_mtm["pv_latente"]
            is_position = alerte_mtm["is_du_annuel"]

            total_pv_latentes += pv_latente
            total_is += is_position

            resultat.ajouter_ligne(
                libelle=f"PV latente {position.get('nom', 'position')} (MTM)",
                montant=pv_latente,
                formule=f"{alerte_mtm['valeur_marche']:,.2f} - {alerte_mtm['prix_acquisition']:,.2f}",
                source="Art. 209-0 A CGI",
            )

    if nb_positions_mtm > 0:
        resultat.ajouter_avertissement(
            f"⚠️ {nb_positions_mtm} position(s) soumise(s) au MTM : IS sur PV latentes chaque année"
        )
        resultat.ajouter_avertissement(
            "Alternative : contrat de capitalisation IS (Art. 238 septies E CGI)"
        )

    resultat.montant_brut = total_pv_latentes
    resultat.total_impots = total_is
    resultat.montant_net = total_pv_latentes - total_is
    resultat.taux_effectif = total_is / total_pv_latentes if total_pv_latentes > 0 else 0.0

    resultat.ajouter_ligne(
        libelle="TOTAL IS (MTM annuel)",
        montant=total_is,
        formule="Somme IS sur PV latentes",
        source="Art. 209-0 A CGI",
    )

    return resultat


def comparer_cto_is_vs_contrat_cap_is(
    capital_initial: float,
    rendement_annuel: float,
    horizon_ans: int,
    tme: float = 0.030,
) -> dict:
    """
    Compare CTO IS (avec MTM) vs Contrat de capitalisation IS.

    Args:
        capital_initial: Capital initial en €
        rendement_annuel: Rendement annuel (ex: 0.06)
        horizon_ans: Horizon en années
        tme: TME (Taux Moyen des Emprunts d'État)

    Returns:
        dict avec simulation CTO IS vs contrat cap IS
    """
    from .contrat_cap_is import calculer_base_taxable_contrat_cap_is

    # CTO IS : MTM annuel
    capital_cto = capital_initial
    is_cumule_cto = 0.0

    for _annee in range(1, horizon_ans + 1):
        gain_annuel = capital_cto * rendement_annuel
        # IS sur gain annuel (MTM)
        if gain_annuel <= IS_SEUIL:
            is_annuel = gain_annuel * IS_TAUX_REDUIT
        else:
            is_annuel = IS_SEUIL * IS_TAUX_REDUIT + (gain_annuel - IS_SEUIL) * IS_TAUX_NORMAL
        is_cumule_cto += is_annuel
        capital_cto += gain_annuel - is_annuel

    # Contrat cap IS : base forfaitaire annuelle
    capital_contrat = capital_initial
    is_cumule_contrat = 0.0

    for _annee in range(1, horizon_ans + 1):
        gain_annuel = capital_contrat * rendement_annuel
        # Base taxable forfaitaire : 105% × TME × prime
        base_taxable = calculer_base_taxable_contrat_cap_is(capital_contrat, tme, {})
        if base_taxable <= IS_SEUIL:
            is_annuel = base_taxable * IS_TAUX_REDUIT
        else:
            is_annuel = IS_SEUIL * IS_TAUX_REDUIT + (base_taxable - IS_SEUIL) * IS_TAUX_NORMAL
        is_cumule_contrat += is_annuel
        capital_contrat += gain_annuel - is_annuel

    # Avantage contrat cap
    avantage = capital_contrat - capital_cto
    economie_is = is_cumule_cto - is_cumule_contrat

    return {
        "capital_initial": capital_initial,
        "rendement_annuel": rendement_annuel,
        "horizon_ans": horizon_ans,
        "tme": tme,
        "capital_final_cto_is": capital_cto,
        "is_cumule_cto_is": is_cumule_cto,
        "capital_final_contrat_cap_is": capital_contrat,
        "is_cumule_contrat_cap_is": is_cumule_contrat,
        "avantage_contrat_cap": avantage,
        "economie_is": economie_is,
        "taux_effectif_cto_is": is_cumule_cto / (capital_cto + is_cumule_cto - capital_initial),
        "taux_effectif_contrat_cap_is": is_cumule_contrat
        / (capital_contrat + is_cumule_contrat - capital_initial),
    }
