# USSD and SMS field channels

Citizens with feature phones and no internet report through two channels. Both are routed by Africa's Talking (architecture Section 4).

| Channel | Number | Callback the gateway calls | Code |
| --- | --- | --- | --- |
| USSD menu | `*801#` | `POST /api/v1/ussd` | [backend/app/services/ussd.py](../backend/app/services/ussd.py) |
| SMS keywords | `8448` | `POST /api/v1/sms/inbound` | [backend/app/services/sms_keywords.py](../backend/app/services/sms_keywords.py) |
| Outbound SMS and airtime | (sender ID `CS-IRCFS`) | Africa's Talking Messaging and Airtime APIs | [backend/app/services/sms.py](../backend/app/services/sms.py) |

A first-time caller is registered automatically as a farmer, keyed by phone number. On their first `*801#` call they choose their sector (two screens of 8 + 7) and then their cell; the session ends and they dial again to report. The cell is what links a report to the map, to a scheme, and to closing-the-loop messages. Planners can still correct it in **Platform Management → Users**.

Retried SMS deliveries (same Africa's Talking message `id`) are ignored, so a retry never creates a second report or reply.

## USSD menu (Kinyarwanda first)

The menu follows the design rules in Section 8.4:
- numeric answers wherever possible
- no free text except a grievance message
- at most three levels below the main menu

```text
Kaze kuri CS-IRCFS. Hitamo:
1. Rapora umusaruro            → crop (1–5) → expected tons             → reply + local irrigation tip
2. Indwara/udukoko             → crop → problem (1 Nzana …) → severity 1–5  → severity 4–5 opens an Act Now case
3. Rapora imvura               → mm today                              → airtime every 3rd report + tip
4. Ibikorwa remezo byo kuhira  → asset (PADAB pumps 1–2, canal, APEFA Ngeruka/Mareba) → condition → bottleneck category
5. Tanga ikibazo/igitekerezo   → category (incl. resettlement/downstream) → message (anonymous)
6. Imirire y'urugo             → meals yesterday → varied diet → enough food → stunting-risk score 1–5
```

The infrastructure asset list comes from the PADAB inventory (2 pumping stations, 65.5 km of canals) and the APEFA solar pumps (Section 9.2).

**Before the pilot,** have the field team and cooperative leaders review every Kinyarwanda screen. Keep each screen under 182 characters.

## SMS keywords to 8448

| Text | Result |
| --- | --- |
| `NYAMATA NZANA 4` | Fall-armyworm alert in Nyamata, severity 4. This feeds the pest heatmap and the Act Now queue. The sector name is optional. |
| `INDWARA IBISHYIMBO` | Crop-disease report on beans |
| `IMVURA 12` | 12 mm at the sender's rain gauge. This counts towards the airtime reward. |
| `UMUSARURO IBIGORI 2.5` | Expected maize harvest of 2.5 tons |
| `IKIBAZO <message>` | Anonymous grievance |
| anything else | Help message listing the keywords |

Every report gets an immediate reply in Kinyarwanda. Rain and harvest reports also get the sector's irrigation advice (the "Local Insights" mechanic, Section 8.3).

## Africa's Talking setup

1. Create an app at africastalking.com. Use the **sandbox** first: it is free and has a phone simulator.
2. **USSD:** create a service code (sandbox: `*384*xxxx#`; production: request `*801#`). Set its callback URL to `https://<your-host>/api/v1/ussd`.
3. **SMS:** create a short code or alphanumeric sender. Set the incoming-messages callback to `https://<your-host>/api/v1/sms/inbound`.
4. In `.env` (or `infrastructure/stack.env`) set:
   ```env
   SMS_PROVIDER=africas_talking
   AIRTIME_PROVIDER=africas_talking      # only when the airtime budget is approved
   AFRICAS_TALKING_USERNAME=sandbox      # your app username in production
   AFRICAS_TALKING_API_KEY=...
   SMS_SENDER_ID=                        # empty in the sandbox; set only after approval
   ```
5. For a local sandbox test, expose the local platform with a tunnel such as `ngrok http 8000`, and use the tunnel URL as the callback.
6. **Zero cost to farmers:** ask the aggregator for a reverse-billed (toll-free) USSD code and short code (Section 8.1).

Until step 4 is done, the platform runs in **dry-run** mode. Every outgoing SMS and airtime reward is recorded with status `dry_run` (visible in **Platform Management → SMS log**), but nothing reaches a phone.

## Trying it without a telecom contract

Open `/simulator.html`. The on-screen phone calls the same callbacks with the same data, and shows each step with an English translation and the database record it created.
