# Limitations and what would change at larger scale or under a different business model (item 10)

## Limitations of the current model

1. **In-memory only.** The registry is a dictionary; restarting the server rebuilds the seed.
   A real system would persist every record and event. The design already separates "what
   happened" (events) from "current state" (statuses), which is the shape an event-sourced
   store needs.
2. **Crew position is not inferred from flown sectors.** `position_location` changes only via
   `position_crew`; availability for a later sector is judged by "arrives there on an earlier
   sector today". After a cancellation the crew's true location can drift from the model.
3. **Duty rules are a single 13-hour daily cap plus rest/leave blocks.** Real flight-time
   limitations depend on report time, number of sectors, acclimatisation and cumulative
   fortnightly/monthly hours.
4. **Cargo is weight only.** No volume, ULD build-up, weight-and-balance, or dangerous-goods
   segregation rules; DGR simply places a hold.
5. **Connections are checked with a fixed 60-minute margin**, not airport-specific minimum
   connection times or domestic/international differences.
6. **Money is minimal.** Fares and charter prices are stored; there is no ticketing, refund,
   compensation or invoicing model, although every record needed to compute them survives.
7. **One person is one role in life.** An employee who travels as a passenger needs a separate
   `Passenger` record; a `Party` abstraction was rejected as premature (rejected.md #5).
8. **Aircraft types are flat.** Variants (A320-200 vs A320neo) and common type ratings are
   not modelled; a rating is matched on the exact type code.
9. **No concurrency or permissions.** Actors are free-text labels on events, not authenticated
   users with roles.

## If the airline became significantly larger

* **Hub-and-spoke network with hundreds of daily flights.** `declare_delay` scans all flights
  to find knock-ons; it would need an explicit *rotation* record (the planned sequence of
  sectors for one airframe and one crew) so knock-on detection is a lookup, not a scan.
  Rotations would become their own class, which the current `AircraftAssignment` and
  `CrewAssignment` already point toward.
* **Multiple bases and crew pools.** `DutyPeriod` would grow into a full roster with report
  times, and the qualification model would need recurrent-training expiry dates enforced by
  a scheduler rather than checked at assignment.
* **Many aircraft types and sub-fleets.** Type ratings would map to *licence endorsements*
  covering families; `qualified_for` would consult a rating-to-type table.
* **Multiple ground handlers per airport.** `Organisation(kind="handler")` is already used as
  an actor; contracts (which handler serves which station for which service) would become a
  dated `HandlingAgreement`.
* **Regulatory reporting.** The journal already records who did what and when; it would need
  immutable storage and retention rules.

## If the business model changed

* **Cargo-only carrier.** `Flight` would keep working; `Booking`/`FlightSegment`/`Seat` would
  become unused, and the cargo side would need ULD positions, volumetric capacity, multi-leg
  routing (`CargoLoad` per leg is already the shape), customs status and a manifest record.
* **Low-cost point-to-point.** Connections and rebooking protection would matter less; ancillary
  charges (bags, seats) would attach to `FlightSegment`; `SpecialServiceRequest` stays.
* **Wet-leasing aircraft and crew from another operator.** `Aircraft` and `CrewMember` would
  need an operator/owner organisation and a lease period (a `TemporalRecord`), and
  qualification checks would defer to the lessor's records.
* **Codeshares and interline partners.** A `Flight` would need a marketing vs operating
  carrier distinction and `FlightSegment` a marketing flight number, which is a second
  service record pointing at the same operating flight rather than a new hierarchy.
