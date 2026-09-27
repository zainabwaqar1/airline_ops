# Inheritance relationships and why the shared information sits where it does (item 6)

The full tree, generated from the code, is on the **Design** tab of the console. Four
structures came out of the domain analysis. For each: what is shared, why it belongs at
that level, and what would go wrong if it sat elsewhere.

## 1. The multi-level people hierarchy

```
Record
└── Person                      first/last name, date of birth, nationality, travel documents
    ├── Passenger               frequent-flyer number, is_infant()
    └── Employee                staff number, base airport, employment status,
        │                       role_at(t), qualifications_at(t)
        ├── CrewMember          duty limit, physical position, qualified_for(type) [abstract idea],
        │   │                   assignments_on(date)
        │   ├── FlightDeckCrew  licence number; qualified = holds a TYPE RATING on the type
        │   └── CabinCrew       languages; qualified = holds a CABIN-TYPE (SEP) qualification
        ├── MaintenanceEngineer authorisation category (B1/B2); can_certify(type)
        └── GroundStaff         department (dispatch, ramp, check-in, cargo, ops control)
```

**Person → Employee / Passenger.** Identity documents belong to the person, not to the
booking or the job. The scenario's "travel-document problem after check-in" is checked
against `Person.documents()`, and the same lookup would serve an employee positioning as a
passenger. Date of birth is on Person because it drives infant status for passengers and
licence/medical rules for crew.

**Employee → CrewMember.** Everything about *being employed* (staff number, base, dated roles)
is shared by engineers, ground staff and crew, so it sits on Employee. What is specific to
*operating* crew - a daily duty limit, being out of position, being assignable to a flight -
sits on CrewMember. Putting `assignments_on()` on Employee would suggest engineers are rostered
onto flights, which they are not.

**CrewMember → FlightDeckCrew / CabinCrew.** Both are assigned to flights, both must be
qualified on the aircraft type, but *what "qualified" means differs*: a pilot needs a type
rating from the regulator; cabin crew need the airline's cabin/safety qualification on the
type. `qualified_for()` therefore exists at CrewMember level (crew assignment calls it without
caring which kind of crew it is) and is *implemented* in each subclass. This is exactly the
"correct job title but not the qualification" case: the title lives in `RoleAssignment`, the
qualification check lives here.

Why not one flat `Employee` with a `kind` field? Because `assign_crew` would need `if kind ==`
branches for the qualification rule, and nothing would stop a ground-staff record being
assigned as a captain.

## 2. TemporalRecord - records that are true for a period

```
Record
└── TemporalRecord              valid_from, valid_to, is_valid_at(t), end()
    ├── CabinConfiguration      a dated version of an aircraft's cabin
    ├── Component               a part installed on an airframe between two dates
    ├── AirportRestriction      a capacity cut that applies then disappears
    ├── AircraftAssignment      which airframe operates a flight, for a period
    ├── RoleAssignment          a job title held between dates
    ├── Qualification           a certificate that is valid then expires or is revoked
    ├── CrewAssignment          a crew member on a flight until released/replaced/cancelled
    ├── DutyPeriod              a rostered duty/rest/standby block
    ├── SeatAssignment          a seat held until superseded
    └── HandlingRequirement     a cargo requirement from the moment it was declared
```

This is the hierarchy that makes *historical correctness* a property of the model rather than
of each operation. Every "what was true at 05:30?" query in the demos
(`configuration_at`, `aircraft_at`, `role_at`, `restrictions_at`, `requirements(at=)`)
is one `is_valid_at()` call. If the validity fields were copied onto each class separately,
each would need its own `end()` logic and its own bugs.

The level is right because the shared behaviour is *only* the period. A cabin configuration
and a qualification have nothing else in common, and the hierarchy claims nothing more.

## 3. EngineeringRecord - entries in the aircraft's technical log

```
Record
└── EngineeringRecord           aircraft, raised_by (engineer), description, certified_by, closed_at, close()
    ├── Inspection              check type, findings (defects it raised)
    ├── Defect                  ATA chapter, component, grounding flag, MEL reference + deferral expiry
    └── WorkOrder               due time, estimated hours, linked defect
```

In the real world these are all tech-log entries with the same audit requirements: which
airframe, who raised it, who certified it, when it was closed. That is the shared part and it
sits on the parent. The children differ in lifecycle: an inspection is performed and closed;
a defect goes open → deferred/rectified (or grounds the aircraft); a work order is planned →
closed. A *deferred* defect is a status of Defect, not a subclass (see rejected.md #3).

## 4. Disruption - events ops control must decide on

```
Record
└── Disruption                  flight, reason code, declared_by/at, resolution, resolved_at,
    │                           affected[] (every record touched), options()
    ├── Delay                   minutes, knock_on flights
    ├── Cancellation            counts of the records preserved
    ├── Diversion               the airport actually landed at
    └── AircraftSubstitution    from/to aircraft, seats lost, cargo offloaded
```

The parent exists because the end-of-day explanation ("what changed, who was affected, and
why") treats them identically: `report.end_of_day()` iterates over `Disruption` and never
needs to know the subtype. `RecoveryOption` attaches to the parent, so *any* disruption can
have alternative choices recorded, which the "delayed inbound producing multiple valid
recovery choices" case requires. The children hold only what their recovery needs.

## What is deliberately *not* inherited

See `rejected.md`. In short: Bag and Consignment are not siblings; charter flights are not
a subclass of Flight; deferred defects are not a subclass of Defect; job titles are not
subclasses of Employee; Organisation is not a Person.
