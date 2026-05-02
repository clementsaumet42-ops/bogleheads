"""Apport-cession Art. 150-0 B ter CGI — report d'imposition sur PV de cession.

Analyse l'éligibilité et chiffre le gain fiscal d'un schéma apport-cession
pour un dirigeant cédant les titres de sa société IS.
"""

from __future__ import annotations


def analyser_eligibilite_150_0_b_ter(
    valeur_titres: float,
    prix_revient: float,
    duree_detention_mois: int,
) -> dict:
    """Analyse l'éligibilité à l'art. 150-0 B ter. À implémenter S+2."""
    raise NotImplementedError("Sprint S+2")
