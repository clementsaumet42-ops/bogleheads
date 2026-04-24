from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChoixScenario:
    id: str
    texte: str
    score: int


@dataclass
class Scenario:
    id: str
    titre: str
    description: str
    contexte: str
    choix: list[ChoixScenario] = field(default_factory=list)


def generer_scenarios(patrimoine_eur: float | None = None) -> list[Scenario]:
    """
    Génère la liste de scénarios comportementaux.

    Parameters
    ----------
    patrimoine_eur : patrimoine du prospect (adapte les contextes chiffrés)

    Returns
    -------
    list[Scenario]
    """
    montant = int(patrimoine_eur or 100_000)

    scenarios = [
        Scenario(
            id="sc1",
            titre="Krach boursier soudain",
            description="Les marchés actions perdent 40% en 3 mois suite à une crise mondiale.",
            contexte=(
                f"Votre portefeuille passe de {montant:,} € à {int(montant * 0.6):,} €.".replace(
                    ",", " "
                )
            ),
            choix=[
                ChoixScenario("a", "Je vends tout immédiatement", -2),
                ChoixScenario("b", "Je vends une partie pour limiter les pertes", -1),
                ChoixScenario("c", "Je conserve et attends la reprise", 1),
                ChoixScenario("d", "J'achète davantage pour profiter de la baisse", 2),
            ],
        ),
        Scenario(
            id="sc2",
            titre="Forte inflation persistante",
            description="L'inflation atteint 8% par an pendant 3 ans.",
            contexte="Vos liquidités perdent 22% de leur valeur réelle.",
            choix=[
                ChoixScenario("a", "Je garde mes liquidités malgré la perte de valeur", -2),
                ChoixScenario("b", "Je déplace vers des produits à taux variable", -1),
                ChoixScenario("c", "J'investis partiellement en actifs réels", 1),
                ChoixScenario("d", "Je bascule vers des actions et matières premières", 2),
            ],
        ),
        Scenario(
            id="sc3",
            titre="Opportunité exceptionnelle",
            description="Un secteur offre des rendements potentiels de 50% avec un risque de perte de 30%.",
            contexte="Vous disposez de 20 000 € d'épargne disponible.",
            choix=[
                ChoixScenario("a", "Je n'investis pas, trop risqué", -2),
                ChoixScenario("b", "J'investis 1 000 € maximum", -1),
                ChoixScenario("c", "J'investis 5 000 € (25% de l'épargne)", 1),
                ChoixScenario("d", "J'investis 10 000 € ou plus", 2),
            ],
        ),
        Scenario(
            id="sc4",
            titre="Stagnation prolongée",
            description="Les marchés stagnent pendant 5 ans avec un rendement annuel de 0%.",
            contexte="Votre portefeuille ne croît pas et l'inflation érode sa valeur réelle.",
            choix=[
                ChoixScenario("a", "Je regrette d'avoir investi et liquide tout", -2),
                ChoixScenario("b", "Je réduis mon exposition aux actions", -1),
                ChoixScenario("c", "Je maintiens ma stratégie en attendant", 1),
                ChoixScenario("d", "Je renforce mes positions — valorisations attractives", 2),
            ],
        ),
        Scenario(
            id="sc5",
            titre="Hausse rapide des taux",
            description="Les taux d'intérêt passent de 1% à 5% en 12 mois.",
            contexte="Votre portefeuille obligataire perd 15% de sa valeur.",
            choix=[
                ChoixScenario("a", "Je liquide toutes mes obligations", -2),
                ChoixScenario("b", "Je réduis la duration de mon portefeuille", -1),
                ChoixScenario("c", "Je maintiens et attends la maturité", 1),
                ChoixScenario("d", "Je profite pour acheter des obligations à haut rendement", 2),
            ],
        ),
    ]
    return scenarios


def calculer_score_scenarios(choix_effectues: dict[str, str]) -> float:
    """
    Calcule le score moyen des scénarios.

    Parameters
    ----------
    choix_effectues : dict {scenario_id: choix_id}

    Returns
    -------
    float — score moyen entre -2 et +2
    """
    scenarios = generer_scenarios()
    scores = []
    for sc in scenarios:
        choix_id = choix_effectues.get(sc.id)
        if choix_id is None:
            continue
        for c in sc.choix:
            if c.id == choix_id:
                scores.append(c.score)
                break
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
