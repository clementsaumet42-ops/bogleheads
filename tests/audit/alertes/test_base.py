"""Tests for S12 alert engine — base infrastructure."""

from __future__ import annotations

from src.audit.alertes.base import _REGISTRY, Alerte, Severite, regle


def test_severite_values():
    assert Severite.ROUGE == "ROUGE"
    assert Severite.JAUNE == "JAUNE"
    assert Severite.VERT == "VERT"


def test_alerte_creation():
    a = Alerte(
        code="TEST",
        famille="Test",
        severite=Severite.ROUGE,
        titre="Test alerte",
        description="Description test",
        gain_eur_annuel=1000.0,
        gain_eur_horizon=10000.0,
        action_concrete="Faire quelque chose",
        sources=["Source A"],
    )
    assert a.code == "TEST"
    assert a.gain_eur_annuel == 1000.0
    assert a.ligne_concernee is None


def test_registry_has_40_rules():
    # Import all rule modules to ensure they're registered
    import src.audit.alertes.frais  # noqa
    import src.audit.alertes.allocation  # noqa
    import src.audit.alertes.fiscalite  # noqa
    import src.audit.alertes.configuration  # noqa
    import src.audit.alertes.liquidite  # noqa
    import src.audit.alertes.epargne_salariale  # noqa
    import src.audit.alertes.credit  # noqa
    import src.audit.alertes.transmission  # noqa
    import src.audit.alertes.hygiene  # noqa
    import src.audit.alertes.bonus  # noqa

    codes = [code for code, _, _ in _REGISTRY]
    # R1 through R40 should all be present
    for i in range(1, 41):
        assert f"R{i}" in codes, f"R{i} manquant dans le registre"


def test_regle_decorator_registers():
    initial_count = len(_REGISTRY)

    @regle("RTEST_UNIQUE", famille="Test")
    def dummy_rule(profil):
        return None

    assert len(_REGISTRY) == initial_count + 1
    _REGISTRY.pop()  # cleanup
