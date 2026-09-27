# Requirement tracker - tick every line before submitting

## Common rules for all problems

- [ ] Domain research performed before finalising the class model → `docs/research.md` (**write your paragraphs and sources**)
- [x] Not every business noun became a class → `docs/rejected.md`; job titles, delay codes, SSR codes, cabin classes, delay reasons are attributes
- [x] Not every similar concept uses inheritance → `docs/rejected.md` (6 rejected hierarchies)
- [x] At least 30 meaningful classes → 49 (`Design` tab, `python main.py` last line)
- [x] At least 30 meaningful operations → 61 in `airline/operations.py`, every one enforces a rule or changes lifecycle
- [x] At least one multi-level inheritance structure → Record → Person → Employee → CrewMember → FlightDeckCrew / CabinCrew
- [x] Historical records stay meaningful after change/leave/expire/transfer/retire → `TemporalRecord`, superseded links, demos' `check` lines
- [x] Normal AND exceptional workflows demonstrated → seed (normal), 8 demos (exceptional)
- [x] Ambiguities stated with the assumption adopted → `docs/assumptions.md`
- [x] Design defended against a plausible alternative → `docs/inheritance.md` + `docs/rejected.md`

## System scope coverage

| Scope area | Classes | Operations |
|---|---|---|
| aircraft fleet records and changing configurations | AircraftType, Aircraft, CabinConfiguration, Seat, Component | register_aircraft, reconfigure_cabin, retire_aircraft, install/remove_component |
| airports, routes, scheduled services, individual flights | Airport, AirportRestriction, Route, ScheduledService, Flight, AircraftAssignment, FlightMovement | create_scheduled_service, create_flight, assign/substitute_aircraft, depart/arrive_flight |
| employee records, qualifications, rosters, assignments, availability | Employee hierarchy, RoleAssignment, Qualification, CrewAssignment, DutyPeriod | hire_employee, change_role, grant/revoke_qualification, roster_duty, assign/release/swap_crew, position_crew |
| reservations, travellers, documents, check-in, seating, boarding, special requests | Booking, FlightSegment, Passenger, TravelDocument, CheckIn, SeatAssignment, SpecialServiceRequest | create_booking, add_segment, assign_seat, add_travel_document, add_special_service, check_in/board/offload_passenger, rebook_segment, change_cabin |
| baggage acceptance, loading, transfer, irregularity, tracing | Bag, BagMovement, BaggageIrregularity | accept/load/offload/reroute_bag, report/resolve_bag_irregularity |
| cargo bookings, consignments, handling, acceptance, loading, delivery | Consignment, HandlingRequirement, CargoLoad | book_consignment, declare_handling, accept_consignment, load/offload_cargo, deliver_consignment |
| engineering inspections, defects, work, components, availability | EngineeringRecord, Inspection, Defect, WorkOrder, Component | record_inspection, raise/escalate/defer/rectify_defect, open/complete_work_order |
| delay, cancellation, diversion, replacement, disruption records | Disruption hierarchy, RecoveryOption | declare_delay, propose/choose_recovery, cancel_flight, divert_flight, substitute_aircraft |
| charter/customer agreements and operational requests | CharterAgreement, Organisation | create_charter_agreement, amend_charter |
| historical reporting across changed or cancelled records | Event, Registry.journal, TemporalRecord.is_valid_at | what_was_true_at, report.end_of_day, `/api/record/<id>` history |

## Critical and conflicting cases → demo

| Case | Demo (Scenarios tab order) |
|---|---|
| aircraft retired after future flights planned around it | 7 |
| cabin configuration changes after bookings exist | 7 |
| flight changes aircraft twice before departure | 2 |
| passenger checks in but is later removed | 5 |
| bag travels on a different routing from its owner | 5 |
| cargo accepted and later needs different handling | 6 |
| crew member changes role/qualification, old assignments accurate | 1 (promotion), 8 (new qualification) |
| delayed inbound threatens later flights, several valid recovery choices | 3 |
| flight cancelled but still in operational and financial history | 4 |
| airport restriction temporary, historical analysis shows it existed | 4 |

## Required submission

1. [ ] Domain-research summary with sources and terminology → `docs/research.md` (**you**)
2. [x] Assumptions list → `docs/assumptions.md`
3. [x] Requirements interpretation → `docs/requirements.md`
4. [x] Class diagram → `docs/class_diagram.md` (Mermaid) + live tree on Design tab
5. [x] Python implementation at required scale → `airline/`
6. [x] Explanation of every inheritance relationship → `docs/inheritance.md`
7. [x] ≥3 rejected inheritance relationships → `docs/rejected.md`
8. [x] Seeded demonstration → `airline/seed.py`
9. [x] ≥5 complex scenario demonstrations → `airline/demos.py` (8)
10. [x] Limitations and scaling discussion → `docs/limitations.md`

## Assessment emphasis (last page of the brief) - self-check

- Domain research: research.md filled in with real sources? ☐
- Class discovery: every class has identity/lifecycle/history (see `prefix` and statuses) ☑
- Inheritance reasoning: inheritance.md argues the *level* for each shared field ☑
- Historical correctness: no operation edits a historical record; supersede/end/link instead ☑
- Operations: arise from workflows, each with a rule (grep `_refuse` in operations.py) ☑
- Exception handling in the model: 10 refused attempts in the seeded day, all logged ☑
- Critical thinking: 6 rejected hierarchies, 14 explicit assumptions ☑
