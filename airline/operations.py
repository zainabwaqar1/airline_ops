"""
The business operations of the system.

Every public function here is one *meaningful* operation: it enforces at least
one business rule, changes status or creates linked records, and writes to the
history.  Refusals raise DomainError AND are logged, so a rejected attempt is
part of the day's story.

Functions take the registry first, then record ids or records (the API passes
ids; the demos pass objects).  `_r()` accepts either.

Operations are grouped by area; OPERATIONS at the bottom lists them for the
frontend and for the class/operation count in docs/tracker.md.
"""
from datetime import timedelta
from .core import DomainError, now, advance, fmt, Record
from .fleet import AircraftType, Aircraft, CabinConfiguration, Seat, Component
from .network import Airport, AirportRestriction, Route, ScheduledService, Flight, AircraftAssignment, FlightMovement
from .people import (Organisation, Passenger, Employee, CrewMember, FlightDeckCrew, CabinCrew,
                     MaintenanceEngineer, GroundStaff, RoleAssignment, Qualification, CrewAssignment, DutyPeriod)
from .commercial import Booking, FlightSegment, SeatAssignment, TravelDocument, CheckIn, SpecialServiceRequest, CharterAgreement
from .baggage import Bag, BagMovement, BaggageIrregularity
from .cargo import Consignment, HandlingRequirement, CargoLoad
from .maintenance import Inspection, Defect, WorkOrder
from .disruption import Disruption, Delay, Cancellation, Diversion, AircraftSubstitution, RecoveryOption


def _r(reg, x):
    """Accept a record or an id."""
    return x if isinstance(x, Record) or x is None else reg.get(x)


def _refuse(record, msg, actor="ops"):
    record.log("refused", msg, actor)
    raise DomainError(msg)


# ============================================================ FLEET
def register_aircraft(reg, registration, type_code, msn, cargo_capacity_kg, config_name, cabins):
    """Add an airframe to the fleet with its first cabin configuration."""
    actype = reg.one(AircraftType, code=type_code)
    ac = Aircraft(reg, registration, actype, msn, cargo_capacity_kg)
    cfg = CabinConfiguration(reg, ac, config_name, cabins)
    ac.log("registered", f"{actype.code} MSN {msn}, config {cfg.label()} {cfg.capacity()} seats")
    return ac


def reconfigure_cabin(reg, aircraft, config_name, cabins, actor="engineering"):
    """Replace the aircraft's cabin layout.  The old configuration is ENDED, not
    deleted; existing seat assignments keep pointing at the old version and are
    flagged for re-seating."""
    ac = _r(reg, aircraft)
    old = ac.current_configuration()
    old.end("superseded by new configuration", "superseded", actor)
    new = CabinConfiguration(reg, ac, config_name, cabins)
    ac.log("reconfigured", f"{old.label()} -> {new.label()} ({old.capacity()} -> {new.capacity()} seats)", actor)
    affected = 0
    for f in reg.all(Flight):
        if f.current_aircraft() is ac and f.status == "planned":
            affected += reseat_flight(reg, f, reason="cabin reconfiguration", actor=actor)
    return new, affected


def retire_aircraft(reg, aircraft, reason, actor="fleet_management"):
    """Retire an airframe.  Future flights planned on it lose their aircraft
    (assignment ended, flight status 'needs_aircraft') but remain planned."""
    ac = _r(reg, aircraft)
    ac.retired_at = now()
    ac.set_status("retired", reason, actor)
    orphaned = []
    for a in reg.all(AircraftAssignment):
        if a.aircraft is ac and a.is_current() and a.flight.status == "planned":
            a.end(f"aircraft retired: {reason}", "ended", actor)
            a.flight.set_status("needs_aircraft", f"{ac.registration} retired", actor)
            orphaned.append(a.flight)
    return orphaned


def install_component(reg, aircraft, part_number, serial_number, description, actor="engineering"):
    """Fit a serialised component to an aircraft."""
    ac = _r(reg, aircraft)
    c = Component(reg, ac, part_number, serial_number, description)
    c.log("installed", f"on {ac.registration}", actor)
    return c


def remove_component(reg, component, reason, actor="engineering"):
    """Remove a component; its installation period ends, its history stays."""
    c = _r(reg, component)
    c.end(reason, "removed", actor)
    return c


# ============================================================ NETWORK
def apply_airport_restriction(reg, airport, kind, description, capacity_factor, actor="airport_authority"):
    """The airport authority imposes a temporary restriction (weather, runway)."""
    apt = _r(reg, airport)
    r = AirportRestriction(reg, apt, kind, description, capacity_factor)
    r.log("imposed", f"{description} (capacity x{capacity_factor})", actor)
    return r


def lift_airport_restriction(reg, restriction, actor="airport_authority"):
    """End a restriction.  Historical queries still show it in force earlier."""
    r = _r(reg, restriction)
    r.end("restriction lifted", "lifted", actor)
    return r


