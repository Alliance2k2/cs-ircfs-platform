"""Preview-first policy-controlled minimisation; scientific report rows are retained."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select
from app.core.config import get_settings
from app.core.security import Principal
from app.db.models import (AdvisoryMessage, AuditEvent, CitizenScienceLog, FieldUser, IncentiveReward,
    InboundMessage, IrrigationClimateLog, NutritionSurvey, DeliveryReceipt, UserRole)
from app.services.audit import record


def retention_plan(db, now=None, apply=False, policy_reference=None):
    if apply and (not policy_reference or len(policy_reference.strip()) < 5):
        raise ValueError("Apply requires the district-approved policy reference")
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    person_cutoff = now - timedelta(days=max(1, settings.field_user_retention_days))
    message_cutoff = now - timedelta(days=max(1, settings.message_retention_days))
    audit_cutoff = now - timedelta(days=max(1, settings.audit_log_retention_days))
    people_query = select(FieldUser).where(FieldUser.created_at < person_cutoff,
        ~FieldUser.phone_number.like("ret-%"), FieldUser.data_origin != "simulator")
    people = list(db.scalars(people_query.with_for_update() if apply else people_query))
    eligible, blocked = [], 0
    for person in people:
        recent = any(db.scalar(select(model.id).where(model.reporter_id == person.id, model.created_at >= person_cutoff).limit(1))
                     for model in (CitizenScienceLog, IrrigationClimateLog, NutritionSurvey))
        recent = recent or db.scalar(select(InboundMessage.id).where(InboundMessage.phone_number == person.phone_number,
            InboundMessage.created_at >= person_cutoff).limit(1))
        pending = db.scalar(select(AdvisoryMessage.id).where(AdvisoryMessage.phone_number == person.phone_number,
            AdvisoryMessage.status.in_(["queued","dispatching"])).limit(1))
        pending = pending or db.scalar(select(IncentiveReward.id).where(IncentiveReward.field_user_id == person.id,
            IncentiveReward.status.in_(["pending","queued","dispatching"])).limit(1))
        if recent or pending: blocked += 1
        else: eligible.append(person)
    inbound_query = select(InboundMessage).where(InboundMessage.created_at < message_cutoff,
        or_(InboundMessage.phone_number != "withheld", InboundMessage.text.is_not(None), InboundMessage.reply.is_not(None)))
    outbound_query = select(AdvisoryMessage).where(AdvisoryMessage.created_at < message_cutoff,
        AdvisoryMessage.status.not_in(["queued","dispatching"]),
        or_(AdvisoryMessage.phone_number != "withheld", AdvisoryMessage.message != "[retained metadata only]"))
    rewards_query = select(IncentiveReward).where(IncentiveReward.created_at < message_cutoff,
        IncentiveReward.status.not_in(["pending","queued","dispatching"]), IncentiveReward.phone_number != "withheld")
    audit_query = select(AuditEvent).where(AuditEvent.created_at < audit_cutoff, AuditEvent.action == "personal.read")
    inbound = list(db.scalars(inbound_query)); outbound = list(db.scalars(outbound_query))
    rewards = list(db.scalars(rewards_query)); audits = list(db.scalars(audit_query))
    receipts = list(db.scalars(select(DeliveryReceipt).where(DeliveryReceipt.received_at < message_cutoff)))
    counts = {"profiles_to_pseudonymize":len(eligible), "profiles_blocked_by_activity_or_queue":blocked,
        "inbound_to_minimize":len(inbound), "outbound_to_minimize":len(outbound), "rewards_to_minimize":len(rewards),
        "audit_events_to_delete":len(audits), "receipts_to_delete":len(receipts), "scientific_reports_to_delete":0}
    if apply:
        session_aliases = {}
        for item in inbound:
            if item.session_id:
                key = (item.channel, item.session_id)
                item.session_id = session_aliases.setdefault(key, "ret-" + secrets.token_hex(16))
            item.phone_number, item.text, item.reply, item.record_id = "withheld", None, None, None
        for item in outbound:
            item.phone_number, item.message, item.provider_id = "withheld", "[retained metadata only]", None
            item.private_recipient, item.private_recipient_expires_at = None, None
        for item in rewards: item.phone_number, item.provider_id = "withheld", None
        for person in eligible:
            person.phone_number = "ret-" + hashlib.sha256(str(person.id).encode()).hexdigest()[:16]
            person.full_name = person.cooperative_name = person.location = person.cell_id = person.cooperative_id = None
            person.training_notes = person.trained_at = person.consent_at = None
            person.is_active = person.is_data_champion = False
            person.opted_out_at = now
        for receipt in receipts: db.delete(receipt)
        for event in audits: db.delete(event)
        record(db, Principal(name="retention-operator", role=UserRole.administrator), "retention.applied", "retention",
               policy_reference=policy_reference.strip(), **counts)
        # Caller owns commit so any failure preserves the original data.
        db.flush()
    return {"mode":"apply" if apply else "preview", "counts":counts,
        "policy_required":True, "message_retention_days":settings.message_retention_days,
        "note":"Pseudonymization is not a claim of irreversible anonymity. Historical activity totals may change as identity links expire. Scientific mutation/provenance audit trails are retained. No stored CSV exports are managed by this service."}
