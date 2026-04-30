"""Tax-loss harvesting IS — récolte des moins-values latentes en holding IS.

Optimise la récolte des moins-values pour compenser des plus-values IS
dans le respect des règles FIFO (PCG + art. 38 CGI).
"""

from __future__ import annotations


def calculer_opportunites_tlh(positions: list, seuil_pv_annuelle: float = 0.0) -> list:
    """Identifie les positions candidates au TLH. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