def create_scheduled_service(reg, flight_number, origin, destination, dep_time, arr_time, days, kind="scheduled"):
    """Add a planned service to the timetable (scheduled or charter)."""
    o, d = _r(reg, origin), _r(reg, destination)
    route = reg.find(Route, origin=o, destination=d)
    route = route[0] if route else Route(reg, o, d, 0, o.country != d.country)
    svc = ScheduledService(reg, flight_number, route, dep_time, arr_time, days, kind)
    svc.log("published", f"{kind} service {svc.label()}")
    return svc


def create_flight(reg, service, date, aircraft=None, actor="scheduling"):
    """Instantiate a service on a date, optionally assigning an aircraft."""
    svc = _r(reg, service)
    f = Flight(reg, svc, date)
    f.log("created", f"from service {svc.label()}", actor)
    if aircraft is not None:
        assign_aircraft(reg, f, aircraft, "initial plan", actor)
    return f


def assign_aircraft(reg, flight, aircraft, reason, actor="ops_control"):
    """Put an airframe on a flight.  Refused if the aircraft is not in service
    or has a grounding defect."""
    f, ac = _r(reg, flight), _r(reg, aircraft)
    if not ac.is_available():
        _refuse(f, f"cannot assign {ac.registration}: status is {ac.status}", actor)
    if any(d.grounding and d.status == "open" for d in reg.all(Defect) if d.aircraft is ac):
        _refuse(f, f"cannot assign {ac.registration}: open grounding defect", actor)
    a = AircraftAssignment(reg, f, ac, reason)
    a.log("assigned", reason, actor)
    if f.status == "needs_aircraft":
        f.set_status("planned", f"aircraft {ac.registration} assigned", actor)
    return a


def substitute_aircraft(reg, flight, new_aircraft, reason, actor="ops_control"):
    """Swap the airframe on a flight.  Ends the old assignment, opens a new one,
    re-seats passengers whose seats no longer exist, offloads cargo that no
    longer fits, and records everything on an AircraftSubstitution."""
    f, new = _r(reg, flight), _r(reg, new_aircraft)
    old = f.current_aircraft()
    if old is new:
        _refuse(f, "substitute aircraft is the same as the current one", actor)
    for a in f.aircraft_assignments():
        if a.is_current():
            a.end(reason, "superseded", actor)
            old_assignment = a
    new_assignment = assign_aircraft(reg, f, new, f"substitution: {reason}", actor)
    old_assignment.superseded_by = new_assignment
    sub = AircraftSubstitution(reg, f, "TD", reason, actor, old, new)
    sub.touch(f); sub.touch(old); sub.touch(new)
    sub.seats_lost = reseat_flight(reg, f, reason=f"substitution to {new.registration}", actor=actor, disruption=sub)
    sub.cargo_offloaded_kg = _fit_cargo(reg, f, sub, actor)
    # the substitute may carry a maintenance requirement later in the day
    for wo in reg.all(WorkOrder):
        if wo.aircraft is new and wo.status == "planned" and wo.due_at.date() == f.date:
            sub.log("warning", f"{new.registration} has {wo.label()} - flight must be back by then", actor)
    sub.resolve(f"{old.registration} -> {new.registration}; {sub.seats_lost} pax re-seated; {sub.cargo_offloaded_kg} kg cargo offloaded")
    return sub


def reseat_flight(reg, flight, reason, actor="ops_control", disruption=None):
    """Re-seat every passenger whose seat does not exist in the flight's
    CURRENT configuration.  Old assignments are superseded, never edited."""
    f = _r(reg, flight)
    ac = f.current_aircraft()
    cfg = ac.current_configuration()
    valid = cfg.seat_numbers()
    taken = {sa.seat.number for sa in reg.all(SeatAssignment)
             if sa.segment.flight is f and sa.is_current() and sa.configuration is cfg}
    changed = 0
    for seg in f.segments():
        sa = seg.seat_assignment()
        if sa is None or sa.configuration is cfg:
            continue
        sa.end(reason, "superseded", actor)
        changed += 1
        if disruption:
            disruption.touch(seg)
        # keep the same seat number if it exists in the same cabin, else next free
        candidates = [sa.seat.number] + sorted(valid)
        for num in candidates:
            s = cfg.seat(num)
            if s and s.cabin_class == seg.cabin_class and num not in taken:
                assign_seat(reg, seg, num, f"re-seated: {reason}", actor)
                taken.add(num)
                break
        else:
            seg.set_status("seat_pending", f"no {seg.cabin_class} seat available after {reason}", actor)
    return changed


