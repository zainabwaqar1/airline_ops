# Integrated Airline Operations & Disruption Recovery

OOP project, Problem 1. A Python class model (the graded part) with a JavaScript
web console on top of it. **No installs are needed**: only Python 3.9+ and a browser.

---

## 1. Where everything goes

Open the whole `airline_ops` folder in Cursor (File → Open Folder). Keep this layout exactly:

```
airline_ops/
├── README.md                ← this file
├── main.py                  ← run the whole day in the terminal (no browser)
├── server.py                ← starts the web server for the JavaScript console
│
├── airline/                 ← THE PYTHON MODEL (submission item 5)
│   ├── __init__.py
│   ├── core.py              Record, TemporalRecord, Event, Registry, DomainError
│   ├── fleet.py             AircraftType, Aircraft, CabinConfiguration, Seat, Component
│   ├── network.py           Airport, AirportRestriction, Route, ScheduledService, Flight,
│   │                        AircraftAssignment, FlightMovement
│   ├── people.py            Organisation, Person → Passenger / Employee → CrewMember →
│   │                        FlightDeckCrew / CabinCrew, MaintenanceEngineer, GroundStaff,
│   │                        RoleAssignment, Qualification, CrewAssignment, DutyPeriod
│   ├── commercial.py        Booking, FlightSegment, SeatAssignment, TravelDocument, CheckIn,
│   │                        SpecialServiceRequest, CharterAgreement
│   ├── baggage.py           Bag, BagMovement, BaggageIrregularity
│   ├── cargo.py             Consignment, HandlingRequirement, CargoLoad
│   ├── maintenance.py       EngineeringRecord → Inspection / Defect / WorkOrder
│   ├── disruption.py        Disruption → Delay / Cancellation / Diversion / AircraftSubstitution,
│   │                        RecoveryOption
│   ├── operations.py        the 61 business operations (item 5)
│   ├── seed.py              the seeded operating day (item 8)
│   ├── demos.py             the 8 scenario demonstrations (item 9)
│   ├── report.py            end-of-day explanation
│   └── meta.py              introspection: class list, inheritance tree, operation list
│
├── frontend/                ← THE JAVASCRIPT CONSOLE
│   ├── index.html           the page skeleton (tabs and empty boxes)
│   ├── styles.css           how it looks
│   └── app.js               how it behaves (talks to server.py, fills the boxes)
│
└── docs/                    ← WRITTEN SUBMISSION ITEMS
    ├── tracker.md           checklist of every requirement → where it is satisfied
    ├── research.md          domain-research summary + glossary (item 1)  [needs your sources]
    ├── assumptions.md       assumptions and answers to the open questions (item 2)
    ├── requirements.md      requirements interpretation: records, workflows, lifecycles (item 3)
    ├── class_diagram.md     Mermaid class diagram (item 4)
    ├── inheritance.md       every inheritance relationship justified (item 6)
    ├── rejected.md          tempting hierarchies that were rejected (item 7)
    └── limitations.md       limitations and scaling discussion (item 10)
```

## 2. How to run it

### Option A - terminal only (fastest way to see everything)

In Cursor open a terminal (Terminal → New Terminal), make sure you are inside the
`airline_ops` folder, and run:

```
python main.py
```

It seeds the day, runs all eight scenarios in order, prints each one, then prints the
end-of-day report and the class/operation counts.

### Option B - the web console

```
python server.py
```

Then open **http://localhost:8000** in your browser. Press **Run full day** at the top
right. The tabs:

| Tab | What it shows |
|---|---|
| Overview | counters, flight board, fleet board (click a row to open the record) |
| Records | every class, every record, and the full history of any record you click |
| Operations | a form for each of the 61 operations; refusals are shown in red |
| Scenarios | the 8 demonstrations, run individually or all in order |
| Journal | every history event of the day, filterable |
| End-of-day report | what changed, who was affected, why; refused attempts; open items |
| Design | the inheritance tree and class/operation catalogue, read live from the Python code |

Stop the server with Ctrl+C in the terminal.

(On some computers the command is `python3` instead of `python`.)

## 3. How the two halves fit together

```
 browser  ──HTTP──▶  server.py  ──calls──▶  airline/operations.py  ──changes──▶  airline/*.py records
 (app.js)           (JSON in/out)                                                   (in memory)
```

* `app.js` never contains business logic. It only sends requests such as
  `POST /api/op/assign_seat {segment: "SEG-001", seat_number: "5A"}` and displays what
  comes back.
* `server.py` converts the JSON to Python arguments and calls the operation.
* Every rule, status change and history event lives in the `airline` package, which is why
  `main.py` can produce the whole demonstration without a browser at all.

## 4. What you still have to do yourself

1. **docs/research.md** - the sources and the glossary must be *your* research. The file has
   the structure and the terms the code uses; fill in what you read and where.
2. Read `docs/assumptions.md`, `docs/inheritance.md` and `docs/rejected.md` and make sure you
   agree with every decision - you will be asked to defend them.
3. Re-read `docs/tracker.md` before submitting and tick each line.

## 5. Design rules in one paragraph

Nothing is ever deleted: every record has a `status` and an `events` list, and every change
is written to the registry-wide journal. Anything that is true only for a period (a cabin
configuration, a qualification, a job title, a crew or aircraft or seat assignment, an
airport restriction) extends `TemporalRecord` with `valid_from` / `valid_to`, so the model can
always answer "what was true at 05:30?". Replacing something ends the old record and creates
a new one linked to it (`superseded_by`, `replaced_by`, `rebooked_to`). Business rules that
refuse an action log the refusal on the record, so rejected attempts are part of the history.
