"""Best-effort request guards, not comprehensive PII or injection detection."""
import re

INJECTION = re.compile(r"ignore (?:all |the |previous )?(?:instructions|evidence|rules)|reveal (?:the |hidden )?(?:database password|instructions|secrets)|\bSYSTEM\s*[: ]+reveal", re.I)
PRIVATE_REQUEST = re.compile(r"(?:show|list|give|export|find)\b.{0,80}\b(?:participant phone|phone numbers|private records)|which households.{0,40}complain", re.I)
LIVE = re.compile(r"\b(?:today'?s?|current|live|latest)\b.{0,80}\b(?:total|budget|participant|household|rainfall reading)", re.I)
EQUIPMENT_STATUS = re.compile(
    r"\b(?:which|what|any|list|show)\b.{0,60}\b(?:pumps?|assets?|equipment)\b.{0,60}\b(?:not working|broken|faulty|down|offline|failed)\b"
    r"|\b(?:which|what|any|list|show)\b.{0,60}\b(?:broken|faulty|failed)\s+(?:pumps?|assets?|equipment)\b"
    r"|\b(?:is|are)\b.{0,40}\b(?:pumps?|equipment)\b.{0,30}\b(?:working|operational|online|offline)\b", re.I)
RW = {"nigute", "ururimi", "imvura", "amakuru", "raporo", "ubutumwa", "nshobora", "ryari"}


def language_hint(question):
    """Limited heuristic; explicit UI choice is preferred. Never native certification."""
    return "rw" if set(re.findall(r"\w+", question.casefold())) & RW else "en"


def rewrite(question, history):
    # Only carry a previous *user* question into short pronoun follow-ups. Never
    # accept assistant-generated text as trusted evidence or access instructions.
    if history and re.match(r"^(?:what about|and |how about|does that|why is that|what does that)", question, re.I):
        return history[-1] + "\nFollow-up: " + question
    return question
