from uuid import uuid4
from app.db.models import Ticket


def test_approval_filter_returns_only_authorized_state(client, db, test_customer, user_headers, admin_headers):
    ticket=Ticket(customer_id=test_customer.id,subject='Synthetic',description='Synthetic')
    db.add(ticket);db.commit()
    response=client.post('/approvals',headers=user_headers,json={'ticket_id':ticket.id,'status':'closed','idempotency_key':str(uuid4())})
    identifier=response.json()['id']
    response=client.get('/approvals?status=approved',headers=user_headers)
    assert response.json()['items']==[]
    response=client.post(f'/approvals/{identifier}/approve',headers=admin_headers)
    assert response.status_code==200
    response=client.get('/approvals?status=approved',headers=user_headers)
    assert [v['id'] for v in response.json()['items']]==[identifier]
    response=client.get('/approvals?status=arbitrary',headers=user_headers)
    assert response.status_code==422
