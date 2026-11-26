from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models.investor import Fund, Investment, Investor, Startup


@pytest.fixture
def directory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.connect() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with Session(engine) as db:
        fund = Fund(name="Example Ventures")
        investor = Investor(name="Example Investor", funds=[fund])
        other = Investor(name="Other Investor")
        startup = Startup(name="Example Robotics", industry="Robotics", country="India")
        other_startup = Startup(name="Example Finance", industry="Fintech", country="UK")
        db.add_all([investor, other, startup, other_startup])
        db.flush()
        investor_id, other_id, startup_id = investor.id, other.id, startup.id
        db.add_all([
            Investment(
                investor_id=investor_id, startup=startup, stage="Seed",
                check_size=Decimal("125000.5000"), check_currency="USD",
                check_source_url="https://example.com/check",
            ),
            Investment(
                fund=fund, startup=other_startup, stage="Series A",
                round_amount=Decimal("1000000"), round_currency="GBP",
                round_source_url="https://example.com/round",
            ),
        ])
        db.commit()

    def override_database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_database
    try:
        with TestClient(app) as client:
            yield client, engine, investor_id, other_id, startup_id
    finally:
        app.dependency_overrides.pop(get_db)
        engine.dispose()


def test_investor_detail_returns_linked_portfolio_and_sourced_amounts(directory):
    client, _, investor_id, _, _ = directory
    response = client.get(f"/investors/{investor_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert [fund["name"] for fund in data["funds"]] == ["Example Ventures"]
    direct, via_fund = data["portfolio"]
    assert direct["investor_id"] == investor_id
    assert direct["startup"]["name"] == "Example Robotics"
    assert direct["check_size"] == "125000.5000"
    assert direct["check_source_url"] == "https://example.com/check"
    assert direct["round_amount"] == "unknown"
    assert via_fund["fund"] == data["funds"][0]
    assert via_fund["investor_id"] is None
    assert via_fund["check_size"] == "unknown"
    assert via_fund["round_amount"] == "1000000.0000"
    assert via_fund["round_source_url"] == "https://example.com/round"


def test_list_and_detail_portfolio_filters(directory):
    client, _, investor_id, other_id, _ = directory
    assert [row["id"] for row in client.get("/investors").json()["data"]] == [
        investor_id, other_id
    ]
    params = {"industry": "fintech", "country": "uk", "stage": "SERIES A",
              "portfolio": " example finance "}
    filtered = client.get("/investors", params=params)
    assert filtered.status_code == 200
    assert [row["id"] for row in filtered.json()["data"]] == [investor_id]
    response = client.get(f"/investors/{investor_id}", params=params)
    assert [row["startup"]["name"] for row in response.json()["data"]["portfolio"]] == [
        "Example Finance"
    ]
    assert client.get("/investors", params={"industry": "Robotics", "stage": "Series A"}).json()[
        "data"
    ] == []
    assert client.get(f"/investors/{other_id}", params=params).json()["data"]["portfolio"] == []
    assert client.get("/investors", params={"industry": " "}).status_code == 422
    assert client.get("/investors/9999").status_code == 404


@pytest.mark.parametrize("amount", ["check_size", "round_amount"])
def test_database_rejects_unsourced_amount(directory, amount):
    _, engine, investor_id, _, startup_id = directory
    with Session(engine) as db:
        db.add(Investment(investor_id=investor_id, startup_id=startup_id, **{amount: 100}))
        with pytest.raises(IntegrityError):
            db.commit()
