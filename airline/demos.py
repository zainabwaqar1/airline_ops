"""
Scenario demonstrations (submission item 9).  Each demo is a normal workflow
that is interrupted by an exception, a dependency, or an operational conflict.
They are designed to run IN ORDER on one seeded day, and every one ends by
proving that the history is still readable.

Each function receives the registry and the seed handles and returns a Story:
a list of (time, kind, text) lines.  kind is one of
  step      something happened
  refused   a business rule rejected an attempt (this is on purpose)
  check     a historical query proving records survived
"""
from datetime import date
from .core import DomainError, now, set_clock, advance, fmt
from .seed import T
from . import operations as op
from .people import CrewAssignment, RoleAssignment
from .commercial import SeatAssignment
from .network import AirportRestriction
from .cargo import CargoLoad


class Story(list):
    def step(self, text):
        self.append({"time": fmt(now()), "kind": "step", "text": text})

    def check(self, text):
        self.append({"time": fmt(now()), "kind": "check", "text": text})

    def attempt(self, fn, *args, **kw):
        """Run an operation that is EXPECTED to be refused; record the refusal."""
        try:
            result = fn(*args, **kw)
            self.append({"time": fmt(now()), "kind": "step", "text": f"(unexpectedly accepted) {fn.__name__}"})
            return result
        except DomainError as e:
            self.append({"time": fmt(now()), "kind": "refused", "text": str(e)})
            return None


# ---------------------------------------------------------------------------
def demo_aircraft_substitution(reg, h):
    """05:30 LHE-KHI: defect on pre-departure check, aircraft changes twice, seats and cargo re-planned."""
    s = Story()
    F, ac, E = h["F"], h["ac"], h["E"]
    set_clock(T(4, 45))
    ins = op.record_inspection(reg, ac["BHA"], E["mehmood"], "pre_departure", "Pre-departure check for PK301")
    d = op.raise_defect(reg, ac["BHA"], E["mehmood"], "Hydraulic fluid weep at green system reservoir", "29", False, inspection=ins)
    s.step(f"Pre-departure check on {ac['BHA'].registration} finds {d.description} -> {d.label()} (not yet clear if deferrable)")
    s.attempt(op.defer_defect, reg, d, "MEL 29-11-01", 3, E["anwar"])
    advance(20)
    op.escalate_defect(reg, d, E["mehmood"], "Leak rate above MEL limit; aircraft unserviceable")
    s.step(f"Engineering escalates: {ac['BHA'].registration} is now {ac['BHA'].status.upper()}")
    s.attempt(op.assign_aircraft, reg, F["301"], ac["BHA"], "try to keep original")
    sub1 = op.substitute_aircraft(reg, F["301"], ac["BHB"], "AP-BHA AOG (hydraulic leak)", actor="ops_control")
    s.step(f"Substitution 1: {sub1.resolution}. Seats: {ac['BHB'].current_configuration().capacity()} vs {ac['BHA'].current_configuration().capacity()}")
    for line in [e.detail for e in sub1.events if e.action == "warning"]:
        s.step("Warning: " + line)
    advance(25)
    apu = op.raise_defect(reg, ac["BHB"], E["mehmood"], "APU bleed valve sluggish", "49", False, component=h["apu_bhb"])
    op.defer_defect(reg, apu, "MEL 49-10-02", 10, E["mehmood"])
    s.step(f"{ac['BHB'].registration}: {apu.label()} deferred under {apu.mel_reference} - flight can go, but the 14:00 work order remains")
    advance(15)
    sub2 = op.substitute_aircraft(reg, F["301"], ac["BHD"], "keep AP-BHB at LHE for its 14:00 brake work order", actor="ops_control")
    s.step(f"Substitution 2: {sub2.resolution} ({ac['BHD'].current_configuration().name})")
    pending = [seg for seg in F["301"].segments(active_only=False) if seg.status == "seat_pending"]
    for seg in pending:
        op.change_cabin(reg, seg, "Y", "no business cabin on AP-BHD; compensation case opened")
        op.assign_seat(reg, seg, "1A" if seg.passenger.first_name == "Ahmad" else "1B", "downgrade re-seat")
    s.step(f"{len(pending)} business-class passengers downgraded and re-seated (old cabin kept in history)")
    op.declare_delay(reg, F["301"], 90, "TD", "aircraft change x2", actor="ops_control")
    set_clock(T(7, 0))
    op.check_in_passenger(reg, h["S"]["ahmad_301"], E["mirza"]); op.check_in_passenger(reg, h["S"]["fatima_301"], E["mirza"])
    op.check_in_passenger(reg, h["S"]["baby_301"], E["mirza"]); op.check_in_passenger(reg, h["S"]["nadeem_301"], E["mirza"])
    op.check_in_passenger(reg, h["S"]["hira_301"], E["mirza"]); op.check_in_passenger(reg, h["S"]["bilal_301"], E["mirza"])
    for seg in F["301"].segments():
        if seg.status == "checked_in":
            op.board_passenger(reg, seg)
    for load in list(reg.all(CargoLoad)):
        if load.flight is F["301"] and load.status == "planned":
            op.load_cargo(reg, load)
    op.depart_flight(reg, F["301"], actor=E["hassan"].label())
    s.step(f"PK301 departs {fmt(now())} on {F['301'].current_aircraft().registration} (+{F['301'].to_dict()['delay_min']} min)")
    set_clock(T(8, 45)); op.arrive_flight(reg, F["301"])
    chain = " -> ".join(a.aircraft.registration + f"[{a.status}]" for a in F["301"].aircraft_assignments())
    s.check(f"Aircraft history of PK301: {chain}")
    smith = h["S"]["smith_301"]
    seats = [f"{sa.seat.number}@{sa.configuration.label()} [{sa.status}]" for sa in reg.all(SeatAssignment) if sa.segment is smith]
    s.check(f"Jonathan Smith's seat history: {' -> '.join(seats)}")
    s.check(f"Aircraft on PK301 at 05:00 was {F['301'].aircraft_at(T(5,0)).registration}; at 06:30 {F['301'].aircraft_at(T(6,30)).registration}")
    return s


