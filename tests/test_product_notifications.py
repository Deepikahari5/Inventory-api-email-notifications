from app.core.exceptions import EmailDeliveryError
from app.services.email_service import email_service


def payload(**overrides):
    data = {"name": "Widget", "sku": "W-001", "price": "9.99", "stock_quantity": 3, "reorder_level": 5}
    data.update(overrides)
    return data


def test_low_stock_on_create_notifies_admin(client, outbox, admin_headers):
    response = client.post("/products", json=payload(), headers=admin_headers)
    assert response.status_code == 201
    assert len(outbox) == 1
    message = outbox[0]
    assert message["To"] == "admin@test.local"
    body = message.get_content()
    assert "Widget" in body
    assert "Current stock quantity: 3" in body
    assert "Reorder level: 5" in body


def test_sufficient_stock_sends_nothing(client, outbox, admin_headers):
    response = client.post("/products", json=payload(stock_quantity=50), headers=admin_headers)
    assert response.status_code == 201
    assert outbox == []


def test_repeated_updates_do_not_duplicate_alerts(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(), headers=admin_headers).json()["id"]
    assert len(outbox) == 1
    for quantity in (2, 1, 0):
        response = client.patch(f"/products/{product_id}", json={"stock_quantity": quantity}, headers=admin_headers)
        assert response.status_code == 200
    assert len(outbox) == 1


def test_alert_rearms_after_restock(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(), headers=admin_headers).json()["id"]
    client.patch(f"/products/{product_id}", json={"stock_quantity": 40}, headers=admin_headers)
    assert len(outbox) == 1
    client.patch(f"/products/{product_id}", json={"stock_quantity": 1}, headers=admin_headers)
    assert len(outbox) == 2


def test_alert_triggers_when_update_crosses_threshold(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(stock_quantity=30), headers=admin_headers).json()["id"]
    assert outbox == []
    client.patch(f"/products/{product_id}", json={"reorder_level": 40}, headers=admin_headers)
    assert len(outbox) == 1


def test_failed_alert_is_retried_on_next_update(client, monkeypatch, admin_headers):
    def boom(message):
        raise EmailDeliveryError("smtp unavailable")

    monkeypatch.setattr(email_service, "_deliver", boom)
    response = client.post("/products", json=payload(), headers=admin_headers)
    assert response.status_code == 201
    product_id = response.json()["id"]
    assert client.get(f"/products/{product_id}", headers=admin_headers).json()["low_stock_notified"] is False

    delivered = []
    monkeypatch.setattr(email_service, "_deliver", lambda message: delivered.append(message))
    client.patch(f"/products/{product_id}", json={"stock_quantity": 2}, headers=admin_headers)
    assert len(delivered) == 1
    assert client.get(f"/products/{product_id}", headers=admin_headers).json()["low_stock_notified"] is True

    client.patch(f"/products/{product_id}", json={"stock_quantity": 1}, headers=admin_headers)
    assert len(delivered) == 1


def test_adjust_stock_sends_inventory_event(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(stock_quantity=50), headers=admin_headers).json()["id"]
    response = client.post(
        f"/products/{product_id}/adjust-stock",
        json={"delta": -10, "reason": "damaged"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["stock_quantity"] == 40
    assert len(outbox) == 1
    body = outbox[0].get_content()
    assert "Stock adjustment" in body
    assert "Previous stock quantity: 50" in body
    assert "New stock quantity: 40" in body
    assert "damaged" in body


def test_adjust_stock_cannot_go_negative(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(stock_quantity=50), headers=admin_headers).json()["id"]
    response = client.post(f"/products/{product_id}/adjust-stock", json={"delta": -100}, headers=admin_headers)
    assert response.status_code == 400
    assert outbox == []


def test_delete_sends_inventory_event(client, outbox, admin_headers):
    product_id = client.post("/products", json=payload(stock_quantity=50), headers=admin_headers).json()["id"]
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    assert len(outbox) == 1
    assert "Product deleted" in outbox[0].get_content()


def test_employee_cannot_create_products(client, outbox, employee_headers):
    response = client.post("/products", json=payload(), headers=employee_headers)
    assert response.status_code == 403
    assert outbox == []


def test_duplicate_sku_is_rejected_without_alert(client, outbox, admin_headers):
    client.post("/products", json=payload(), headers=admin_headers)
    response = client.post("/products", json=payload(), headers=admin_headers)
    assert response.status_code == 409
    assert len(outbox) == 1


def test_low_stock_filter(client, outbox, admin_headers):
    client.post("/products", json=payload(), headers=admin_headers)
    client.post("/products", json=payload(name="Gadget", sku="G-001", stock_quantity=100), headers=admin_headers)
    response = client.get("/products?low_stock_only=true", headers=admin_headers)
    assert [item["sku"] for item in response.json()] == ["W-001"]
