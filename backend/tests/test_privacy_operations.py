from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from app.core.config import Settings
from app.core.security import Principal
from app.db.models import AuditEvent,FieldUser,CitizenScienceLog,InboundMessage,AdvisoryMessage,UserRole
from app.services import retention
from app.services.audit import personal_read


def test_personal_read_audit_is_bounded_and_contains_no_private_values(db):
    principal=Principal(name="planner",role=UserRole.district_planner)
    personal_read(db,principal,"field_user",rows=3)
    personal_read(db,principal,"field_user",rows=3)
    events=list(db.scalars(select(AuditEvent)))
    assert len(events)==1 and events[0].action=="personal.read"
    assert events[0].detail=='{"rows": 3}'
    personal_read(db,Principal(name="monitor",role=UserRole.citizen_science_monitor),"field_user")
    assert db.scalar(select(func.count()).select_from(AuditEvent))==1


def test_retention_preview_does_not_change_profiles_and_apply_preserves_reports(db):
    old=datetime.now(timezone.utc)-timedelta(days=800)
    person=FieldUser(phone_number="+250788123456",full_name="Private Name",created_at=old)
    db.add(person);db.flush()
    report=CitizenScienceLog(reporter_id=person.id,crop_type="Maize",created_at=old)
    inbound=InboundMessage(phone_number=person.phone_number,channel="sms",text="Private text",reply="Private reply",created_at=old)
    db.add_all([report,inbound]);db.commit()
    preview=retention.retention_plan(db)
    assert preview["counts"]["profiles_to_pseudonymize"]==1
    db.expire_all();assert person.phone_number=="+250788123456" and inbound.text=="Private text"
    import pytest
    with pytest.raises(ValueError):retention.retention_plan(db,apply=True)
    retention.retention_plan(db,apply=True,policy_reference="Approved district test policy")
    db.commit()
    assert person.phone_number.startswith("ret-") and person.full_name is None and not person.is_active
    assert inbound.phone_number=="withheld" and inbound.text is None
    assert db.get(CitizenScienceLog,report.id) is not None
    assert db.scalar(select(AuditEvent).where(AuditEvent.action=="retention.applied")) is not None


def test_retention_blocks_profiles_with_recent_activity_or_queued_messages(db):
    old=datetime.now(timezone.utc)-timedelta(days=800)
    person=FieldUser(phone_number="+250788123456",created_at=old)
    db.add(person)
    db.add(AdvisoryMessage(phone_number=person.phone_number,message="queued",status="queued",created_at=old))
    db.commit()
    plan=retention.retention_plan(db)
    assert plan["counts"]["profiles_to_pseudonymize"]==0
    assert plan["counts"]["profiles_blocked_by_activity_or_queue"]==1

def test_legacy_report_lists_mask_free_text_for_monitors_and_audit_staff_reads(client,auth,db):
    from app.db.models import CitizenScienceLog
    db.add(CitizenScienceLog(crop_type='Maize',notes='Private household detail'))
    db.commit()
    monitor=auth('legacy-monitor@example.org',role=UserRole.citizen_science_monitor)
    response=client.get('/api/v1/citizen-reports',headers=monitor)
    assert response.status_code==200 and response.json()[0]['notes'] is None
    planner=auth('legacy-planner@example.org',role=UserRole.district_planner)
    response=client.get('/api/v1/citizen-reports',headers=planner)
    assert response.json()[0]['notes']=='Private household detail'
    assert db.scalar(select(AuditEvent).where(AuditEvent.action=='personal.read')) is not None