def demo_crew_title_vs_qualification(reg, h):
    """Captain sick; the substitute has the right job title but not the type rating; later promotion keeps old records accurate."""
    s = Story()
    F, E, CA = h["F"], h["E"], h["CA"]
    set_clock(T(4, 30))
    op.release_crew(reg, CA[("301", "raza")], "reported unfit (illness)")
    op.release_crew(reg, CA[("302", "raza")], "reported unfit (illness)")
    op.release_crew(reg, CA[("303", "raza")], "reported unfit (illness)")
    s.step("Capt Raza reports sick: released from PK301, PK302 and PK303 (assignments kept as 'released')")
    s.attempt(op.assign_crew, reg, F["301"], E["chaudhry"], "CP")
    s.attempt(op.assign_crew, reg, F["301"], E["tariq"], "CP")
    a = op.assign_crew(reg, F["301"], E["qureshi"], "CP")
    s.step(f"Standby {a.label()} assigned (title {a.role_title}, A320 type rating held)")
    op.assign_crew(reg, F["302"], E["qureshi"], "CP")
    s.step("Same captain covers the return PK302 via rotation; PK303 tonight still has no captain (open item for crewing)")
    set_clock(T(10, 0))
    op.change_role(reg, E["khan"], "Captain", "Flight Operations")
    s.step("Sara Khan promoted to Captain at 10:00")
    old = CA[("301", "khan")]
    s.check(f"PK301 crew record still says: {old.crew.label()} flew as {old.position} with title '{old.role_title}'")
    roles = [f"{r.title} {fmt(r.valid_from)}-{fmt(r.valid_to) if r.valid_to else 'now'}" for r in reg.all(RoleAssignment) if r.employee is E["khan"]]
    s.check("Role history: " + "; ".join(roles))
    s.check(f"Role at 05:30 = {E['khan'].role_at(T(5,30)).title}; role now = {E['khan'].current_role().title}")
    return s