def _fit_cargo(reg, flight, disruption, actor):
    ac = flight.current_aircraft()
    loads = [l for l in reg.all(CargoLoad) if l.flight is flight and l.status in ("planned", "loaded")]
    total = sum(l.consignment.weight_kg for l in loads)
    offloaded = 0
    for l in sorted(loads, key=lambda l: -l.consignment.weight_kg):
        if total <= ac.cargo_capacity_kg:
            break
        offload_cargo(reg, l, f"exceeds capacity of {ac.registration}", actor)
        disruption.touch(l.consignment)
        total -= l.consignment.weight_kg
        offloaded += l.consignment.weight_kg
    return offloaded


def depart_flight(reg, flight, actor="dispatch"):
    """Off-blocks.  Creates the FlightMovement.  Refused without a full crew."""
    f = _r(reg, flight)
    positions = {c.position for c in f.crew_assignments()}
    if not {"CP", "FO", "SCCM"} <= positions:
        _refuse(f, f"cannot depart: crew incomplete {sorted(positions)}", actor)
    mv = FlightMovement(reg, f, f.current_aircraft())
    f.set_status("departed", f"actual {fmt(now())}", actor)
    for seg in f.segments():
        ci = seg.check_in()
        if ci and ci.status == "boarded":
            seg.set_status("flown", "", actor)
    return mv


def arrive_flight(reg, flight, actor="dispatch"):
    """On-blocks at the movement's actual destination."""
    f = _r(reg, flight)
    mv = f.movement()
    mv.actual_arrival = now()
    mv.set_status("landed", f"at {mv.actual_destination.iata}", actor)
    f.set_status("arrived", f"at {mv.actual_destination.iata} {fmt(now())}", actor)
    f.current_aircraft().location = mv.actual_destination
    return mv


# ============================================================ PEOPLE
def hire_employee(reg, kind, first_name, last_name, dob, nationality, staff_number, base, title, department, extra):
    """Create an employee of the right subclass and open their first role."""
    base = _r(reg, base)
    cls = {"flight_deck": FlightDeckCrew, "cabin": CabinCrew, "engineer": MaintenanceEngineer, "ground": GroundStaff}[kind]
    e = cls(reg, first_name, last_name, dob, nationality, staff_number, base, extra)
    role = RoleAssignment(reg, e, title, department)
    e.log("hired", f"as {title} in {department} at {base.iata}", "hr")
    return e


def change_role(reg, employee, new_title, department, actor="hr"):
    """Promote / move an employee.  The old RoleAssignment is ended and kept, so
    old crew assignments still show the title held at the time."""
    e = _r(reg, employee)
    old = e.current_role()
    if old:
        old.end(f"changed to {new_title}", "ended", actor)
    r = RoleAssignment(reg, e, new_title, department)
    e.log("role_change", f"{old.title if old else '-'} -> {new_title}", actor)
    return r


def grant_qualification(reg, employee, kind, subject_code, issued_by, expires=None, actor="training"):
    """Record a new type rating / cabin qualification / authorisation."""
    e = _r(reg, employee)
    q = Qualification(reg, e, kind, subject_code, issued_by, expires)
    q.log("granted", f"to {e.label()} by {issued_by}", actor)
    return q


def revoke_qualification(reg, qualification, reason, actor="training"):
    """End a qualification (expired, failed check).  Assignments made while it
    was valid remain valid history."""
    q = _r(reg, qualification)
    q.end(reason, "revoked", actor)
    return q


def roster_duty(reg, crew, kind, start, end, location, actor="crewing"):
    """Roster a duty / rest / standby block."""
    c = _r(reg, crew)
    d = DutyPeriod(reg, c, kind, start, end, _r(reg, location))
    d.log("rostered", "", actor)
    return d


def assign_crew(reg, flight, crew, position, actor="crewing"):
    """Assign a crew member.  Refused if not qualified on the flight's aircraft
    type, not positioned at the origin, or over the daily duty limit."""
    f, c = _r(reg, flight), _r(reg, crew)
    ac = f.current_aircraft()
    if ac is None:
        _refuse(f, "no aircraft assigned yet, cannot check crew qualification", actor)
    if not c.qualified_for(ac.aircraft_type):
        _refuse(f, f"{c.label()} holds title '{c.current_role().title}' but no {ac.aircraft_type.code} qualification", actor)
    # positioning: physically at the origin, or arriving there on an earlier sector of the same day
    arrives_there = any(a.flight.destination is f.origin and a.flight.sta <= f.std for a in c.assignments_on(f.date))
    if c.position_location is not f.origin and not arrives_there:
        _refuse(f, f"{c.label()} is positioned at {c.position_location.iata}, flight departs {f.origin.iata}", actor)
    for d in reg.all(DutyPeriod):
        if d.crew is c and d.kind in ("rest", "leave") and d.valid_from <= f.std < d.valid_to:
            _refuse(f, f"{c.label()} is on {d.kind} until {fmt(d.valid_to)}", actor)
    hours = sum((a.flight.sta - a.flight.std).total_seconds() / 3600 for a in c.assignments_on(f.date))
    hours += (f.sta - f.std).total_seconds() / 3600
    if hours > c.max_duty_hours:
        _refuse(f, f"{c.label()} would exceed {c.max_duty_hours}h duty ({hours:.1f}h)", actor)
    a = CrewAssignment(reg, f, c, position, c.current_role().title)
    a.log("assigned", f"as {position} ({a.role_title})", actor)
    return a


