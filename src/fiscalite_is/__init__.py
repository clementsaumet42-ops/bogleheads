"""Moteur fiscal IS — cœur du projet HoldIS Advisor.

Traite spécifiquement les enjeux fiscaux des holdings à l'IS :
- Piège mark-to-market Art. 209-0 A CGI
- Contrat de capitalisation IS comme alternative
- Tax-loss harvesting IS
- Apport-cession Art. 150-0 B ter CGI
"""

from .contrat_cap_is import *  # noqa: F401, F403
from .piege_mtm import *  # noqa: F401, F403