def demo_delayed_inbound_recovery_options(reg, h):
    """Delayed inbound PK760 threatens PK305 (same aircraft and crew) and connecting passengers; ops weighs several valid options."""
    s = Story()
    F, E, ac = h["F"], h["E"], h["ac"]
    set_clock(T(6, 40))
    d = op.declare_delay(reg, F["760"], 150, "WX", "fog at ISB, low visibility procedures", actor=E["gill"].label())
    s.step(f"PK760 delayed +150 -> ETD {fmt(F['760'].etd)}, ETA {fmt(F['760'].eta)}. Knock-on: {[f.label() for f in d.knock_on]}")
    at_risk = [e.detail for e in reg.journal if e.action == "connection_at_risk"]
    for line in at_risk:
        s.step("Connection at risk: " + line)
    o1 = op.propose_recovery(reg, d, "Delay PK305 by 60 min to protect connections", 5000, 3)
    o2 = op.propose_recovery(reg, d, "Operate PK305 with AP-BHD and Capt Qureshi's crew after PK301 (leaves PK302 uncrewed)", 12000, 0)
    o3 = op.propose_recovery(reg, d, "Cancel PK305 and rebook everyone tomorrow", 90000, 120)
    s.step("Three recovery options recorded")
    op.choose_recovery(reg, o1, E["gill"].label())
    op.declare_delay(reg, F["305"], 60, "RA", "reactionary: protect PK760 connections", actor=E["gill"].label())
    s.step(f"Chosen: {o1.description}. Others marked rejected but kept.")
    set_clock(T(9, 30))
    for seg in F["760"].segments():
        if seg.status == "checked_in":
            op.board_passenger(reg, seg)
    op.depart_flight(reg, F["760"], actor="dispatch ISB")
    set_clock(T(11, 30)); op.arrive_flight(reg, F["760"])
    s.step("PK760 arrives KHI 11:30; PK305 now departs 13:00 - connections hold")
    s.check("Options for this delay: " + "; ".join(f"{o.description[:40]}... [{o.status}]" for o in d.options()))
    s.check(f"Affected records on the delay: {d.affected}")
    return s


def demo_weather_restriction_and_cancellation(reg, h):
    """Weather cuts KHI capacity; PK302 is cancelled but bookings, crew, seat and cargo records remain in history; restriction later lifted."""
    s = Story()
    F, E, apts = h["F"], h["E"], h["apts"]
    set_clock(T(8, 0))
    r = op.apply_airport_restriction(reg, apts["KHI"], "weather", "Thunderstorm cell: single-runway ops, 50% arrival/departure rate", 0.5)
    s.step(f"Airport authority imposes: {r.description}")
    c = op.cancel_flight(reg, F["302"], "WX", "KHI slot cut; crew and aircraft reallocated", actor=E["gill"].label())
    s.step(f"PK302 cancelled. Records preserved: {c.records_preserved}")
    for key in ("laila_302", "kamran_302"):
        new = op.rebook_segment(reg, h["S"][key], F["304"], "PK302 cancelled")
        s.step(f"{new.passenger.label()} rebooked to {new.flight.label()}")
    set_clock(T(11, 0))
    op.lift_airport_restriction(reg, r)
    s.step("Restriction lifted at 11:00")
    s.check(f"Restrictions at KHI at 08:30: {[x.description for x in apts['KHI'].restrictions_at(T(8,30))]}")
    s.check(f"Restrictions at KHI at 11:30: {[x.description for x in apts['KHI'].restrictions_at(T(11,30))]}")
    seg = h["S"]["laila_302"]
    s.check(f"Original segment {seg.label()} status={seg.status}, rebooked_to={seg.rebooked_to.label()}")
    crew = [f"{a.crew.label()} [{a.status}]" for a in reg.all(CrewAssignment) if a.flight is F["302"]]
    s.check("PK302 crew history: " + "; ".join(crew))
    return s