def release_crew(reg, assignment, reason, actor="crewing"):
    """Take a crew member off a flight.  The assignment stays as 'released'."""
    a = _r(reg, assignment)
    a.end(reason, "released", actor)
    return a


def swap_crew(reg, assignment, replacement, reason, actor="crewing"):
    """Replace one crew member with another in the same position.  All
    qualification checks in assign_crew apply to the replacement."""
    a = _r(reg, assignment)
    new = assign_crew(reg, a.flight, replacement, a.position, actor)   # may refuse
    a.end(reason, "replaced", actor)
    a.replaced_by = new
    return new


def position_crew(reg, crew, airport, reason, actor="crewing"):
    """Move a crew member (as passenger / by road) to another airport."""
    c, apt = _r(reg, crew), _r(reg, airport)
    c.log("positioned", f"{c.position_location.iata} -> {apt.iata}: {reason}", actor)
    c.position_location = apt
    return c


# ============================================================ COMMERCIAL
def create_booking(reg, locator, booked_by, email, corporate=None):
    """Open a PNR."""
    b = Booking(reg, locator, booked_by, email, _r(reg, corporate))
    b.log("created", f"by {booked_by}")
    return b


def add_segment(reg, booking, passenger, flight, cabin_class, fare, connecting_from=None):
    """Book a passenger onto a flight under a PNR.  Refused if the cabin is sold
    out on the current configuration."""
    b, p, f = _r(reg, booking), _r(reg, passenger), _r(reg, flight)
    ac = f.current_aircraft()
    if ac and cabin_class != "INF":
        cap = ac.current_configuration().capacity(cabin_class)
        sold = len([s for s in f.segments() if s.cabin_class == cabin_class])
        if sold >= cap:
            _refuse(b, f"{f.label()} cabin {cabin_class} is full ({cap})")
    seg = FlightSegment(reg, b, p, f, cabin_class, fare)
    b.total_fare += fare
    seg.log("booked", f"{cabin_class} fare {fare}")
    if connecting_from is not None:
        prev = _r(reg, connecting_from)
        prev.connecting_to = seg
        prev.log("connection", f"connects to {seg.flight.label()}")
    return seg


def assign_seat(reg, segment, seat_number, reason="passenger choice", actor="reservations"):
    """Give a segment a seat in the CURRENT configuration version."""
    seg = _r(reg, segment)
    cfg = seg.flight.current_aircraft().current_configuration()
    seat = cfg.seat(seat_number)
    if seat is None:
        _refuse(seg, f"seat {seat_number} does not exist in {cfg.label()}", actor)
    if seat.cabin_class != seg.cabin_class and seg.cabin_class != "INF":
        _refuse(seg, f"seat {seat_number} is {seat.cabin_class}, segment is {seg.cabin_class}", actor)
    for sa in reg.all(SeatAssignment):
        if sa.seat is seat and sa.is_current() and sa.segment.flight is seg.flight:
            _refuse(seg, f"seat {seat_number} already taken by {sa.segment.passenger.label()}", actor)
    old = seg.seat_assignment()
    if old:
        old.end("re-seated", "superseded", actor)
    sa = SeatAssignment(reg, seg, seat, reason)
    sa.log("assigned", reason, actor)
    return sa


def add_travel_document(reg, holder, kind, number, country, expires):
    """Attach a passport / visa to a person."""
    d = TravelDocument(reg, _r(reg, holder), kind, number, country, expires)
    d.log("recorded", "")
    return d


def add_special_service(reg, segment, code, detail, actor="reservations"):
    """Attach an SSR (INFT, WCHR, MEDA...) to a segment."""
    s = SpecialServiceRequest(reg, _r(reg, segment), code, detail)
    s.log("requested", detail, actor)
    return s


def check_in_passenger(reg, segment, agent=None, channel="counter", actor="check_in"):
    """Check in.  Refused for international flights without a valid document,
    or if the segment is not confirmed."""
    seg = _r(reg, segment)
    if seg.status != "confirmed":
        _refuse(seg, f"cannot check in: segment is {seg.status}", actor)
    if seg.flight.service.route.international:
        docs = [d for d in seg.passenger.documents() if d.status == "valid" and d.expires > seg.flight.date]
        if not docs:
            _refuse(seg, "international flight and no valid travel document on file", actor)
    ci = CheckIn(reg, seg, _r(reg, agent), channel)
    ci.boarding_pass_seq = len([c for c in reg.all(CheckIn) if c.segment.flight is seg.flight])
    seg.set_status("checked_in", f"seq {ci.boarding_pass_seq} via {channel}", actor)
    return ci


