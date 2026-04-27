"""Sprint S15 Lot D — Calendrier de mise en œuvre.

Génère un calendrier Gantt des étapes de mise en œuvre basé sur
le plan de déploiement.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Literal

logger = logging.getLogger(__name__)

TypeEtape = Literal["admin", "virement", "ordre", "controle"]

# Durées types par type d'étape (en jours ouvrés)
_DUREES_ETAPES: dict[str, int] = {
    "admin": 14,  # ouverture de compte (2 semaines)
    "virement": 3,  # virement bancaire (3 jours)
    "ordre": 1,  # passage d'ordre (1 jour)
    "controle": 1,  # contrôle exécution (1 jour)
}

# Délai entre étapes en jours calendaires
_DELAI_POST_ADMIN = 2  # 2 jours après ouverture avant premier virement
_DELAI_POST_VIREMENT = 1  # 1 jour après virement avant de passer ordres


def _date_plus_jours(d: date, jours: int) -> date:
    """Ajoute des jours calendaires à une date."""
    return d + timedelta(days=jours)


def _date_fin(date_debut: date, type_etape: str) -> date:
    """Calcule la date de fin selon le type d'étape."""
    duree = _DUREES_ETAPES.get(type_etape, 1)
    return _date_plus_jours(date_debut, duree - 1)


