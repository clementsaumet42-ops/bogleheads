from __future__ import annotations

from src.cif.journal import JournalConseils


def test_ajouter_et_lire(tmp_path):
    j = JournalConseils(tmp_path / "test.db", "secret")
    cid = j.ajouter_conseil("C1", "test", {"data": 1})
    assert cid
    conseils = j.lire_conseils("C1")
    assert len(conseils) == 1
    assert conseils[0]["contenu"] == {"data": 1}


def test_purger(tmp_path):
    j = JournalConseils(tmp_path / "test2.db", "secret")
    j.ajouter_conseil("C2", "test", {})
    n = j.purger_client("C2")
    assert n == 1
    assert len(j) == 0