def board_passenger(reg, segment, actor="gate"):
    """Scan boarding pass at the gate."""
    seg = _r(reg, segment)
    ci = seg.check_in()
    if not ci or ci.status != "checked_in":
        _refuse(seg, "cannot board: not checked in", actor)
    ci.boarded_at = now()
    ci.set_status("boarded", "", actor)
    seg.set_status("boarded", "", actor)
    return ci


def offload_passenger(reg, segment, reason, actor="gate"):
    """Remove a checked-in passenger.  Check-in becomes 'offloaded' (kept), and
    any bag loaded for them must come off too (security rule)."""
    seg = _r(reg, segment)
    ci = seg.check_in()
    if not ci:
        _refuse(seg, "passenger is not checked in", actor)
    ci.offload_reason = reason
    ci.set_status("offloaded", reason, actor)
    seg.set_status("offloaded", reason, actor)
    bags = []
    for bag in reg.all(Bag):
        if bag.owner_segment is seg and bag.current_flight() is seg.flight:
            offload_bag(reg, bag, f"owner offloaded: {reason}", actor)
            bags.append(bag)
    return bags


def invalidate_document(reg, document, reason, actor="immigration"):
    """A document is found unacceptable after the fact."""
    d = _r(reg, document)
    d.set_status("invalid", reason, actor)
    return d


def rebook_segment(reg, segment, new_flight, reason, actor="customer_service"):
    """Move a passenger to another flight.  The original segment stays with
    status 'rebooked' and the two are linked both ways."""
    seg, nf = _r(reg, segment), _r(reg, new_flight)
    if seg.status in ("flown", "rebooked"):
        _refuse(seg, f"cannot rebook a segment that is {seg.status}", actor)
    new = add_segment(reg, seg.booking, seg.passenger, nf, seg.cabin_class, 0.0)
    new.rebooked_from = seg
    seg.rebooked_to = new
    seg.set_status("rebooked", f"-> {nf.label()}: {reason}", actor)
    return new


def change_cabin(reg, segment, new_class, reason, actor="customer_service"):
    """Downgrade / upgrade a passenger (e.g. business cabin no longer exists on
    the substitute aircraft).  The old cabin is kept in history for compensation."""
    seg = _r(reg, segment)
    old = seg.cabin_class
    seg.cabin_class = new_class
    seg.log("cabin_change", f"{old} -> {new_class}: {reason}", actor)
    if seg.status == "seat_pending":
        seg.set_status("confirmed", f"cabin changed to {new_class}", actor)
    return seg


def cancel_segment(reg, segment, reason, actor="customer_service"):
    """Cancel one passenger's segment (refund path)."""
    seg = _r(reg, segment)
    seg.set_status("cancelled", reason, actor)
    return seg


def create_charter_agreement(reg, customer, flight, passengers, price, actor="commercial"):
    """Sign a charter contract against a charter flight."""
    f = _r(reg, flight)
    if f.service.service_kind != "charter":
        _refuse(f, "charter agreement requires a charter service", actor)
    a = CharterAgreement(reg, _r(reg, customer), f, passengers, price)
    a.log("agreed", f"{passengers} pax at {price}", actor)
    return a


def amend_charter(reg, agreement, new_passengers, reason, actor="commercial"):
    """Customer changes passenger numbers.  Refused above aircraft capacity;
    every amendment is appended, never overwritten."""
    a = _r(reg, agreement)
    cap = a.flight.current_aircraft().current_configuration().capacity()
    if new_passengers > cap:
        _refuse(a, f"{new_passengers} pax exceeds capacity {cap} of {a.flight.current_aircraft().registration}", actor)
    a.amendments.append({"at": now().isoformat(), "from": a.agreed_passengers, "to": new_passengers, "reason": reason})
    a.log("amended", f"{a.agreed_passengers} -> {new_passengers} pax: {reason}", actor)
    a.agreed_passengers = new_passengers
    a.set_status("amended", reason, actor)
    return a


# ============================================================ BAGGAGE
def accept_bag(reg, segment, tag, weight_kg, accepted_by, actor="check_in"):
    """Accept a checked bag and plan it on the owner's flight."""
    seg = _r(reg, segment)
    if seg.status not in ("checked_in", "boarded"):
        _refuse(seg, "bags can only be accepted from a checked-in passenger", actor)
    bag = Bag(reg, tag, seg, weight_kg, _r(reg, accepted_by))
    bag.log("accepted", f"{weight_kg} kg for {seg.flight.label()}", actor)
    load_bag(reg, bag, seg.flight, accepted_by, "owner's flight", actor)
    return bag


def load_bag(reg, bag, flight, handler, reason, actor="ramp"):
    """Load a bag on a flight (a BagMovement).  Warns when the routing differs
    from the owner's flight."""
    bag, f = _r(reg, bag), _r(reg, flight)
    m = BagMovement(reg, bag, f, _r(reg, handler), reason)
    if f is not bag.owner_segment.flight:
        m.log("warning", f"bag routing {f.label()} differs from owner's {bag.owner_segment.flight.label()}", actor)
    bag.set_status("loaded", f"on {f.label()}", actor)
    return m