def demo_passenger_offload_and_bag_routing(reg, h):
    """International passenger checked in, then document found invalid -> offloaded and bag pulled; another bag travels on a different flight from its owner."""
    s = Story()
    F, E, S = h["F"], h["E"], h["S"]
    set_clock(T(9, 0))
    op.report_bag_irregularity(reg, h["bag_a_iqbal"], "delayed", "Bag not on PK301 arrival belt - traced to LHE sort area", h["apts"]["KHI"], "KHI baggage services")
    op.reroute_bag(reg, h["bag_a_iqbal"], F["303"], "missed PK301 sortation; forward on next LHE-KHI")
    s.step(f"Ayesha Iqbal's bag {h['bag_a_iqbal'].tag} rerouted on {F['303'].label()} while she travelled on PK301")
    set_clock(T(10, 30))
    op.check_in_passenger(reg, S["ahmad_305"], None, "counter"); op.check_in_passenger(reg, S["fatima_305"], None, "counter")
    op.check_in_passenger(reg, S["baby_305"], None, "counter")
    bag = op.accept_bag(reg, S["ahmad_305"], "PK305001", 22, h["orgs"]["handler_khi"])
    s.step("Siddiqui family checked in for PK305 KHI-DXB, one bag accepted and loaded")
    advance(40)
    op.invalidate_document(reg, h["passport_ahmad"], "passport expires 15 Oct: less than 6 months validity for UAE entry")
    bags = op.offload_passenger(reg, S["ahmad_305"], "travel document not acceptable for destination")
    s.step(f"Ahmad Siddiqui offloaded after check-in; {len(bags)} bag(s) automatically offloaded (security rule)")
    s.step(f"Fatima and infant remain checked in on PK305 [{S['fatima_305'].status}]")
    s.attempt(op.check_in_passenger, reg, S["ahmad_305"], None, "counter")
    s.check("Bag movements: " + " -> ".join(f"{x.flight.label()}[{x.status}]" for x in h["bag_a_iqbal"].movements()))
    ci = S["ahmad_305"].check_in()
    s.check(f"Ahmad's PK305 check-in record kept: status={ci.status}, reason='{ci.offload_reason}', seq={ci.boarding_pass_seq}")
    s.check(f"Ahmad's bag {bag.tag}: status={bag.status}, movements={[ (x.flight.label(), x.status) for x in bag.movements()]}")
    return s


def demo_cargo_reclassified_and_damaged_bag(reg, h):
    """Cargo accepted as general later suspected to contain lithium batteries; damaged bag on arrival."""
    s = Story()
    F, E, C = h["F"], h["E"], h["C"]
    set_clock(T(9, 15))
    s.step(f"{C['machines'].label()} was accepted at {fmt(C['machines'].accepted_at)} as '{C['machines'].description}' on {F['303'].label()}")
    op.declare_handling(reg, C["machines"], "DGR", "Suspected UN3480 lithium-ion batteries inside crated parts (x-ray)", "LHE cargo screening")
    s.step(f"Reclassified: status={C['machines'].status}, handling={[r.code for r in C['machines'].requirements()]}; offloaded from PK303 pending DG check")
    s.attempt(op.load_cargo, reg, h["load_machines"])
    s.step(f"Temperature-sensitive {C['pharma'].label()} flew on PK301 as planned; {C['textiles'].label()} was offloaded by the substitution and awaits re-plan")
    set_clock(T(11, 40))
    pir = op.report_bag_irregularity(reg, h["bag_omar"], "damaged", "Hard-shell case cracked, wheel missing, on PK760 arrival", h["apts"]["KHI"], "Gerry's dnata")
    op.resolve_bag_irregularity(reg, pir, "Repair voucher PKR 8,000 issued")
    s.step(f"{pir.label()} raised and closed: {pir.resolution}")
    s.check(f"Handling requirements on {C['machines'].label()} at 05:00: {[r.code for r in C['machines'].requirements(T(5,0))]}; now: {[r.code for r in C['machines'].requirements()]}")
    s.check(f"Loads for {C['machines'].label()}: {[(l.flight.label(), l.status, l.offload_reason) for l in reg.all(type(h['load_machines'])) if l.consignment is C['machines']]}")
    return s


