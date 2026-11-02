from sqlalchemy import select
from app.db.models import AuditEvent,CommunityFeedback


def test_reference_labels_reject_blanks_and_nulls(client):
    assert client.post('/api/v1/grievance-categories',json={'label_en':'  ','label_rw':'test'}).status_code==422
    created=client.post('/api/v1/grievance-categories',json={'label_en':'Water fee','label_rw':'Amafaranga y’amazi'}).json()
    assert client.patch(f'/api/v1/grievance-categories/{created["id"]}',json={'label_en':None}).status_code==422
    assert client.patch(f'/api/v1/grievance-categories/{created["id"]}',json={'is_active':None}).status_code==422


def test_referenced_labels_are_immutable_and_changes_audited(client,db):
    created=client.post('/api/v1/grievance-categories',json={'label_en':'Water fee','label_rw':'Amafaranga y’amazi'}).json()
    db.add(CommunityFeedback(category='Water fee',message='test'));db.commit()
    url=f'/api/v1/grievance-categories/{created["id"]}'
    assert client.patch(url,json={'label_en':'New meaning'}).status_code==409
    assert client.patch(url,json={'is_active':False}).status_code==200
    assert db.scalar(select(AuditEvent).where(AuditEvent.action=='grievance_category.update')) is not None
