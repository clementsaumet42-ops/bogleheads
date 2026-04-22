# -*- coding: utf-8 -*-
"""
Module de location d'actifs (asset location) — optimisation fiscale.
Détermine quelle enveloppe utiliser en priorité pour chaque classe d'actifs,
selon les règles fiscales françaises et l'approche Bogleheads.

Structure prête pour intégration future de cvxpy (optimisation sous contraintes).
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Règles de priorité par classe d'actifs
# ---------------------------------------------------------------------------

# Dictionnaire de règles : classe_actifs → liste ordonnée d'IDs enveloppes
# Règle générale Bogleheads :
# - Actifs peu efficaces fiscalement (obligations, dividendes élevés) → enveloppes privilégiées
# - Actions de croissance (capitalisantes, faibles dividendes) → PEA puis CTO
# - Produits retraite → PER si TMI élevée

REGLES_PRIORITE: dict[str, list[str]] = {
    # Obligations d'État — fortement fiscalisées en CTO → à loger dans enveloppe
    "Obligations État Zone Euro": ["contrat_capi_is", "per", "pea", "cto_perso", "cto_is"],
    "Obligations État USA": ["contrat_capi_is", "per", "cto_perso", "cto_is"],
    "Obligations État Monde": ["contrat_capi_is", "per", "cto_perso", "cto_is"],

    # Obligations crédit — coupons imposables en CTO
    "Obligations Crédit IG Zone Euro": ["contrat_capi_is", "per", "cto_perso"],
    "Obligations Haut Rendement Zone Euro": ["contrat_capi_is", "per", "cto_perso"],

    # Actions Monde — priorité PEA (synthétique) pour exonération IR après 5 ans
    "Actions Monde": ["pea", "per", "cto_perso", "cto_is"],
    "Actions Monde (All-World)": ["pea", "per", "cto_perso", "cto_is"],
    "Actions Monde Small Cap": ["per", "cto_perso"],

    # Actions USA — PEA si synthétique disponible (SP5, EWLD)
    "Actions USA": ["pea", "per", "cto_perso", "cto_is"],

    # Actions Europe — PEA privilégié (éligibilité directe)
    "Actions Europe": ["pea", "per", "cto_perso"],
    "Actions Zone Euro (Large Cap)": ["pea", "per", "cto_perso"],
    "Actions France": ["pea", "per", "cto_perso"],
    "Actions Europe (ex-Controversées)": ["pea", "per", "cto_perso"],

    # Actions Émergents — PEA si disponible (PAEEM), sinon PER ou CTO
    "Actions Émergents": ["pea", "per", "cto_perso", "cto_is"],
    "Actions Émergents (IMI)": ["per", "cto_perso"],

    # Actions sociétés minières — CTO (hors champ PEA généralement)
    "Actions Sociétés Minières Or": ["per", "cto_perso"],

    # Or physique (ETC) — CTO uniquement (ETC physique non éligible PEA/PER généralement)
    "Or physique": ["cto_perso"],

    # Fallback générique
    "_defaut": ["pea", "per", "cto_perso", "contrat_capi_is", "cto_is"],
}

# Règles spéciales pour les ETFs distribuants
# Un ETF distribuant génère des dividendes annuels → préférer enveloppes capitalisantes
PENALITE_DISTRIBUANT: dict[str, int] = {
    # Descendre ces enveloppes de N rangs si l'ETF est distribuant
    "cto_perso": 2,    # Les dividendes sont fiscalisés chaque année en CTO
    "cto_is": 2,
}


@dataclass
class RecommandationLocation:
    """Résultat d'une recommandation de location d'actifs.

    Attributes:
        classe_actifs: Classe d'actifs concernée.
        ticker: Ticker de l'ETF.
        nom_etf: Nom complet de l'ETF.
        priorites: Liste ordonnée d'IDs d'enveloppes (meilleure en premier).
        enveloppe_recommandee: ID de l'enveloppe recommandée.
        raison: Explication de la recommandation.
    """

    classe_actifs: str
    ticker: str
    nom_etf: str
    priorites: list[str]
    enveloppe_recommandee: str
    raison: str


class AssetLocator:
    """Moteur de recommandation de location d'actifs.

    Détermine quelle enveloppe utiliser pour chaque ETF selon des règles
    fiscales prédéfinies. La structure est prête pour une intégration future
    d'un solveur d'optimisation (ex: cvxpy) sous contraintes de plafonds.

    Utilisation future avec cvxpy :
    ```python
    # TODO: Intégrer cvxpy pour optimisation sous contraintes :
    # - Plafond PEA 150 000 €
    # - Plafond PEA-PME 225 000 €
    # - Contraintes d'éligibilité
    # - Minimiser l'impôt total à horizon N ans
    import cvxpy as cp
    x = cp.Variable((n_etfs, n_enveloppes), boolean=True)
    # Objectif : minimiser somme(impôts estimés)
    # Contraintes : x[i,j] = 0 si ETF i non éligible dans enveloppe j
    ```
    """

    def __init__(self, enveloppes_disponibles: list[str] | None = None):
        """Initialise le localisateur d'actifs.

        Args:
            enveloppes_disponibles: Liste des IDs d'enveloppes disponibles pour
                                    ce client. Si None, toutes les enveloppes sont
                                    considérées disponibles.
        """
        self.enveloppes_disponibles = enveloppes_disponibles or list(
            set(id_env for ids in REGLES_PRIORITE.values() for id_env in ids)
        )
        self.regles = REGLES_PRIORITE.copy()

    def get_priorites_enveloppes(
        self,
        classe_actifs: str,
        enveloppes: list[str] | None = None,
        type_etf: str = "capitalisant",
    ) -> list[str]:
        """Retourne la liste ordonnée d'enveloppes pour une classe d'actifs.

        Args:
            classe_actifs: Classe d'actifs (ex: 'Actions Monde', 'Obligations État Zone Euro').
            enveloppes: Sous-ensemble d'enveloppes à considérer. Si None, utilise
                        les enveloppes disponibles de l'instance.
            type_etf: 'capitalisant' ou 'distribuant' — influence les priorités.

        Returns:
            Liste ordonnée d'IDs d'enveloppes, de la plus recommandée à la moins.
        """
        enveloppes_cible = enveloppes or self.enveloppes_disponibles

        # Récupération des règles de base
        priorites_brutes = self.regles.get(classe_actifs, self.regles.get("_defaut", []))

        # Filtrage sur les enveloppes disponibles
        priorites_filtrees = [env for env in priorites_brutes if env in enveloppes_cible]

        # Ajout des enveloppes non listées dans les règles mais disponibles
        for env in enveloppes_cible:
            if env not in priorites_filtrees:
                priorites_filtrees.append(env)

        # Pénalité pour les ETFs distribuants
        if type_etf == "distribuant":
            priorites_filtrees = self._appliquer_penalite_distribuant(priorites_filtrees)

        return priorites_filtrees

    def _appliquer_penalite_distribuant(self, priorites: list[str]) -> list[str]:
        """Déplace les enveloppes pénalisées pour les ETFs distribuants.

        Les ETFs distribuants génèrent des dividendes imposables chaque année
        en CTO — ils sont moins efficaces fiscalement dans cette enveloppe.

        Args:
            priorites: Liste de priorités initiale.

        Returns:
            Liste réordonnée tenant compte de la pénalité distribuant.
        """
        # Applique les pénalités par permutation
        result = list(priorites)
        for env, decalage in PENALITE_DISTRIBUANT.items():
            if env in result:
                idx = result.index(env)
                # Déplace l'enveloppe vers la fin de la liste
                result.pop(idx)
                nouvelle_pos = min(idx + decalage, len(result))
                result.insert(nouvelle_pos, env)
        return result

    def recommander_pour_etf(
        self,
        etf: dict,
        enveloppes: list[str] | None = None,
    ) -> RecommandationLocation:
        """Génère une recommandation de location pour un ETF donné.

        Args:
            etf: Dictionnaire décrivant l'ETF (issu du YAML univers_etf.yaml).
            enveloppes: Enveloppes à considérer.

        Returns:
            RecommandationLocation avec la recommandation et son explication.
        """
        classe = etf.get("classe_actifs", "_defaut")
        ticker = etf.get("ticker", "?")
        nom = etf.get("nom", ticker)
        type_etf = etf.get("type", "capitalisant")

        # Vérification des éligibilités déclarées dans le YAML
        eligibilite = etf.get("eligibilite", {})
        enveloppes_eligibles = [
            env_id
            for env_id, eligible in eligibilite.items()
            if eligible
        ]

        # Si des éligibilités sont déclarées, on restreint au sous-ensemble éligible
        enveloppes_filtrees = enveloppes or self.enveloppes_disponibles
        if enveloppes_eligibles:
            enveloppes_filtrees = [
                e for e in enveloppes_filtrees if e in enveloppes_eligibles
            ]
            # Si aucune enveloppe éligible disponible, on garde toutes (fallback)
            if not enveloppes_filtrees:
                enveloppes_filtrees = enveloppes or self.enveloppes_disponibles

        priorites = self.get_priorites_enveloppes(classe, enveloppes_filtrees, type_etf)

        enveloppe_rec = priorites[0] if priorites else "cto_perso"

        raison = self._generer_raison(classe, enveloppe_rec, type_etf)

        return RecommandationLocation(
            classe_actifs=classe,
            ticker=ticker,
            nom_etf=nom,
            priorites=priorites,
            enveloppe_recommandee=enveloppe_rec,
            raison=raison,
        )

    def _generer_raison(
        self,
        classe_actifs: str,
        enveloppe_id: str,
        type_etf: str,
    ) -> str:
        """Génère une explication textuelle de la recommandation.

        Args:
            classe_actifs: Classe d'actifs.
            enveloppe_id: ID de l'enveloppe recommandée.
            type_etf: Type de l'ETF.

        Returns:
            Texte explicatif en français.
        """
        raisons = {
            "pea": "PEA recommandé : exonération IR après 5 ans, capitalisation optimale",
            "per": "PER recommandé : déduction à l'entrée si TMI élevée, report fiscal",
            "contrat_capi_is": "Contrat capitalisation IS recommandé : évite mark-to-market art. 209-0 A",
            "cto_perso": "CTO personnel : flexibilité maximale, fiscalité standard PFU 31.4 %",
            "cto_is": "CTO IS : à éviter pour OPCVM (piège mark-to-market annuel)",
            "pee": "PEE : si disponible avec abondement employeur, exonération IR PV",
        }

        base = raisons.get(enveloppe_id, f"Enveloppe {enveloppe_id}")

        if type_etf == "distribuant":
            base += " — Note : ETF distribuant, dividendes fiscalisés annuellement hors enveloppes"

        if "Obligations" in classe_actifs:
            base += " — Obligations : coupons peu efficaces en CTO, préférer enveloppe"

        return base

    def generer_matrice_location(
        self,
        etfs: list[dict],
        enveloppes: list[str] | None = None,
    ) -> list[dict]:
        """Génère la matrice complète de location pour tous les ETFs.

        Args:
            etfs: Liste de dictionnaires ETF (depuis univers_etf.yaml).
            enveloppes: Enveloppes à considérer.

        Returns:
            Liste de recommandations triées par ticker.
        """
        recommandations = []
        for etf in etfs:
            rec = self.recommander_pour_etf(etf, enveloppes)
            recommandations.append({
                "ticker": rec.ticker,
                "nom_etf": rec.nom_etf,
                "classe_actifs": rec.classe_actifs,
                "enveloppe_recommandee": rec.enveloppe_recommandee,
                "priorites": rec.priorites,
                "raison": rec.raison,
            })
        return sorted(recommandations, key=lambda x: x["ticker"])