def demo_reconfiguration_and_retirement(reg, h):
    """Cabin re-configured after bookings exist; then the aircraft is retired although a flight tonight is planned on it."""
    s = Story()
    F, E, ac = h["F"], h["E"], h["ac"]
    set_clock(T(12, 0))
    old_cfg = ac["BHE"].current_configuration()
    new_cfg, reseated = op.reconfigure_cabin(reg, ac["BHE"], "16C/144Y (premium refit)", [("C", 4, 4), ("Y", 24, 6)])
    s.step(f"{ac['BHE'].registration} reconfigured {old_cfg.name} -> {new_cfg.name}; {reseated} PK303 passengers re-seated")
    z = h["S"]["zeeshan_303"]
    hist = [f"{sa.seat.number}@v{sa.configuration.version} [{sa.status}]" for sa in reg.all(SeatAssignment) if sa.segment is z]
    s.step(f"Zeeshan Haider (was 29A, row no longer exists): {' -> '.join(hist)}")
    set_clock(T(12, 30))
    orphaned = op.retire_aircraft(reg, ac["BHE"], "Corrosion found during refit; lease return brought forward")
    s.step(f"{ac['BHE'].registration} RETIRED. Flights left without aircraft: {[f.label() + '[' + f.status + ']' for f in orphaned]}")
    s.attempt(op.assign_aircraft, reg, F["303"], ac["BHA"], "try the original PK301 aircraft")
    set_clock(T(14, 0))
    op.complete_work_order(reg, h["wo_bhb"], E["mehmood"], "Brake unit replaced, ops check good")
    op.assign_aircraft(reg, F["303"], ac["BHB"], "AP-BHB released from maintenance")
    reseated2 = op.reseat_flight(reg, F["303"], "aircraft assigned after retirement")
    s.step(f"AP-BHB assigned to PK303 after its work order; {reseated2} passengers re-seated again onto {ac['BHB'].current_configuration().label()}")
    s.check(f"Configuration of AP-BHE at 05:00: {ac['BHE'].configuration_at(T(5,0)).label()}; at 12:15: {ac['BHE'].configuration_at(T(12,15)).label()}")
    s.check(f"AP-BHE status={ac['BHE'].status}, retired_at={fmt(ac['BHE'].retired_at)}; its {len([c for c in reg.all(type(old_cfg)) if c.aircraft is ac['BHE']])} configurations still exist")
    s.check("Zeeshan's full seat history: " + " -> ".join(f"{sa.seat.label()} [{sa.status}]" for sa in reg.all(SeatAssignment) if sa.segment is z))
    return s


def demo_charter_change_and_diversion(reg, h):
    """Charter customer changes passenger numbers at the last minute; the charter then diverts."""
    s = Story()
    F, E, ac, apts = h["F"], h["E"], h["ac"], h["apts"]
    set_clock(T(13, 30))
    a = h["charter"]
    s.step(f"{a.label()}: {a.agreed_passengers} pax agreed on {ac['BKX'].registration} ({ac['BKX'].current_configuration().capacity()} seats)")
    s.attempt(op.amend_charter, reg, a, 80, "customer adds a second department")
    op.amend_charter(reg, a, 70, "customer adds a second department (reduced to fit)")
    s.step(f"Amendment accepted: now {a.agreed_passengers} pax; amendments on file: {len(a.amendments)}")
    s.attempt(op.assign_crew, reg, F["9001"], E["ali"], "CC")
    op.grant_qualification(reg, E["ali"], "cabin_type", "ATR72", "Airline Training")
    op.assign_crew(reg, F["9001"], E["ali"], "CC")
    s.step("Extra cabin crew needed for 70 pax: Hamza Ali qualified on ATR72 today and assigned")
    set_clock(T(15, 5)); op.depart_flight(reg, F["9001"])
    set_clock(T(15, 50))
    d = op.divert_flight(reg, F["9001"], apts["MUX"], "WX", "dust storm at SKZ below minima", actor=E["farooq"].label())
    set_clock(T(16, 10)); op.arrive_flight(reg, F["9001"])
    s.step(f"PK9001 diverted to MUX: flight status={F['9001'].status}, movement planned={F['9001'].movement().planned_destination.iata} actual={F['9001'].movement().actual_destination.iata}")
    s.check(f"Charter amendment trail: {a.amendments}")
    s.check(f"The ScheduledService still says {F['9001'].service.route.label()}; only the movement changed")
    return s


DEMOS = [
    demo_crew_title_vs_qualification,      # 04:30 - before the aircraft problem
    demo_aircraft_substitution,            # 04:45 - 08:45
    demo_delayed_inbound_recovery_options,
    demo_weather_restriction_and_cancellation,
    demo_passenger_offload_and_bag_routing,
    demo_cargo_reclassified_and_damaged_bag,
    demo_reconfiguration_and_retirement,
    demo_charter_change_and_diversion,
]


def run_all(reg, h):
    out = []
    for fn in DEMOS:
        out.append({"name": fn.__name__, "title": fn.__doc__, "story": fn(reg, h)})
    return out
