"""Disruption and recovery.

Third inheritance structure:

    Record
     └── Disruption             an operational event against a flight that ops
          │                     control must decide on: declared when, why,
          │                     by whom; resolved how; who was affected
          ├── Delay             minutes and a reason code
          ├── Cancellation      the flight will not operate; records stay
          ├── Diversion         the movement lands somewhere else
          └── AircraftSubstitution   airframe A replaced by airframe B

Ops control treats these identically for reporting and for the end-of-day
explanation (who was affected and why), which is what justifies the parent.

RecoveryOption records the *choices* ops considered for a disruption, so a
"delayed inbound producing multiple valid recovery choices" is visible even
for the options that were not taken.
"""
from .core import Record, now


class Disruption(Record):
    prefix = "DIS"

    def __init__(self, registry, flight, reason_code, description, declared_by):
        super().__init__(registry, status="open")
        self.flight = flight
        self.reason_code = reason_code      # IATA-style: TD technical, WX weather, CR crew, RA reactionary
        self.description = description
        self.declared_by = declared_by
        self.declared_at = now()
        self.resolved_at = None
        self.resolution = None
        self.affected = []                  # ids of records touched by this disruption

    def label(self):
        return f"{type(self).__name__} {self.flight.label()} ({self.reason_code})"

    def touch(self, record):
        if record.id not in self.affected:
            self.affected.append(record.id)

    def resolve(self, resolution):
        self.resolution = resolution
        self.resolved_at = now()
        self.set_status("resolved", resolution)

    def options(self):
        return [o for o in self.registry.all(RecoveryOption) if o.disruption is self]


class Delay(Disruption):
    prefix = "DLY"

    def __init__(self, registry, flight, reason_code, description, declared_by, minutes):
        super().__init__(registry, flight, reason_code, description, declared_by)
        self.minutes = minutes
        self.knock_on = []                  # flights threatened by this delay


class Cancellation(Disruption):
    prefix = "CNL"

    def __init__(self, registry, flight, reason_code, description, declared_by):
        super().__init__(registry, flight, reason_code, description, declared_by)
        self.records_preserved = {}         # counts of the records that stay in history


class Diversion(Disruption):
    prefix = "DIV"

    def __init__(self, registry, flight, reason_code, description, declared_by, diverted_to):
        super().__init__(registry, flight, reason_code, description, declared_by)
        self.diverted_to = diverted_to


class AircraftSubstitution(Disruption):
    prefix = "SUB"

    def __init__(self, registry, flight, reason_code, description, declared_by, from_aircraft, to_aircraft):
        super().__init__(registry, flight, reason_code, description, declared_by)
        self.from_aircraft = from_aircraft
        self.to_aircraft = to_aircraft
        self.seats_lost = 0
        self.cargo_offloaded_kg = 0


class RecoveryOption(Record):
    prefix = "OPT"

    def __init__(self, registry, disruption, description, cost_estimate, passengers_affected):
        super().__init__(registry, status="proposed")
        self.disruption = disruption
        self.description = description
        self.cost_estimate = cost_estimate
        self.passengers_affected = passengers_affected
        self.decided_by = None

    def label(self):
        return f"Option: {self.description}"
