"""Personal-data minimisation for API responses.

District officers, planners and administrators act on individual reports and need to
see who sent them. Citizen Science Monitors and cooperative leaders follow the live
picture, so they get masked phone numbers and no message text.
"""
from app.core.security import Principal
from app.db.models import UserRole

# Stored instead of a phone number where the sender must stay anonymous (grievances).
WITHHELD = "withheld"
PERSONAL_DATA_ROLES = frozenset({UserRole.district_officer, UserRole.district_planner, UserRole.administrator})


def sees_personal_data(principal: Principal) -> bool:
    return principal.role in PERSONAL_DATA_ROLES


def mask_phone(phone: str | None) -> str | None:
    """'+250788123456' -> '+250 7•• ••• 456'. Short or withheld values are returned as-is."""
    if not phone or phone == WITHHELD or len(phone) < 8:
        return phone
    return f"{phone[:4]} {phone[4]}•• ••• {phone[-3:]}"
