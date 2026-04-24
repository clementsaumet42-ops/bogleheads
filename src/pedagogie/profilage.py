"""Explications pédagogiques pour le profilage par 3 prismes."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_convergence_3_prismes(
    profil_consolide: dict,
) -> Explication:
    """Retourne l'explication pédagogique de la convergence des 3 prismes de profilage.

    Args:
        profil_consolide: Dictionnaire décrivant le profil consolidé avec au moins :
                          - profil_final (str)
                          - profil_declare (str, optionnel)
                          - profil_grable_lytton (str, optionnel)
                          - profil_scenarios (str, optionnel)
                          - convergent (bool, optionnel)

    Returns:
        Une Explication décrivant la méthode de convergence et le profil retenu.
    """
    profil_final = profil_consolide.get("profil_final", "équilibré")
    profil_declare = profil_consolide.get("profil_declare", profil_final)
    profil_gl = profil_consolide.get("profil_grable_lytton", profil_final)
    profil_scenarios = profil_consolide.get("profil_scenarios", profil_final)
    convergent = profil_consolide.get("convergent", True)

    prismes = [
        f"déclaratif ({profil_declare})",
        f"Grable-Lytton ({profil_gl})",
        f"scénarios ({profil_scenarios})",
    ]
    prismes_str = ", ".join(prismes)

    if convergent:
        texte_court = (
            f"Les 3 prismes convergent sur le profil « {profil_final} » : "
            f"{prismes_str}. Profil fiable — faible risque de dissonance comportementale."
        )
        texte_long = (
            f"Le profilage par 3 prismes est conforme à la recommandation AMF "
            f"(Position-recommandation 2019-03) et à la directive MIF II (Art. 54-55 RD 2017/565). "
            f"Les trois angles convergent sur « {profil_final} » : "
            f"(1) Profil déclaratif : {profil_declare} — ressenti subjectif du client. "
            f"(2) Questionnaire Grable-Lytton (α=0,77) : {profil_gl} — mesure psychométrique validée. "
            f"(3) Scénarios de perte concrets : {profil_scenarios} — réaction comportementale. "
            f"La convergence des trois prismes renforce la fiabilité du profil retenu "
            f"et réduit le risque de portefeuille non adapté (unsuitability risk)."
        )
        alt = None
    else:
        # Divergence — on cale sur le plus prudent
        profil_retenu = profil_final
        texte_court = (
            f"Divergence détectée entre les 3 prismes ({prismes_str}). "
            f"Profil calé sur « {profil_retenu} » (le plus prudent) pour éviter la panique "
            "en cas de crise."
        )
        texte_long = (
            f"Les trois prismes de profilage divergent : {prismes_str}. "
            f"En cas de divergence, la déontologie CIF impose de retenir le profil le plus "
            f"prudent (principe de précaution AMF). "
            f"Le profil final retenu est « {profil_retenu} ». "
            "La divergence la plus risquée est la sur-déclaration du risque (client se dit "
            "dynamique mais réagirait comme un défensif en cas de krach −40 %). "
            "Ce gap comportemental est documenté par Kahneman & Tversky (1979) — "
            "la théorie des perspectives montre que la douleur d'une perte est 2× "
            "plus forte que le plaisir d'un gain équivalent."
        )
        alt = (
            f"Profil déclaratif « {profil_declare} » écarté comme profil principal : "
            "trop optimiste vs comportement observé sur les scénarios de perte. "
            "Conservé comme contexte pour la communication client."
        )

    return Explication(
        section="profilage.convergence_3_prismes",
        titre=f"Pourquoi le profil « {profil_final} » ?",
        texte_court=texte_court,
        texte_long=texte_long,
        source=(
            "Grable, J. E., & Lytton, R. H. (1999). Financial risk tolerance revisited: "
            "The development of a risk assessment instrument. "
            "Financial Services Review, 8(3), 163-181. "
            "AMF Position-recommandation 2019-03. "
            "Art. 54-55 Règlement délégué (UE) 2017/565 (MIF II). "
            "Kahneman, D. & Tversky, A. (1979). Prospect Theory. Econometrica, 47(2), 263-291."
        ),
        alternative_ecartee=alt,
        variables_contexte={
            "profil_final": profil_final,
            "profil_declare": profil_declare,
            "profil_grable_lytton": profil_gl,
            "profil_scenarios": profil_scenarios,
        },
    )


def expliquer_prismes_detail(
    profil_consolide: dict,
) -> list[Explication]:
    """Retourne le détail des 3 prismes de profilage comme une liste d'Explications.

    Args:
        profil_consolide: Même structure que expliquer_convergence_3_prismes.

    Returns:
        Liste de 3 Explication (une par prisme).
    """
    profil_final = profil_consolide.get("profil_final", "équilibré")
    profil_declare = profil_consolide.get("profil_declare", profil_final)
    profil_gl = profil_consolide.get("profil_grable_lytton", profil_final)
    profil_scenarios = profil_consolide.get("profil_scenarios", profil_final)

    return [
        Explication(
            section="profilage.prisme_declaratif",
            titre="Prisme 1 : profil déclaratif",
            texte_court=(
                f"Profil déclaré : « {profil_declare} ». "
                "Ressenti subjectif — nécessaire mais insuffisant seul."
            ),
            texte_long=(
                f"Le profil déclaratif (« {profil_declare} ») est le ressenti que le client "
                "exprime spontanément face au risque. C'est le point de départ de la "
                "conversation, mais il peut être biaisé par l'humeur du moment, "
                "le contexte de marché récent (biais de récence) ou la sur-confiance. "
                "Il doit être croisé avec des mesures plus objectives (Grable-Lytton, scénarios)."
            ),
            source="AMF Position-recommandation 2019-03. Art. 25 MIF II (directive 2014/65/UE).",
        ),
        Explication(
            section="profilage.prisme_grable_lytton",
            titre="Prisme 2 : questionnaire Grable-Lytton (scientifique)",
            texte_court=(
                f"Score Grable-Lytton → profil « {profil_gl} ». "
                "Instrument psychométrique validé (α=0,77, fiabilité test-retest élevée)."
            ),
            texte_long=(
                f"Le questionnaire Grable & Lytton (1999) est composé de 13 questions "
                f"avec scores 1-4, validé scientifiquement (alpha de Cronbach = 0,77). "
                f"Il mesure la tolérance financière au risque sur 5 dimensions : "
                "investissement spéculatif, gestion des liquidités, horizons d'investissement, "
                "gestion des dépenses, et comportement face aux pertes. "
                f"Score obtenu → profil « {profil_gl} ». "
                "C'est l'instrument le plus cité dans la littérature académique francophone "
                "de conseil en gestion de patrimoine."
            ),
            source=(
                "Grable, J. E., & Lytton, R. H. (1999). Financial risk tolerance revisited. "
                "Financial Services Review, 8(3), 163-181."
            ),
        ),
        Explication(
            section="profilage.prisme_scenarios",
            titre="Prisme 3 : scénarios concrets de perte",
            texte_court=(
                f"Réaction aux scénarios → profil « {profil_scenarios} ». "
                "Test comportemental : 'que feriez-vous si votre portefeuille perdait −30 % ?"
            ),
            texte_long=(
                f"Les scénarios de perte concrets testent le comportement réel face à la "
                f"volatilité : −10 %, −20 %, −30 %, −40 % de portefeuille. "
                f"La réaction déclarée (vendre / conserver / acheter davantage) révèle "
                f"le profil comportemental réel, souvent différent du profil déclaratif. "
                f"Score scénarios → profil « {profil_scenarios} ». "
                "Ce prisme est particulièrement utile pour détecter les investisseurs qui "
                "surestiment leur tolérance au risque (overconfidence bias, Barber & Odean 2001)."
            ),
            source=(
                "Barber, B. & Odean, T. (2001). Boys will be Boys. "
                "Quarterly Journal of Economics, 116(1), 261-292. "
                "Kahneman, D. & Tversky, A. (1979). Prospect Theory. "
                "Econometrica, 47(2), 263-291."
            ),
        ),
    ]
