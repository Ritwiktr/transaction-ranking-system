from fastapi.testclient import TestClient


def post_transaction(client: TestClient, user_id: str, amount: int, key: str):
    return client.post(
        "/transaction",
        json={"userId": user_id, "amount": amount, "idempotencyKey": key},
    )


def test_quality_user_ranks_above_spammer_with_same_total_points(client: TestClient):
    # Both users reach 200 points; quality uses fewer, larger transactions.
    for index in range(20):
        post_transaction(client, "spammer", 10, f"spam-key-{index:03d}")

    post_transaction(client, "quality", 100, "quality-key-001")
    post_transaction(client, "quality", 100, "quality-key-002")

    ranking = client.get("/ranking").json()["rankings"]
    users = {entry["userId"]: entry for entry in ranking}

    assert users["quality"]["totalPoints"] == users["spammer"]["totalPoints"] == 200
    assert users["quality"]["averageTransactionAmount"] == 100.0
    assert users["spammer"]["averageTransactionAmount"] == 10.0
    assert users["quality"]["rank"] < users["spammer"]["rank"]


def test_summary_returns_matching_rank(client: TestClient):
    post_transaction(client, "leader", 500, "leader-key-001")
    post_transaction(client, "runner", 100, "runner-key-001")

    summary = client.get("/summary/runner").json()
    ranking = client.get("/ranking").json()["rankings"]
    runner_from_ranking = next(entry for entry in ranking if entry["userId"] == "runner")

    assert summary["rank"] == runner_from_ranking["rank"] == 2


def test_ranking_respects_limit_query_param(client: TestClient):
    for index in range(5):
        post_transaction(client, f"user-{index}", 10, f"limit-key-{index:03d}")

    ranking = client.get("/ranking?limit=3").json()["rankings"]
    assert len(ranking) == 3
