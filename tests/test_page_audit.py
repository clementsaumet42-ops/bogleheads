"""Tests smoke — Page 04_Audit_Patrimonial.

Vérifie que la page est syntaxiquement valide et que les helpers importés existent.
Ces tests n'exécutent PAS le corps Streamlit (ce qui nécessiterait un serveur).
"""

from __future__ import annotations


def test_page_audit_patrimonial_compile_sans_erreur():
    """La page doit être syntaxiquement correcte (compile sans lever d'exception)."""
    with open("pages/06_Audit_Patrimonial.py", encoding="utf-8") as f:
        source = f.read()

    # Compile en mode 'exec' — vérifie la syntaxe sans exécuter le corps Streamlit
    code = compile(source, "04_Audit_Patrimonial.py", "exec")
    assert code is not None


def test_page_audit_imports_helpers_ok():
    """Les modules helpers utilisés par la page doivent être importables."""
    from src.audit.adapter import contexte_depuis_profil  # noqa: F401
    from src.audit.master import ContexteAudit, RapportAudit, auditer_patrimoine  # noqa: F401
    from src.pedagogie.audit import expliquer_concept_bps, expliquer_opportunite  # noqa: F401
    from src.ui.cards import carte_kpi  # noqa: F401
    from src.ui.explications import bloc_script_restitution, expander_explication  # noqa: F401
    from src.ui.formatters import format_euro  # noqa: F401


def test_page_audit_referentiel_audit_importable():
    """Le module src.audit.master doit exporter les symboles attendus."""
    import src.audit.master as master

    assert hasattr(master, "auditer_patrimoine")
    assert hasattr(master, "ContexteAudit")
    assert hasattr(master, "RapportAudit")
    assert hasattr(master, "_LEVIERS")
    assert len(master._LEVIERS) == 5


def test_pedagogie_audit_fonctions_disponibles():
    """Le module src.pedagogie.audit doit exporter les deux fonctions requises."""
    from src.pedagogie.audit import expliquer_concept_bps, expliquer_opportunite  # noqa: F401

    explication = expliquer_concept_bps()
    assert explication.titre
    assert explication.texte_long
    assert explication.source
    assert explication.formule
