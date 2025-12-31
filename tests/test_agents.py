import pytest

from src.agents.finance import FinanceVarianceAgent
from src.agents.demand import DemandAgent
from src.agents.supply import SupplyAgent
from src.agents.shipments import ShipmentsAgent
from src.agents.fx import FXAgent
from src.agents.synthesis import SynthesisAgent
from src.agents.events import EventsAgent
from src.tools.data_loader import DataRepository


@pytest.fixture(scope="module")
def repo():
    return DataRepository()


def test_finance_variance_apac_supply_shock(repo):
    agent = FinanceVarianceAgent()
    res = agent.analyze(repo.finance(), month="2025-08", comparison="plan", region="APAC", product_line="Gamma")
    assert res["totals"]  # expect variance present
    assert any(tc.get("product_line") == "Gamma" for tc in res["top_contributors"])


def test_supply_signal_apac_supply_shock(repo):
    agent = SupplyAgent()
    res = agent.analyze(repo.supply(), month="2025-08", region="APAC", product_line="Gamma")
    assert res["signals"], "Expected supply signals for APAC Gamma Aug 2025"


def test_demand_signal_emea_promo(repo):
    agent = DemandAgent()
    res = agent.analyze(repo.orders(), month="2025-03", region="EMEA", bu="Growth")
    assert res["signals"], "Expected demand signals for EMEA Growth promo Mar 2025"


def test_fx_signal_nov_2025(repo):
    agent = FXAgent()
    res = agent.analyze(repo.fx(), month="2025-11", region="EMEA")
    assert res["signals"], "Expected FX signals for Nov 2025"


def test_shipments_signal_apac_supply_shock(repo):
    agent = ShipmentsAgent()
    res = agent.analyze(repo.shipments(), month="2025-08", region="APAC", product_line="Gamma")
    assert res["signals"], "Expected shipments signals for APAC Gamma Aug 2025"


def test_events_present_apac_aug(repo):
    agent = EventsAgent()
    res = agent.analyze(repo.events(), month="2025-08", region="APAC")
    assert res["events"], "Expected contextual events for APAC Aug 2025"


def test_synthesis(repo):
    finance_agent = FinanceVarianceAgent()
    demand_agent = DemandAgent()
    supply_agent = SupplyAgent()
    shipments_agent = ShipmentsAgent()
    fx_agent = FXAgent()
    events_agent = EventsAgent()
    synthesis_agent = SynthesisAgent()

    finance_res = finance_agent.analyze(repo.finance(), month="2025-08", comparison="plan", region="APAC", product_line="Gamma")
    demand_res = demand_agent.analyze(repo.orders(), month="2025-08", region="APAC", product_line="Gamma")
    supply_res = supply_agent.analyze(repo.supply(), month="2025-08", region="APAC", product_line="Gamma")
    shipments_res = shipments_agent.analyze(repo.shipments(), month="2025-08", region="APAC", product_line="Gamma")
    fx_res = fx_agent.analyze(repo.fx(), month="2025-08", region="APAC")
    events_res = events_agent.analyze(repo.events(), month="2025-08", region="APAC")

    synthesis = synthesis_agent.synthesize(finance_res, demand_res, supply_res, shipments_res, fx_res, events_res)
    assert synthesis["findings"], "Synthesis should include findings"
