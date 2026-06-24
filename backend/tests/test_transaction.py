import concurrent.futures

from fastapi.testclient import TestClient


def post_transaction(client: TestClient, user_id: str, amount: int, key: str):
    return client.post(
        "/transaction",
        json={"userId": user_id, "amount": amount, "idempotencyKey": key},
    )


def test_create_transaction_returns_201(client: TestClient):
    response = post_transaction(client, "alice", 100, "create-key-001")
    assert response.status_code == 201
    body = response.json()
    assert body["userId"] == "alice"
    assert body["totalPoints"] == 100
    assert body["duplicate"] is False


def test_duplicate_idempotency_key_returns_200_without_double_count(client: TestClient):
    first = post_transaction(client, "alice", 100, "dup-key-001")
    second = post_transaction(client, "alice", 100, "dup-key-001")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert first.json()["totalPoints"] == second.json()["totalPoints"] == 100


def test_invalid_user_id_returns_400(client: TestClient):
    response = post_transaction(client, "ab", 100, "invalid-user-key")
    assert response.status_code == 400


def test_invalid_amount_returns_400(client: TestClient):
    response = post_transaction(client, "alice", 0, "invalid-amount-key")
    assert response.status_code == 400


def test_summary_not_found_returns_404(client: TestClient):
    response = client.get("/summary/unknown-user")
    assert response.status_code == 404


def test_concurrent_updates_apply_all_points(client: TestClient):
    def submit(index: int):
        return post_transaction(client, "carol", 10, f"concurrent-key-{index:03d}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(submit, range(10)))

    assert all(response.status_code == 201 for response in responses)

    summary = client.get("/summary/carol").json()
    assert summary["totalPoints"] == 100
    assert summary["transactionCount"] == 10


def test_rate_limit_returns_429(client: TestClient):
    for index in range(30):
        response = post_transaction(client, "rate-user", 1, f"rate-key-{index:03d}")
        assert response.status_code == 201

    blocked = post_transaction(client, "rate-user", 1, "rate-key-blocked")
    assert blocked.status_code == 429
