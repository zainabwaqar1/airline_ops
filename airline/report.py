"""End-of-day explanation: what changed, who was affected, and why.

Built entirely from records that still exist - nothing here needs anything
that was 'deleted', because nothing is."""
from .core import TemporalRecord, fmt
from .network import Flight, AircraftAssignment
from .people import CrewAssignment
from .commercial import FlightSegment
from .baggage import Bag
from .cargo import CargoLoad
from .disruption import Disruption
from .maintenance import Defect


def end_of_day(reg):
    flights = []
    for f in sorted(reg.all(Flight), key=lambda x: x.std):
        segs = f.segments(active_only=False)
        by_status = {}
        for s in segs:
            by_status[s.status] = by_status.get(s.status, 0) + 1
        flights.append({
            "flight": f.label(), "route": f.service.route.label(), "kind": f.service.service_kind,
            "status": f.status, "std": fmt(f.std), "etd": fmt(f.etd), "delay_min": f.to_dict()["delay_min"],
            "aircraft_chain": [f"{a.aircraft.registration} [{a.status}]" for a in f.aircraft_assignments()],
            "crew": [f"{c.crew.label()} {c.position} [{c.status}]" for c in reg.all(CrewAssignment) if c.flight is f],
            "passengers_by_status": by_status,
            "bags": len([b for b in reg.all(Bag) if any(m.flight is f for m in b.movements())]),
            "cargo_loads": [f"{l.consignment.label()} [{l.status}]" for l in reg.all(CargoLoad) if l.flight is f],
            "movement": (lambda m: f"{m.planned_destination.iata} -> {m.actual_destination.iata} [{m.status}]" if m else None)(f.movement()),
        })
    disruptions = [{
        "id": d.id, "type": type(d).__name__, "flight": d.flight.label(), "reason": d.reason_code,
        "description": d.description, "declared": fmt(d.declared_at), "resolution": d.resolution,
        "affected": [reg.get(i).label() for i in d.affected], "options": [f"{o.description} [{o.status}]" for o in d.options()],
    } for d in sorted(reg.all(Disruption), key=lambda d: d.declared_at)]
    refused = [e.to_dict() for e in reg.journal if e.action == "refused"]
    ended = [{"type": type(r).__name__, "label": r.label(), "from": fmt(r.valid_from), "to": fmt(r.valid_to), "status": r.status}
             for r in reg.all(TemporalRecord) if r.valid_to is not None]
    defects = [{"id": d.id, "aircraft": d.aircraft.registration, "description": d.description, "status": d.status,
                "grounding": d.grounding, "mel": d.mel_reference} for d in reg.all(Defect)]
    open_items = []
    for f in reg.all(Flight):
        if f.status in ("planned", "delayed", "needs_aircraft"):
            positions = {c.position for c in f.crew_assignments()}
            missing = {"CP", "FO", "SCCM"} - positions
            if missing:
                open_items.append(f"{f.label()} still needs crew positions {sorted(missing)}")
            if f.current_aircraft() is None:
                open_items.append(f"{f.label()} has no aircraft")
    for c in reg.all(CargoLoad):
        if c.status == "offloaded" and c.consignment.current_load() is None and c.consignment.status != "delivered":
            open_items.append(f"{c.consignment.label()} offloaded ({c.offload_reason}) and not yet re-planned")
    return {
        "flights": flights, "disruptions": disruptions, "refused_attempts": refused,
        "periods_ended_today": ended, "defects": defects, "open_items": open_items,
        "totals": {"records": len(reg.items), "events": len(reg.journal), "classes_in_use": len({type(r).__name__ for r in reg.items.values()})},
    }
