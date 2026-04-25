"""Tests ETF monde développé ex-USA (Livrable 3 S10)."""

from pathlib import Path

import yaml


def test_au_moins_un_etf_actions_dev_ex_usa():
    path = Path("config/univers_etf.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    etfs = data["univers_etf"]
    ex_us_etfs = [e for e in etfs if e.get("classe_actif_granulaire") == "actions_dev_ex_usa"]
    assert len(ex_us_etfs) >= 1, "Au moins 1 ETF actions_dev_ex_usa requis"


def test_ex_us_non_eligible_pea():
    path = Path("config/univers_etf.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    etfs = data["univers_etf"]
    ex_us_etfs = [e for e in etfs if e.get("classe_actif_granulaire") == "actions_dev_ex_usa"]
    for etf in ex_us_etfs:
        assert not etf.get("eligibilite", {}).get("PEA", True), (
            f"{etf['ticker']}: ETF ex-US ne devrait pas être PEA éligible"
        )
