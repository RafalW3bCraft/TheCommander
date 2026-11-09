"""Real PostgreSQL judge authority and conservative cross-account budgets."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from test_accounts import invitation, personal_client
from test_workflows import app as workflow_app

from commander.connections import Connections
from commander.db import json
from commander.demo_grants import check_admission, require_dispatch
from commander.errors import DomainError
from commander.inference import complete
from commander.preferences import resolve

app = workflow_app
MODEL = "fixture-vultr-model"


def source(client, db, owner):
    assert (
        client.put("/api/connections/vultr", json={"secret": "fictional-operator-key"}).status_code
        == 200
    )
    db.one(
        "UPDATE connections SET status='validated',validated_at=now(),config=%s WHERE owner_id=%s AND kind='vultr' RETURNING kind",
        (
            json(
                {
                    "validated_model": MODEL,
                    "validated_endpoint": "https://api.vultrinference.com/v1",
                }
            ),
            owner,
        ),
    )


def grant(client, account, **changes):
    return client.post(
        "/api/admin/demo-grants",
        json={
            "owner_id": account,
            "model": MODEL,
            "expires_hours": 1,
            "prices": {MODEL: {"input_usd_per_million": 0.1, "output_usd_per_million": 0.35}},
            "max_usd": 0.005,
            "max_tokens": 1_000_000,
            "max_runs": 2,
            "aggregate_max_usd": 0.005,
            "aggregate_max_tokens": 1_000_000,
            **changes,
        },
    )


class UnknownConsumption:
    def __init__(self):
        self.calls = 0

    def completion(self, *_):
        self.calls += 1
        return {"content": "Fixture completion"}, None, 1


def test_only_judge_gets_expiring_authority_not_operator_secrets(app):
    client, _, owner, db = app
    source(client, db, owner)
    personal, personal_id = personal_client(client, invitation(client)["token"], "personal")
    judge, judge_id = personal_client(client, invitation(client, "judge")["token"], "judge")
    assert grant(client, personal_id).status_code == 409
    created = grant(client, judge_id)
    assert created.status_code == 200, created.text
    assert judge.get("/api/admin/demo-grants").status_code == 403
    assert judge.post("/api/admin/demo-grants", json={}).status_code == 403
    assert not db.one("SELECT 1 FROM connections WHERE owner_id=%s", (judge_id,))
    rows = judge.get("/api/connections").json()
    assert next(row for row in rows if row["kind"] == "vultr")["config"]["delegated"] is True
    assert "fictional-operator-key" not in judge.get("/api/connections").text
    effective = resolve(db, db.settings, judge_id)
    assert (effective.inference_provider, effective.provider_model) == ("vultr", MODEL)
    conns = Connections(db, db.settings)
    assert conns.secret(conns.get(judge_id, "vultr")) == "fictional-operator-key"
    with pytest.raises(DomainError):
        conns.get(personal_id, "vultr")
    assert client.delete("/api/admin/demo-grants/" + created.json()["id"]).status_code == 200
    with pytest.raises(DomainError):
        conns.get(judge_id, "vultr")
    with pytest.raises(DomainError):
        require_dispatch(db, judge_id)
    assert personal.get("/api/auth/me").status_code == 200


def test_unknown_usage_reserves_aggregate_usd_across_two_accounts(app):
    client, _, owner, db = app
    source(client, db, owner)
    _, first = personal_client(client, invitation(client, "judge")["token"], "judge1")
    _, second = personal_client(client, invitation(client, "judge")["token"], "judge2")
    assert grant(client, first).status_code == 200
    assert grant(client, second).status_code == 200
    provider = UnknownConsumption()

    def send(account):
        try:
            complete(
                db,
                resolve(db, db.settings, account),
                provider,
                account,
                "fictional-operator-key",
                [{"role": "user", "content": "Fictional task"}],
            )
            return 200
        except DomainError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, (first, second))) == [200, 429]
    assert provider.calls == 1
    records = db.all("SELECT * FROM usage WHERE demo_grant_id IS NOT NULL")
    assert len(records) == 1 and records[0]["cost_usd"] is None
    assert records[0]["reserved_cost_usd"] > 0
    assert grant(client, first, aggregate_max_usd=1).status_code == 409


def test_expiry_changed_key_unpriced_model_and_run_cap_fail_closed(app):
    client, _, owner, db = app
    source(client, db, owner)
    _, account = personal_client(client, invitation(client, "judge")["token"], "judge")
    created = grant(client, account)
    assert created.status_code == 200
    selected = resolve(db, db.settings, account)
    provider = UnknownConsumption()
    with pytest.raises(DomainError, match="prices"):
        complete(
            db,
            selected.model_copy(update={"provider_model": "unpriced"}),
            provider,
            account,
            "fictional",
            [],
        )
    for _ in range(2):
        db.one(
            "INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'conversation','1','Fixture') RETURNING id",
            (account,),
        )
    with pytest.raises(DomainError, match="allowance"):
        check_admission(db, account)
    db.one(
        "UPDATE demo_provider_grants SET expires_at=now()-interval '1 second' WHERE owner_id=%s RETURNING id",
        (account,),
    )
    with pytest.raises(DomainError):
        complete(db, selected, provider, account, "previously-read-secret", [])
    db.one(
        "UPDATE demo_provider_grants SET expires_at=now()+interval '1 hour' WHERE owner_id=%s RETURNING id",
        (account,),
    )
    db.one(
        "UPDATE connections SET revision=revision+1 WHERE owner_id=%s AND kind='vultr' RETURNING kind",
        (owner,),
    )
    with pytest.raises(DomainError):
        require_dispatch(db, account)
    assert provider.calls == 0
