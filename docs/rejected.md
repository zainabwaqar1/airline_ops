# Tempting inheritance relationships that were considered and rejected (item 7)

## 1. `Bag` and `Consignment` under a shared `CarriedItem` parent - rejected

Tempting because both have a weight, both are loaded on a flight, both can be offloaded and
both can have an irregularity. But:

* A bag has no contract of its own; it exists only because a `FlightSegment` exists and is
  carried free under the passenger's ticket. A consignment *is* a contract (the air waybill)
  between a shipper, an agent and the airline, with its own price and documentation.
* Their lifecycles differ: a bag follows its owner (offloading the passenger forces the bag
  off), while cargo is booked, tendered, accepted, held, loaded and delivered independently.
* Their irregularities differ: a `BaggageIrregularity` is a passenger-service claim (PIR);
  cargo problems are handling requirements and holds.

The only shared fields would be `weight_kg` and "currently on flight X". A parent with two
fields and no shared behaviour is the "similar-looking fields" trap the brief warns about.
Instead each has its own movement record (`BagMovement`, `CargoLoad`).

## 2. `CharterFlight(Flight)` - rejected

Tempting because charters have a customer, a negotiated passenger count and no public
bookings. But a charter flight still needs an aircraft, a crew that is qualified and
positioned, a dispatch release, and it can be delayed, substituted or diverted exactly like
a scheduled service (demo 8 diverts one). Subclassing `Flight` would force every operation
that touches flights to know about the subclass for no behavioural gain. The commercial
difference is captured by `ScheduledService.service_kind = "charter"` plus a separate
`CharterAgreement` record that has its own lifecycle (agreed → amended) and its own
amendment history.

## 3. `DeferredDefect(Defect)` - rejected

Tempting because a deferred defect carries extra data (MEL reference, deferral expiry,
certifying engineer). But deferral is a *state transition of the same defect*: it is raised
open, deferred, and later rectified - one record, three statuses. A subclass would require
either creating a new object at deferral time (breaking the tech-log identity `DEF-001`)
or mutating an object's class. The extra fields simply stay empty until deferral.

## 4. `Captain(FlightDeckCrew)`, `FirstOfficer(FlightDeckCrew)` etc. - rejected

Tempting because titles feel like "kinds of employee". But titles change over time
(demo 2 promotes a First Officer to Captain at 10:00) and the historical requirement is that
her 05:30 assignment still says First Officer. A subclass cannot change on promotion without
replacing the object and losing its history. Titles are therefore dated `RoleAssignment`
records, and the title held is frozen onto each `CrewAssignment` at the moment of assignment.

## 5. `Organisation` as a kind of `Person` (a shared `Party` parent) - rejected

Tempting because both can "book", "ship" or "handle". But a person has a date of birth,
nationality and travel documents; an organisation has none of those and is referenced only as
a counter-party (corporate account, shipper, agent, handler, airport authority). A `Party`
parent would carry nothing but a name.

## 6. `Seat` as a subclass of `TemporalRecord` - rejected

Seats do not have a validity period of their own; they exist as part of a configuration
version, and the *configuration* is the temporal record. Giving seats their own dates would
duplicate the configuration's dates on ~160 records per aircraft.
