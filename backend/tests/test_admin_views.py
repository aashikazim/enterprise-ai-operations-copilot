from app.db.models import Customer, Document, Ticket


def test_admin_views_enforce_tenant_and_role(client, db, admin_headers, user_headers, test_customer):
    other = Customer(name="Foreign", email="admin-foreign@example.com")
    db.add(other);db.flush()
    db.add_all([Document(customer_id=test_customer.id, title="Own doc", content="Private own"),
                Document(customer_id=other.id, title="Foreign doc", content="Private foreign"),
                Ticket(customer_id=test_customer.id,subject="Own ticket",description="Private own"),
                Ticket(customer_id=other.id,subject="Foreign ticket",description="Private foreign")])
    db.commit()
    for kind in ['documents','tickets','users']:
        response = client.get(f"/admin/records/{kind}")
        assert response.status_code == 401
        response = client.get(f"/admin/records/{kind}",headers=user_headers)
        assert response.status_code == 403
        response = client.get(f"/admin/records/{kind}",headers=admin_headers)
        assert response.status_code == 200
        assert "Foreign" not in response.text and "Private" not in response.text and "hashed_password" not in response.text


def test_admin_pagination_and_filters(client, db, admin_headers, test_customer):
    db.add_all([Ticket(customer_id=test_customer.id,subject=str(i),description="Synthetic",status='closed' if i else 'open') for i in range(3)])
    db.commit()
    response=client.get('/admin/records/tickets?status=closed&limit=1&offset=1',headers=admin_headers)
    assert response.status_code==200 and len(response.json()['items'])==1
    assert response.json()['items'][0]['status']=='closed'
    response=client.get('/admin/records/documents?limit=101',headers=admin_headers)
    assert response.status_code==422
