# FieldVoice India Field Work Knowledge Base

This Markdown file is the domain knowledge source for RAG-style retrieval in the FieldVoice demo. It is written for Indian industrial and infrastructure field-work scenarios and is meant to improve domain-aware voice capture, extraction, and question answering.

It is not a legal or safety compliance document. Field teams must still follow their company SOPs, site permit systems, and applicable local regulations.

## Core Field Roles

Field technician: captures inspection notes, reads meters, checks alarms, takes photos, performs basic corrective actions, and raises work orders.

Supervisor: reviews exceptions, assigns jobs, approves shutdowns, monitors high-severity faults, and validates closure notes.

Maintenance planner: tracks spare parts, schedules preventive maintenance, and reviews repeated faults.

Safety officer: reviews permit-to-work, lockout tagout, PPE, near-miss reports, and unsafe-condition alerts.

## Indian Field Conditions

Common environments include manufacturing plants, water-treatment facilities, commercial buildings, hospitals, telecom tower sites, metro or rail assets, solar plants, distribution substations, and residential society utility rooms.

Common constraints include high ambient temperature, dust, monsoon water ingress, unreliable mobile network, power cuts, high background machine noise, mixed Hindi-English speech, regional place names, and workers wearing gloves or helmets.

Common location phrases include north plant bay, pump house, utility room, DG yard, LT panel room, HT yard, roof solar inverter room, basement sump, STP area, WTP area, compressor room, chiller plant, line one, line two, tower site, feeder pillar, and maintenance store.

## Voice Capture Vocabulary

Equipment codes should be recognized even when spoken with NATO or Indian callouts:

- PMP-204B: pump 204 Bravo, P M P two zero four B, pump two zero four bravo
- CMP-118A: compressor 118 Alpha, C M P one one eight A
- VLV-77C: valve 77 Charlie, V L V seventy seven C
- DG-125KVA-01: diesel generator 125 kVA one, DG set one
- TRF-33KV-02: transformer 33 kV two, transformer yard two
- RMU-FDR-07: ring main unit feeder seven
- INV-SOLAR-03: solar inverter three
- STP-PMP-02: sewage treatment plant pump two
- AHU-05: air handling unit five
- CHW-PMP-01: chilled water pump one

Technical vocabulary:

- bearing temperature
- vibration
- coupling alignment
- mechanical seal
- gland packing
- oil level
- coolant flow
- suction pressure
- discharge pressure
- current draw
- overload relay
- MCC panel
- PCC panel
- LT panel
- HT panel
- ACB
- VCB
- MCB
- RCCB
- ELCB
- earthing
- neutral voltage
- insulation resistance
- thermal scan
- hot spot
- water ingress
- seepage
- diesel level
- battery voltage
- radiator coolant
- alternator
- busbar
- cable gland
- ferrule
- lug
- torque marking
- lockout tagout
- permit to work
- isolation
- barricading
- near miss

Indian speech variants and common phrases:

- "current jyada hai" means current is high.
- "garam ho raha hai" means temperature is high or overheating.
- "pani aa raha hai" means water ingress or leakage.
- "trip ho gaya" means equipment tripped.
- "load kam karo" means reduce load.
- "seal leak hai" means seal is leaking.
- "DG start nahi ho raha" means diesel generator is not starting.

## Work Order Fields

Every voice-created work order should try to capture:

- equipment_code
- inspection_result
- fault_code
- location
- severity
- action_taken
- parts_required
- status
- created_by
- transcript

Recommended severity mapping:

- LOW: observation only, minor noise, paint damage, loose label, housekeeping issue.
- MEDIUM: degraded performance, repeated warning, minor leakage, abnormal reading but equipment still available.
- HIGH: overheating, high vibration, trip event, safety risk, important spare required, repeated failure.
- CRITICAL: fire, shock risk, major leak, smoke, complete shutdown, unsafe energized panel, flooding near electrical equipment.

Recommended status mapping:

- OPEN: new work order created and not yet assigned.
- IN_PROGRESS: technician or maintenance team is working.
- ESCALATED: supervisor attention required.
- CLOSED: issue resolved and closure note captured.

## Fault Taxonomy

Mechanical faults:

- F12: bearing temperature high
- F18: vibration above limit
- F21: mechanical seal leak
- F24: coupling misalignment
- F29: abnormal noise

Electrical faults:

- E07: overload trip
- E11: phase imbalance
- E14: low insulation resistance
- E19: hot spot in panel
- E22: earth leakage

Utility faults:

- U03: low suction pressure
- U05: water ingress
- U08: air filter choking
- U12: coolant flow low
- U15: diesel level low

Solar and power faults:

- S04: inverter offline
- S09: string current mismatch
- S11: DC isolator fault
- P06: transformer oil temperature high
- P10: feeder trip

## Pump Inspection Procedure

Use for PMP-204B, STP-PMP-02, CHW-PMP-01, and similar pumps.

1. Confirm the pump tag and location before recording.
2. Check suction and discharge pressure.
3. Listen for abnormal noise.
4. Check bearing temperature.
5. Check vibration by touch or meter if available.
6. Inspect mechanical seal or gland packing for leakage.
7. Check coupling guard and base bolts.
8. Record action taken and required spares.
9. Escalate if temperature is high, vibration is severe, or leakage is increasing.

Good voice note:

"Inspecting pump PMP 204 Bravo at north plant bay four. Bearing temperature high, fault code F twelve. Action applied coolant. Need replacement seal kit. Severity high."