def offload_bag(reg, bag, reason, actor="ramp"):
    """Take a bag off its current flight."""
    bag = _r(reg, bag)
    for m in bag.movements():
        if m.status == "loaded":
            m.offloaded_at = now()
            m.set_status("offloaded", reason, actor)
    bag.set_status("offloaded", reason, actor)
    return bag


def reroute_bag(reg, bag, new_flight, reason, actor="baggage_services"):
    """Send a bag on a different flight from its owner (missed connection,
    mis-sort).  History shows every flight it touched."""
    offload_bag(reg, bag, reason, actor)
    return load_bag(reg, bag, new_flight, None, reason, actor)


def report_bag_irregularity(reg, bag, kind, description, airport, reported_by, actor="baggage_services"):
    """Raise a PIR."""
    pir = BaggageIrregularity(reg, _r(reg, bag), kind, description, _r(reg, airport), reported_by)
    pir.log("raised", description, actor)
    pir.bag.set_status(f"irregular_{kind}", description, actor)
    return pir


def resolve_bag_irregularity(reg, pir, resolution, actor="baggage_services"):
    """Close a PIR with an outcome (repaired, compensated, delivered)."""
    p = _r(reg, pir)
    p.resolution = resolution
    p.set_status("closed", resolution, actor)
    return p


# ============================================================ CARGO
def book_consignment(reg, awb, shipper, agent, description, pieces, weight_kg, origin, destination):
    """Book a shipment under an air waybill."""
    c = Consignment(reg, awb, _r(reg, shipper), _r(reg, agent), description, pieces, weight_kg, _r(reg, origin), _r(reg, destination))
    c.log("booked", f"{pieces} pcs {weight_kg} kg {c.origin.iata}-{c.destination.iata}")
    return c


def declare_handling(reg, consignment, code, detail, declared_by, actor="cargo"):
    """Attach a handling requirement (PER, DGR...).  Dated, so the record shows
    when the airline learned of it - possibly AFTER acceptance."""
    c = _r(reg, consignment)
    h = HandlingRequirement(reg, c, code, detail, declared_by)
    h.log("declared", f"{detail} by {declared_by}", actor)
    if c.accepted_at and code == "DGR":
        c.set_status("held", f"DGR declared after acceptance: {detail}", actor)
        load = c.current_load()
        if load and load.flight.service.service_kind != "cargo":
            offload_cargo(reg, load, "dangerous goods require re-check before uplift", actor)
    return h


def accept_consignment(reg, consignment, accepted_by, flight, actor="cargo"):
    """Freight agent tenders, airline accepts, and plans the uplift.  Refused if
    the flight's aircraft cannot take the weight."""
    c, f = _r(reg, consignment), _r(reg, flight)
    ac = f.current_aircraft()
    planned = sum(l.consignment.weight_kg for l in reg.all(CargoLoad) if l.flight is f and l.status in ("planned", "loaded"))
    if planned + c.weight_kg > ac.cargo_capacity_kg:
        _refuse(c, f"{c.weight_kg} kg exceeds remaining capacity on {f.label()} ({ac.cargo_capacity_kg - planned} kg)", actor)
    c.accepted_at = now()
    c.accepted_by = _r(reg, accepted_by)
    c.set_status("accepted", f"by {c.accepted_by.label()}", actor)
    load = CargoLoad(reg, c, f, actor)
    load.log("planned", f"{c.weight_kg} kg", actor)
    return load


def load_cargo(reg, load, actor="ramp"):
    """Physically load a planned consignment.  Refused if it is held."""
    l = _r(reg, load)
    if l.consignment.status == "held":
        _refuse(l, f"{l.consignment.label()} is held and cannot be loaded", actor)
    l.loaded_at = now()
    l.set_status("loaded", "", actor)
    l.consignment.set_status("loaded", f"on {l.flight.label()}", actor)
    return l


def offload_cargo(reg, load, reason, actor="ramp"):
    """Remove a consignment from a flight; it returns to 'accepted' awaiting re-plan."""
    l = _r(reg, load)
    l.offloaded_at = now()
    l.offload_reason = reason
    l.set_status("offloaded", reason, actor)
    if l.consignment.status != "held":
        l.consignment.set_status("accepted", f"offloaded from {l.flight.label()}: {reason}", actor)
    return l


def deliver_consignment(reg, consignment, consignee_signature, actor="cargo"):
    """Hand over at destination."""
    c = _r(reg, consignment)
    c.set_status("delivered", f"signed {consignee_signature}", actor)
    return c


# ============================================================ MAINTENANCE
def record_inspection(reg, aircraft, engineer, check_type, description, actor="engineering"):
    """Log a check on an aircraft."""
    i = Inspection(reg, _r(reg, aircraft), _r(reg, engineer), description, check_type)
    i.log("performed", description, actor)
    return i


