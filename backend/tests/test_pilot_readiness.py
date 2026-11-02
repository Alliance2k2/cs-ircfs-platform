def test_readiness_uses_real_current_evidence_and_never_authorizes_training(client,db):
    from app.db.models import CitizenScienceLog
    db.add(CitizenScienceLog(crop_type='Demo',data_origin='demo',reported_harvest_tons=900))
    db.commit()
    response=client.get('/api/v1/admin/readiness')
    assert response.status_code==200
    body=response.json()
    assert body['field_crop_reports']==0 and body['measured_yield_reports']==0
    assert body['ml_training_authorized'] is False and body['causal_impact_established'] is False
