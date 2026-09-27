# Requirements interpretation (item 3)

What the system must represent, how records move through their lives, and which exceptional
cases it must survive. Written from the brief plus the domain research; assumptions are in
`assumptions.md`.

## Main records

| Area | Records | Notes |
|---|---|---|
| Fleet | AircraftType, Aircraft, CabinConfiguration (versioned), Seat, Component | a type is certified; an airframe is owned, maintained and configured |
| Network | Airport, AirportRestriction, Route, ScheduledService, Flight, AircraftAssignment, FlightMovement | plan vs instance vs physical movement |
| People | Organisation, Person, Passenger, Employee, CrewMember, FlightDeckCrew, CabinCrew, MaintenanceEngineer, GroundStaff, RoleAssignment, Qualification, CrewAssignment, DutyPeriod | titles and certificates are dated records |
| Commercial | Booking, FlightSegment, SeatAssignment, TravelDocument, CheckIn, SpecialServiceRequest, CharterAgreement | one segment per passenger per flight |
| Baggage | Bag, BagMovement, BaggageIrregularity | a bag's routing can differ from its owner's |
| Cargo | Consignment, HandlingRequirement, CargoLoad | requirements are dated; loads are per flight |
| Maintenance | EngineeringRecord, Inspection, Defect, WorkOrder | the technical log |
| Disruption | Disruption, Delay, Cancellation, Diversion, AircraftSubstitution, RecoveryOption | decisions and their alternatives |

## Workflows (normal path)

1. **Publish schedule → create flights → assign aircraft → assign crew.** Crew assignment is
   refused unless the person is qualified on the flight's aircraft type, positioned at the
   origin (or arriving there earlier that day), not on rest/leave, and within the duty limit.
2. **Book → seat → check in → accept bags → board → depart → arrive.** Check-in on an
   international flight requires a valid travel document. Departure requires CP, FO and SCCM.
3. **Book cargo → declare handling → accept onto a flight → load → deliver.** Acceptance is
   refused if the aircraft's remaining capacity is exceeded; loading is refused if held.
4. **Inspect → raise defect → defer under MEL or rectify → work order → return to service.**
   Only a certifying engineer on the type may defer or rectify; grounding defects cannot be
   deferred.

## Lifecycles (statuses a record can hold)

* Aircraft: `in_service → aog → in_service`, `→ retired`
* CabinConfiguration / Qualification / RoleAssignment / assignments: `active → superseded | ended | released | replaced | cancelled | revoked | lifted`
* Flight: `planned → delayed → departed → arrived`, `→ diverted`, `→ cancelled`, `→ needs_aircraft → planned`
* FlightSegment: `confirmed → checked_in → boarded → flown`, `→ seat_pending → confirmed`, `→ offloaded`, `→ rebooked`, `→ cancelled | cancelled_flight`
* CheckIn: `checked_in → boarded`, `→ offloaded`
* Bag: `accepted → loaded → offloaded → loaded ...`, `→ irregular_*`
* Consignment: `booked → accepted → loaded → delivered`, `→ held`
* Defect: `open → deferred | rectified`, plus `grounding` flag
* Disruption: `open → resolved`; RecoveryOption: `proposed → chosen | rejected`
* CharterAgreement: `agreed → amended`

Nothing moves to a "deleted" state. Ending a period sets `valid_to`.

## Exceptional cases the model must support (and where each is demonstrated)

| Case from the brief | Demo |
|---|---|
| aircraft retired after future flights were planned on it | 7 |
| cabin configuration changes after bookings exist | 7 |
| a flight changes aircraft twice before departure | 2 |
| a passenger checks in but is later removed | 5 |
| a bag travels on a different routing from its owner | 5 |
| cargo accepted and later found to need different handling | 6 |
| crew member changes role/qualification, old assignments stay accurate | 1, 8 |
| delayed inbound threatens later flights, several valid recovery choices | 3 |
| a flight is cancelled but stays in operational and financial history | 4 |
| an airport restriction applies temporarily and later disappears | 4 |
| substitute aircraft: seat assignments no longer exist | 2 |
| employee has the right job title but not the qualification | 1 |
| infant, mobility assistance, connecting passengers, temperature-sensitive cargo | seed, 2, 3, 6 |
| travel-document problem after check-in | 5 |
| damaged baggage on arrival | 6 |
| charter customer changes passenger numbers last-minute | 8 |
| end-of-day explanation of what changed, who was affected and why | report |

(Demo numbers are the order on the Scenarios tab: 1 crew, 2 substitution, 3 delayed inbound,
4 restriction & cancellation, 5 offload & bag routing, 6 cargo & damaged bag,
7 reconfiguration & retirement, 8 charter & diversion.)
