# CS Assistant

> 24 November: the existing chat, document workspace and authorization model are preserved. Main suggestions, input controls, evidence modes and feedback controls now use the shared EN/RW interface dictionaries. RW wording remains draft. Review [the keyed native-review pack](modernization-native-review-20261124.json) and [remaining source-located UI candidates](modernization-ui-review-20261124.json) with native-speaking staff; neither file records approval. The [modernization report](modernization-2026-11-24.md) contains the 64-case lexical comparison. No semantic score or generated-answer faithfulness score is claimed without the required model and validation. Generation remains disabled by default; the local document lookup needs no paid provider.

Open **CS Assistant** in the staff dashboard or visit `/app/assistant`.
It answers platform-procedure questions from authorized, approved source excerpts.
The default is local document lookup; it has no live participant or equipment data.

The compact chat includes suggestions, a fixed composer, keyboard sending, source
references, copy/feedback, New Chat and bounded page-only conversation history.
Administrator source management is collapsed beneath the chat. Uploads stay disabled
until the extraction environment is explicitly approved. External generation stays
off by default. Enabling it is a separate operator decision, not part of a UI change.

- [Operator and engineering guide](ai/ASSISTANT_OPERATIONS.md): chat behavior, source
  search, approvals, index repair, security controls and beginner-friendly decisions.
- [Audit and prioritized plan](ai/ASSISTANT_AUDIT_2026-11-19.md): observed implementation,
  gaps and retrieval baseline.
- [Actual validation and limits](ai/VALIDATION_2026-11-19.md): test results and remaining gates.
- [Existing architecture reference](ai/RAG_ARCHITECTURE.md): optional embedding/vector adapters.

Only district officers, planners and administrators may ask questions. Managed
sources are filtered by document role, required sectors and approved version before
chunk text is retrieved. All permitted staff can use the packaged general procedures.

Citations establish source provenance, not institutional truth or semantic correctness.
Full source text, revision and available page/logical-section metadata can be expanded.
Never enter participant details, grievances, personal documents or credentials.

Run locally with `./start-local.ps1 -Demo`; no upload or AI-provider activation is
needed. The demo uses a separate SQLite database and requires normal account sign-in.