def raise_defect(reg, aircraft, engineer, description, ata_chapter, grounding, inspection=None, component=None, actor="engineering"):
    """Write a defect in the tech log.  A grounding defect makes the aircraft AOG."""
    ac = _r(reg, aircraft)
    d = Defect(reg, ac, _r(reg, engineer), description, ata_chapter, _r(reg, component), _r(reg, inspection))
    d.grounding = grounding
    d.log("raised", description, actor)
    if inspection is not None:
        d.inspection.findings.append(d)
    if grounding:
        ac.set_status("aog", f"grounding defect {d.id}", actor)
    return d


def escalate_defect(reg, defect, engineer, note, actor="engineering"):
    """Engineering decides a defect first logged as minor actually grounds the
    aircraft.  The defect keeps its id and history; the aircraft becomes AOG."""
    d, e = _r(reg, defect), _r(reg, engineer)
    d.grounding = True
    d.log("escalated", f"{note} (by {e.label()})", actor)
    d.aircraft.set_status("aog", f"grounding defect {d.id}: {note}", actor)
    return d


def defer_defect(reg, defect, mel_reference, days, engineer, actor="engineering"):
    """Defer under the MEL.  Refused for a grounding defect or by an engineer
    without certifying authority on the type."""
    d, e = _r(reg, defect), _r(reg, engineer)
    if d.grounding:
        _refuse(d, "grounding defect cannot be deferred", actor)
    if not e.can_certify(d.aircraft.aircraft_type):
        _refuse(d, f"{e.label()} cannot certify on {d.aircraft.aircraft_type.code}", actor)
    d.mel_reference = mel_reference
    d.deferral_expires = now() + timedelta(days=days)
    d.certified_by = e
    d.set_status("deferred", f"MEL {mel_reference} until {d.deferral_expires:%d %b}", actor)
    return d


def rectify_defect(reg, defect, engineer, note, actor="engineering"):
    """Fix and certify.  If it was the last grounding defect, aircraft returns to service."""
    d, e = _r(reg, defect), _r(reg, engineer)
    if not e.can_certify(d.aircraft.aircraft_type):
        _refuse(d, f"{e.label()} cannot certify on {d.aircraft.aircraft_type.code}", actor)
    d.close(e, note)
    d.set_status("rectified", note, actor)
    ac = d.aircraft
    if ac.status == "aog" and not any(x.grounding and x.status == "open" for x in reg.all(Defect) if x.aircraft is ac):
        ac.set_status("in_service", f"returned to service after {d.id}", actor)
    return d


def open_work_order(reg, aircraft, engineer, description, due_at, hours, defect=None, actor="engineering"):
    """Plan maintenance work."""
    w = WorkOrder(reg, _r(reg, aircraft), _r(reg, engineer), description, due_at, hours, _r(reg, defect))
    w.log("opened", f"due {due_at:%H:%M}", actor)
    return w


def complete_work_order(reg, work_order, engineer, note, actor="engineering"):
    """Close a work order and certify it."""
    w = _r(reg, work_order)
    w.close(_r(reg, engineer), note)
    return w


# ============================================================ DISRUPTION
def declare_delay(reg, flight, minutes, reason_code, description, actor="ops_control"):
    """Delay a flight; identify knock-on flights sharing its aircraft or crew,
    and connecting passengers at risk."""
    f = _r(reg, flight)
    d = Delay(reg, f, reason_code, description, actor, minutes)
    f.etd = f.etd + timedelta(minutes=minutes)
    f.eta = f.eta + timedelta(minutes=minutes)
    f.set_status("delayed", f"+{minutes} min {reason_code}: {description}", actor)
    d.touch(f)
    ac = f.current_aircraft()
    crew_ids = {c.crew.id for c in f.crew_assignments()}
    for other in reg.all(Flight):
        if other is f or other.date != f.date or other.std <= f.std or other.status not in ("planned", "delayed"):
            continue
        same_ac = other.current_aircraft() is ac
        same_crew = any(c.crew.id in crew_ids for c in other.crew_assignments())
        if (same_ac or same_crew) and other.std < f.eta + timedelta(minutes=45):
            d.knock_on.append(other)
            d.touch(other)
            other.log("threatened", f"by delay of {f.label()} ({'aircraft' if same_ac else 'crew'} rotation)", actor)
    for seg in f.segments():
        nxt = seg.connecting_to
        if nxt and nxt.flight.etd < f.eta + timedelta(minutes=60):
            d.touch(seg)
            seg.log("connection_at_risk", f"arrives {fmt(f.eta)}, {nxt.flight.label()} departs {fmt(nxt.flight.etd)}", actor)
    d.resolve(f"ETD {fmt(f.etd)}; {len(d.knock_on)} knock-on flight(s)")
    return d