## Diesel Generator Inspection Procedure

Use for DG-125KVA-01 and similar DG sets.

1. Check panel status and alarm history.
2. Check diesel level.
3. Check engine oil level.
4. Check battery voltage and charger status.
5. Check radiator coolant level.
6. Inspect for fuel leakage.
7. Start in manual test mode only if permitted.
8. Record running voltage, frequency, and load.
9. Escalate if the DG does not start, has fuel leakage, or shows abnormal smoke.

Good voice note:

"Inspecting DG 125 kVA one at DG yard. Battery voltage low, fault code U fifteen. Action cleaned terminals. Need battery replacement. Severity medium."

## Transformer Yard Inspection Procedure

Use for TRF-33KV-02 and similar transformer or HT yard assets.

1. Confirm safe access and authorization.
2. Check oil temperature and winding temperature indicators.
3. Check oil level in conservator.
4. Check silica gel breather color.
5. Look for oil leakage around gasket and radiator.
6. Check unusual humming, smell, or visible hot spots.
7. Record feeder or transformer code clearly.
8. Escalate immediately for smoke, oil leak, abnormal sound, or high temperature.

Good voice note:

"Inspecting transformer TRF 33 kV zero two at HT yard. Oil temperature high, fault code P zero six. Action reduced load after supervisor approval. Need thermal scan. Severity high."

## Electrical Panel Inspection Procedure

Use for MCC, PCC, LT panel, HT panel, feeder pillar, and RMU assets.

1. Check panel name and feeder number.
2. Look for alarm lamps, trip indicators, or breaker status.
3. Check load current on each phase.
4. Listen for buzzing or loose contact noise.
5. Check panel temperature or hot spot with thermal camera if available.
6. Check cable gland condition and door gasket.
7. Do not open energized panels without authorization and required PPE.
8. Escalate for burning smell, smoke, hot spot, earth leakage, or repeated breaker trip.

Good voice note:

"Inspecting RMU feeder seven at basement panel room. Feeder tripped, fault code P ten. Action reset not attempted. Need supervisor inspection. Severity critical."

## Solar Site Inspection Procedure

Use for INV-SOLAR-03 and rooftop or ground-mounted solar assets.

1. Check inverter status and alarms.
2. Check DC isolator position.
3. Compare string current values.
4. Inspect cable trays, MC4 connectors, and water ingress.
5. Check dust accumulation on panels.
6. Record inverter code and alarm text.
7. Escalate for DC fault, burning smell, water ingress, or repeated inverter trip.

Good voice note:

"Inspecting solar inverter three on roof. Inverter offline, fault code S zero four. Action checked DC isolator. Need connector inspection. Severity medium."

## Monsoon Field Work Notes

During monsoon, pay extra attention to water ingress, cable gland sealing, panel door gaskets, sump overflow, slippery access routes, earthing pits, and outdoor junction boxes.

Voice note should mention if the site is wet, flooded, leaking, or unsafe to access.

Escalate if water is near energized electrical equipment, if panel insulation is suspected to be compromised, or if access is unsafe.

Good monsoon query:

"What should I check during monsoon inspection of an LT panel?"

Expected answer should include water ingress, cable glands, door gaskets, earthing, safe access, and escalation for water near energized equipment.

## Heat and Dust Field Work Notes

During high temperature and dusty conditions, check air filters, ventilation, radiator fins, panel fans, chiller plant cleanliness, compressor intake filters, and motor bearing temperature.

Dust can cause overheating in VFD panels, inverter rooms, compressor filters, and DG radiators.

Good query:

"What should I check when a compressor is overheating in a dusty utility room?"

Expected answer should include intake filter, ventilation, oil level, load, and temperature trend.

## Offline Operation Rules

Field workers may lose network in basements, plants, remote solar sites, tower sites, and HT yards.

Offline commands should be stored with a client UUID, original transcript, worker ID, timestamp, and command mode.

Sync should be idempotent: the same client UUID must not create duplicate work orders.

Critical notes should be queued first and shown clearly after reconnection.

## Voice Query Examples

Ask maintenance history:

"What is the last maintenance date for PMP-204B?"

Ask procedure:

"What is the high bearing temperature procedure for PMP-204B?"

Ask Indian monsoon context:

"What should I check during monsoon inspection of an LT panel?"

Ask DG set context:

"What should I capture for DG set inspection in India?"

Ask escalation:

"When should I escalate water ingress near an electrical panel?"

Ask vocabulary:

"What does trip ho gaya mean in a field note?"

## Demo Equipment Knowledge

PMP-204B is a boiler feed pump in North Plant Bay 4. Important terms are bearing temperature, seal kit, coolant flow, and fault F12.

CMP-118A is an air compressor in Utility Room 2. Important terms are intake filter, oil carryover, pressure drop, and fault F07.

VLV-77C is a steam isolation valve on Line 7 Station C. Important terms are stem packing, torque reading, lockout tagout, and fault F31.

DG-125KVA-01 is a diesel generator used for backup power. Important checks are diesel level, battery voltage, coolant level, oil level, smoke, and start failure.

TRF-33KV-02 is a transformer yard asset. Important checks are oil temperature, winding temperature, oil level, silica gel breather, leakage, humming, and hot spot.

INV-SOLAR-03 is a solar inverter. Important checks are inverter status, DC isolator, string current, water ingress, connector condition, and alarm code.
