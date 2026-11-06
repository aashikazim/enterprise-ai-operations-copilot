from app.db.models import Customer, Document, DocumentChunk


def test_source_preview_checks_document_and_chunk_tenant(client, db, user_headers, test_customer):
    other = Customer(name="Foreign", email="source-foreign@example.com")
    db.add(other); db.flush()
    document = Document(customer_id=test_customer.id, title="Synthetic source", content="Synthetic")
    db.add(document); db.flush()
    chunk = DocumentChunk(customer_id=test_customer.id, document_id=document.id,
                          chunk_index=0, content="Synthetic evidence", embedding=[1.] + [0.] * 383)
    db.add(chunk); db.commit()
    path = f"/knowledge/documents/{document.id}/chunks/0"
    response = client.get(path, headers=user_headers)
    assert response.status_code == 200 and response.json()["content"] == "Synthetic evidence"
    chunk.customer_id = other.id; db.commit()
    response = client.get(path, headers=user_headers)
    assert response.status_code == 404
    response = client.get(path)
    assert response.status_code == 401
