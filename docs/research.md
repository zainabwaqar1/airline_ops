# Domain research summary (item 1) - YOU MUST COMPLETE THIS FILE

The code was designed around the concepts below. For each research area the brief lists,
write 3-6 sentences on what you learned and cite where you read it. Suggested starting
points are given, but the sources you cite must be ones you actually consulted.

## Sources consulted

| # | Source | What it was used for |
|---|---|---|
| 1 | *e.g.* IATA Airport Handling Manual (AHM) overview page | baggage, PIR, handler responsibilities |
| 2 | *e.g.* ICAO Annex 6 summary / national CAA flight-time limitations page | duty limits, rest, type ratings |
| 3 | *e.g.* an MEL explainer from an airline or regulator | deferred defects, MEL categories |
| 4 | *e.g.* IATA Dangerous Goods Regulations overview | DGR, UN numbers, lithium batteries |
| 5 | *e.g.* an IROPS / disruption-management article | delay reason codes, recovery options |
| 6 | ... | ... |

## Research areas (one paragraph each - write these yourself)

1. **Commercial flight lifecycle from planning through post-flight closure** -
2. **Aircraft type vs individual aircraft and configuration changes** -
3. **Crew roles, qualifications, duty limitations and positioning** -
4. **Scheduled, charter, passenger and cargo operations** -
5. **Maintenance checks, defects, deferred defects, return to service** -
6. **Booking, check-in, boarding, rebooking, special-service requests** -
7. **Baggage handling and irregular baggage** -
8. **Air cargo, dangerous/special cargo, shipment documentation** -
9. **Delays, cancellation, diversion, substitution, disruption recovery** -
10. **Airport operational constraints and airline vs airport responsibilities** -

## Glossary of terms used in the code

| Term | Meaning | Where it appears |
|---|---|---|
| Aircraft type | Certified design (A320-200). Ratings and MEL attach to it | `AircraftType` |
| Registration / tail number | Identity of one airframe (AP-BHA) | `Aircraft.registration` |
| MSN | Manufacturer serial number | `Aircraft.msn` |
| Cabin configuration | Layout of seats by class; can change over an airframe's life | `CabinConfiguration` |
| Scheduled service | Timetable entry: flight number, route, times, days | `ScheduledService` |
| Flight / sector / leg | One operation of a service on a date | `Flight` |
| STD / STA / ETD / ETA | Scheduled and estimated departure/arrival times | `Flight` |
| Off-blocks / on-blocks | Actual movement times | `FlightMovement` |
| Rotation | Sequence of sectors flown by one aircraft/crew in a day | assumed in `assign_crew` positioning |
| Type rating | Regulator-issued pilot qualification for one aircraft type | `Qualification(kind="type_rating")` |
| SEP / cabin-type qualification | Cabin crew safety qualification per type | `Qualification(kind="cabin_type")` |
| Certifying staff (B1/B2) | Engineers licensed to certify work on a type | `MaintenanceEngineer`, `Qualification(kind="certifying")` |
| CP / FO / SCCM / CC | Captain, First Officer, Senior Cabin Crew Member, Cabin Crew | `CrewAssignment.position` |
| FTL / duty period | Flight-time limitations; the rostered duty and rest blocks | `CrewMember.max_duty_hours`, `DutyPeriod` |
| Positioning / deadheading | Moving crew to where a flight departs | `position_crew` |
| PNR / record locator | Booking reference | `Booking.locator` |
| Segment | One passenger on one flight | `FlightSegment` |
| SSR (INFT, WCHR, MEDA, UMNR) | Special service request codes | `SpecialServiceRequest` |
| Offload | Removing a checked-in passenger or their bag before departure | `offload_passenger`, `offload_bag` |
| Bag tag | Baggage identifier printed at check-in | `Bag.tag` |
| PIR | Property Irregularity Report for damaged/delayed/lost bags | `BaggageIrregularity` |
| AWB | Air waybill: the cargo contract and shipment document | `Consignment.awb_number` |
| Freight agent / forwarder | Organisation that tenders cargo on behalf of the shipper | `Organisation(kind="freight_agent")` |
| PER / DGR / AVI / VAL | Special handling codes: perishable, dangerous goods, live animals, valuables | `HandlingRequirement.code` |
| UN3480 | UN number for lithium-ion batteries (dangerous goods) | demo 6 |
| Tech log | The aircraft's technical log of inspections, defects and work | `EngineeringRecord` |
| ATA chapter | Standard numbering of aircraft systems (29 hydraulics, 49 APU) | `Defect.ata_chapter` |
| MEL | Minimum Equipment List: what may be deferred and for how long | `defer_defect` |
| AOG | Aircraft on ground: unserviceable | `Aircraft.status = "aog"` |
| Work order | Planned maintenance task with a due time | `WorkOrder` |
| Delay codes (TD, WX, CR, RA) | Technical, weather, crew, reactionary (knock-on) | `Disruption.reason_code` |
| Diversion | Landing at an airport other than the planned destination | `Diversion`, `FlightMovement.actual_destination` |
| Substitution / aircraft change | Replacing the planned airframe | `AircraftSubstitution` |
| IROPS | Irregular operations: the whole disruption-recovery activity | `disruption.py` |
| Charter agreement | Contract with one customer for a whole flight | `CharterAgreement` |
| Airport authority / handler | Owns the airport's restrictions; third party doing ramp/baggage work | `Airport.operator`, `Organisation(kind="handler")` |