def generer_calendrier(
    plan_deploiement: dict,
    date_debut: date,
) -> list[dict]:
    """
    Génère le calendrier de mise en œuvre à partir du plan de déploiement.

    Parameters
    ----------
    plan_deploiement : dict
        Résultat de deploiement.plan_deploiement().
    date_debut : date
        Date de démarrage de la mise en œuvre.

    Returns
    -------
    list[dict]
        Liste d'étapes triées par date, chacune contenant :
        - ordre : int (numéro de séquence)
        - date_debut : date
        - date_fin : date
        - titre : str
        - description : str
        - enveloppe : str | None
        - type : TypeEtape
        - depends_on : list[int]
    """
    mode: str = plan_deploiement.get("mode", "lump_sum")
    duree_mois: int = plan_deploiement.get("duree_mois", 0)
    sequence: list[str] = plan_deploiement.get("sequence_enveloppes", [])
    tranches: list[dict] = plan_deploiement.get("tranches", [])

    etapes: list[dict] = []
    ordre = 1

    # ── Étape 1 : Ouverture des comptes ───────────────────────────────────────
    if sequence:
        brokers_ouvrir = _deduire_brokers(sequence)
        for broker_desc in brokers_ouvrir:
            etape_admin: dict = {
                "ordre": ordre,
                "date_debut": date_debut,
                "date_fin": _date_fin(date_debut, "admin"),
                "titre": f"Ouvrir compte {broker_desc}",
                "description": (
                    "Démarches d'ouverture : KYC, pièces justificatives, signature CGU. "
                    "Délai moyen 5–10 jours ouvrés selon le broker."
                ),
                "enveloppe": broker_desc,
                "type": "admin",
                "depends_on": [],
            }
            etapes.append(etape_admin)
            ordre += 1

    # Date après ouverture de tous les comptes
    if etapes:
        date_apres_admin = _date_plus_jours(max(e["date_fin"] for e in etapes), _DELAI_POST_ADMIN)
    else:
        date_apres_admin = date_debut

    # ── Étape 2+ : Virements et ordres par tranche ────────────────────────────
    # Regrouper les tranches par mois
    mois_uniques = sorted({t["mois"] for t in tranches})

    # IDs des étapes admin pour les dépendances
    ids_admin = [e["ordre"] for e in etapes if e["type"] == "admin"]

    prev_ordre_ids_par_env: dict[str, list[int]] = {}

    for mois_idx, mois in enumerate(mois_uniques):
        # Date de ce mois (date_debut + N mois calendaires environ)
        date_mois = date_apres_admin if mois == 0 else _date_plus_jours(date_apres_admin, mois * 30)

        tranches_mois = [t for t in tranches if t["mois"] == mois]
        enveloppes_mois = list({t["enveloppe"] for t in tranches_mois})

        for env in enveloppes_mois:
            montant_mois = sum(t["montant_eur"] for t in tranches_mois if t["enveloppe"] == env)

            # Dépendances du virement
            deps_virement = list(ids_admin)
            if env in prev_ordre_ids_par_env:
                deps_virement.extend(prev_ordre_ids_par_env[env])

            # Étape virement
            etape_virement: dict = {
                "ordre": ordre,
                "date_debut": date_mois,
                "date_fin": _date_fin(date_mois, "virement"),
                "titre": (
                    f"Virement {env} — tranche {mois_idx + 1}"
                    if mode in ("DCA", "hybride")
                    else f"Virement initial {env}"
                ),
                "description": (
                    f"Virement de {montant_mois:,.0f} € vers {env}. "
                    f"Délai de réception : 1–3 jours ouvrés."
                ),
                "enveloppe": env,
                "type": "virement",
                "depends_on": deps_virement,
            }
            etapes.append(etape_virement)
            id_virement = ordre
            ordre += 1

            # Étape ordre
            date_ordre = _date_plus_jours(etape_virement["date_fin"], _DELAI_POST_VIREMENT)
            etape_ordre: dict = {
                "ordre": ordre,
                "date_debut": date_ordre,
                "date_fin": _date_fin(date_ordre, "ordre"),
                "titre": (
                    f"Ordres {env} — tranche {mois_idx + 1}"
                    if mode in ("DCA", "hybride")
                    else f"Ordres {env}"
                ),
                "description": (
                    f"Passer les ordres d'achat ETF sur {env} ({montant_mois:,.0f} €). "
                    f"Ordres limités à ±2% du prix de référence."
                ),
                "enveloppe": env,
                "type": "ordre",
                "depends_on": [id_virement],
            }
            etapes.append(etape_ordre)
            id_ordre = ordre
            prev_ordre_ids_par_env[env] = [id_ordre]
            ordre += 1

        # ── Étape contrôle après chaque tranche ───────────────────────────────
        ids_ordres_mois = [
            e["ordre"]
            for e in etapes
            if e["type"] == "ordre"
            and e.get("enveloppe") in enveloppes_mois
            and e["ordre"] > (max(ids_admin) if ids_admin else 0)
        ]
        # Prendre les ordres du mois courant seulement
        ids_ordres_mois_courant = ids_ordres_mois[-(len(enveloppes_mois)) :]

        if ids_ordres_mois_courant:
            date_controle = _date_plus_jours(
                max(e["date_fin"] for e in etapes if e["ordre"] in ids_ordres_mois_courant), 2
            )
            libelle = (
                f"Contrôle exécution tranche {mois_idx + 1}"
                if mode in ("DCA", "hybride")
                else "Contrôle exécution + reporting initial"
            )
            etape_controle: dict = {
                "ordre": ordre,
                "date_debut": date_controle,
                "date_fin": _date_fin(date_controle, "controle"),
                "titre": libelle,
                "description": (
                    "Vérifier l'exécution des ordres, contrôler les prix moyens obtenus, "
                    "mettre à jour le tableau de suivi."
                ),
                "enveloppe": None,
                "type": "controle",
                "depends_on": ids_ordres_mois_courant,
            }
            etapes.append(etape_controle)
            ordre += 1

    # ── Revue intermédiaire à M+6 (si DCA ou hybride) ─────────────────────────
    if mode in ("DCA", "hybride") and duree_mois >= 6:
        date_revue = _date_plus_jours(date_apres_admin, 6 * 30)
        etapes.append(
            {
                "ordre": ordre,
                "date_debut": date_revue,
                "date_fin": _date_fin(date_revue, "controle"),
                "titre": "Revue intermédiaire M+6",
                "description": (
                    "Point d'étape : vérifier l'allocation réalisée vs cible, "
                    "ajuster si nécessaire, préparer la suite du déploiement."
                ),
                "enveloppe": None,
                "type": "controle",
                "depends_on": [],
            }
        )
        ordre += 1

    # ── Rebalancing annuel à M+12 ──────────────────────────────────────────────
    date_rebal = _date_plus_jours(date_debut, 365)
    etapes.append(
        {
            "ordre": ordre,
            "date_debut": date_rebal,
            "date_fin": _date_fin(date_rebal, "controle"),
            "titre": "Rebalancing annuel M+12",
            "description": (
                "Rebalancement du portefeuille : vendre les sur-pondérés, "
                "acheter les sous-pondérés pour revenir à l'allocation cible."
            ),
            "enveloppe": None,
            "type": "controle",
            "depends_on": [],
        }
    )

    return etapes


def _deduire_brokers(sequence: list[str]) -> list[str]:
    """Déduit les brokers à ouvrir depuis la séquence d'enveloppes."""
    brokers: list[str] = []
    for env in sequence:
        env_up = env.upper()
        if env_up == "PEA":
            brokers.append("PEA (broker à choisir)")
        elif env_up == "CTO":
            brokers.append("CTO (broker à choisir)")
        elif env_up == "AV":
            brokers.append("Contrat AV (assureur à choisir)")
        elif env_up == "PER":
            brokers.append("PER (teneur à choisir)")
        else:
            brokers.append(env)
    return brokers