def propose_recovery(reg, disruption, description, cost, passengers_affected, actor="ops_control"):
    """Record one candidate recovery choice for a disruption."""
    o = RecoveryOption(reg, _r(reg, disruption), description, cost, passengers_affected)
    o.log("proposed", description, actor)
    return o


def choose_recovery(reg, option, decided_by, actor="ops_control"):
    """Pick one option; siblings become 'rejected' but stay visible."""
    o = _r(reg, option)
    for sib in o.disruption.options():
        if sib is not o and sib.status == "proposed":
            sib.set_status("rejected", f"chose {o.id}", actor)
    o.decided_by = decided_by
    o.set_status("chosen", f"by {decided_by}", actor)
    o.disruption.resolve(o.description)
    return o


def cancel_flight(reg, flight, reason_code, description, actor="ops_control"):
    """Cancel.  Every dependent record is set to a cancelled status and KEPT;
    the Cancellation stores counts so finance/ops history stays readable."""
    f = _r(reg, flight)
    if f.status in ("departed", "arrived", "cancelled"):
        _refuse(f, f"cannot cancel a flight that is {f.status}", actor)
    c = Cancellation(reg, f, reason_code, description, actor)
    kept = {"segments": 0, "crew_assignments": 0, "bags": 0, "cargo_loads": 0, "seat_assignments": 0}
    for seg in f.segments(active_only=False):
        if seg.status in ("confirmed", "checked_in", "boarded", "seat_pending"):
            seg.set_status("cancelled_flight", description, actor); kept["segments"] += 1; c.touch(seg)
            sa = seg.seat_assignment()
            if sa:
                sa.end("flight cancelled", "cancelled", actor); kept["seat_assignments"] += 1
    for ca in f.crew_assignments():
        ca.end("flight cancelled", "cancelled", actor); kept["crew_assignments"] += 1; c.touch(ca.crew)
    for bag in reg.all(Bag):
        if bag.current_flight() is f:
            offload_bag(reg, bag, "flight cancelled", actor); kept["bags"] += 1; c.touch(bag)
    for l in reg.all(CargoLoad):
        if l.flight is f and l.status in ("planned", "loaded"):
            offload_cargo(reg, l, "flight cancelled", actor); kept["cargo_loads"] += 1; c.touch(l.consignment)
    for a in f.aircraft_assignments():
        if a.is_current():
            a.end("flight cancelled", "cancelled", actor)
    c.records_preserved = kept
    f.set_status("cancelled", f"{reason_code}: {description}", actor)
    c.resolve(f"cancelled; preserved {kept}")
    return c


def divert_flight(reg, flight, new_airport, reason_code, description, actor="captain"):
    """Land somewhere other than planned.  Changes the movement, not the plan."""
    f, apt = _r(reg, flight), _r(reg, new_airport)
    mv = f.movement()
    if mv is None:
        _refuse(f, "cannot divert a flight that has not departed", actor)
    d = Diversion(reg, f, reason_code, description, actor, apt)
    mv.actual_destination = apt
    mv.log("diverted", f"{mv.planned_destination.iata} -> {apt.iata}: {description}", actor)
    f.set_status("diverted", f"to {apt.iata}", actor)
    for seg in f.segments():
        d.touch(seg)
    d.resolve(f"landed {apt.iata}")
    return d


# ============================================================ REPORTING
def what_was_true_at(reg, t):
    """Historical query: every temporal record in force at time t."""
    from .core import TemporalRecord
    return [r for r in reg.all(TemporalRecord) if r.is_valid_at(t)]


# ---------------------------------------------------------------------------
# Catalogue used by the frontend and the docs.  (name, area, description)
# ---------------------------------------------------------------------------
OPERATIONS = {
    "Fleet": [register_aircraft, reconfigure_cabin, retire_aircraft, install_component, remove_component],
    "Network": [apply_airport_restriction, lift_airport_restriction, create_scheduled_service, create_flight,
                assign_aircraft, substitute_aircraft, reseat_flight, depart_flight, arrive_flight],
    "People": [hire_employee, change_role, grant_qualification, revoke_qualification, roster_duty,
               assign_crew, release_crew, swap_crew, position_crew],
    "Commercial": [create_booking, add_segment, assign_seat, add_travel_document, add_special_service,
                   check_in_passenger, board_passenger, offload_passenger, invalidate_document,
                   rebook_segment, change_cabin, cancel_segment, create_charter_agreement, amend_charter],
    "Baggage": [accept_bag, load_bag, offload_bag, reroute_bag, report_bag_irregularity, resolve_bag_irregularity],
    "Cargo": [book_consignment, declare_handling, accept_consignment, load_cargo, offload_cargo, deliver_consignment],
    "Maintenance": [record_inspection, raise_defect, escalate_defect, defer_defect, rectify_defect, open_work_order, complete_work_order],
    "Disruption": [declare_delay, propose_recovery, choose_recovery, cancel_flight, divert_flight],
}
