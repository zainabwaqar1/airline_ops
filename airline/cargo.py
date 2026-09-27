"""Air cargo.

  Consignment          the shipment under one air waybill; belongs to a shipper,
                       tendered by a freight agent.
  HandlingRequirement  a dated requirement attached to a consignment: PER
                       (perishable, temperature range), DGR (dangerous goods,
                       UN number), AVI (live animals) ...  Adding one later does
                       not rewrite the acceptance record; it shows WHEN the
                       airline learned of it.
  CargoLoad            the consignment's place on a particular flight.  Offload
                       and re-plan create a new CargoLoad rather than editing.
"""
from .core import Record, TemporalRecord, now


class Consignment(Record):
    prefix = "AWB"

    def __init__(self, registry, awb_number, shipper, agent, description, pieces, weight_kg, origin, destination):
        super().__init__(registry, status="booked")
        self.awb_number = awb_number
        self.shipper = shipper              # Organisation
        self.agent = agent                  # Organisation (freight agent)
        self.description = description
        self.pieces = pieces
        self.weight_kg = weight_kg
        self.origin = origin
        self.destination = destination
        self.accepted_at = None
        self.accepted_by = None

    def label(self):
        return f"AWB {self.awb_number}"

    def requirements(self, at=None):
        t = at or now()
        return [r for r in self.registry.all(HandlingRequirement) if r.consignment is self and r.is_valid_at(t)]

    def current_load(self):
        for l in self.registry.all(CargoLoad):
            if l.consignment is self and l.status in ("planned", "loaded"):
                return l
        return None

    def to_dict(self):
        d = super().to_dict()
        d["handling"] = [r.code for r in self.requirements()]
        cl = self.current_load()
        d["on_flight"] = cl.flight.label() if cl else None
        return d


class HandlingRequirement(TemporalRecord):
    prefix = "HRQ"

    def __init__(self, registry, consignment, code, detail, declared_by):
        super().__init__(registry)
        self.consignment = consignment
        self.code = code                    # PER | DGR | AVI | VAL | HUM
        self.detail = detail
        self.declared_by = declared_by

    def label(self):
        return f"{self.code} on {self.consignment.label()}"


class CargoLoad(Record):
    prefix = "CLD"

    def __init__(self, registry, consignment, flight, planned_by):
        super().__init__(registry, status="planned")
        self.consignment = consignment
        self.flight = flight
        self.planned_by = planned_by
        self.loaded_at = None
        self.offloaded_at = None
        self.offload_reason = None

    def label(self):
        return f"{self.consignment.label()} on {self.flight.label()}"
