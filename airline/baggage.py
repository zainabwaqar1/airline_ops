"""Baggage.  Deliberately NOT related to cargo by inheritance (see
docs/inheritance.md, rejected hierarchy #1): a bag belongs to a passenger
segment and travels free under the ticket; a consignment is a paid contract
with a shipper and its own documentation.  They share 'weight' and 'loaded on
a flight' and nothing else of substance.

  Bag                 identified by its tag; owner is a FlightSegment
  BagMovement         each time a bag is loaded on / offloaded from a flight.
                      Lets a bag's routing differ from its owner's.
  BaggageIrregularity the PIR raised when a bag is damaged, delayed, or lost.
"""
from .core import Record, now


class Bag(Record):
    prefix = "BAG"

    def __init__(self, registry, tag, owner_segment, weight_kg, accepted_by):
        super().__init__(registry, status="accepted")
        self.tag = tag
        self.owner_segment = owner_segment
        self.weight_kg = weight_kg
        self.accepted_by = accepted_by      # GroundStaff or handler Organisation
        self.accepted_at = now()

    def label(self):
        return f"bag {self.tag}"

    def movements(self):
        return [m for m in self.registry.all(BagMovement) if m.bag is self]

    def current_flight(self):
        for m in reversed(self.movements()):
            if m.status == "loaded":
                return m.flight
        return None

    def to_dict(self):
        d = super().to_dict()
        d["owner"] = self.owner_segment.passenger.label()
        d["owner_flight"] = self.owner_segment.flight.label()
        cf = self.current_flight()
        d["loaded_on"] = cf.label() if cf else None
        return d


class BagMovement(Record):
    prefix = "BMV"

    def __init__(self, registry, bag, flight, handler, reason):
        super().__init__(registry, status="loaded")
        self.bag = bag
        self.flight = flight
        self.handler = handler
        self.reason = reason
        self.loaded_at = now()
        self.offloaded_at = None

    def label(self):
        return f"{self.bag.label()} on {self.flight.label()}"


class BaggageIrregularity(Record):
    """Property Irregularity Report."""
    prefix = "PIR"

    def __init__(self, registry, bag, kind, description, reported_at_airport, reported_by):
        super().__init__(registry, status="open")
        self.bag = bag
        self.kind = kind                    # damaged | delayed | missing | pilfered
        self.description = description
        self.reported_at_airport = reported_at_airport
        self.reported_by = reported_by
        self.resolution = None

    def label(self):
        return f"PIR {self.kind} {self.bag.tag}"
