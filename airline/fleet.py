"""Fleet: aircraft types, individual airframes, and their changing cabin layouts.

Key distinction (research area: "aircraft type versus an individual aircraft"):
  AircraftType        what the manufacturer certifies (A320-200).  Crew type
                      ratings and MEL documents attach to the type.
  Aircraft            one physical airframe with a registration (AP-BHA).
                      Defects, components and availability attach here.
  CabinConfiguration  a dated version of how one aircraft's cabin is laid out.
                      Bookings reference the version that was in force when the
                      seat was assigned, so a re-configuration never rewrites
                      history.
"""
from .core import Record, TemporalRecord, now


class AircraftType(Record):
    prefix = "TYP"

    def __init__(self, registry, code, manufacturer, name, max_cargo_kg, range_km):
        super().__init__(registry)
        self.code = code                    # e.g. "A320"
        self.manufacturer = manufacturer
        self.name = name
        self.max_cargo_kg = max_cargo_kg
        self.range_km = range_km

    def label(self):
        return self.code


class Aircraft(Record):
    prefix = "ACF"

    def __init__(self, registry, registration, aircraft_type, msn, cargo_capacity_kg):
        super().__init__(registry, status="in_service")
        self.registration = registration    # tail number, e.g. AP-BHA
        self.aircraft_type = aircraft_type
        self.msn = msn                      # manufacturer serial number
        self.cargo_capacity_kg = cargo_capacity_kg
        self.location = None                # Airport where it currently is
        self.retired_at = None

    def label(self):
        return self.registration

    def current_configuration(self):
        for c in self.registry.all(CabinConfiguration):
            if c.aircraft is self and c.is_current():
                return c
        return None

    def configuration_at(self, t):
        for c in self.registry.all(CabinConfiguration):
            if c.aircraft is self and c.is_valid_at(t):
                return c
        return None

    def is_available(self):
        return self.status == "in_service"


class CabinConfiguration(TemporalRecord):
    prefix = "CFG"

    def __init__(self, registry, aircraft, name, cabins):
        """cabins: list of (cabin_class, rows, seats_per_row) e.g. [("C",2,4),("Y",25,6)]"""
        super().__init__(registry)
        self.aircraft = aircraft
        self.name = name
        self.cabins = [{"cabin_class": c, "rows": r, "abreast": a} for c, r, a in cabins]
        self.version = len([c for c in registry.all(CabinConfiguration) if c.aircraft is aircraft])
        self.seats = self._build_seats()

    def _build_seats(self):
        seats = []
        row = 1
        for cabin in self.cabins:
            letters = "ABCDEFGHJK"[: cabin["abreast"]]
            for _ in range(cabin["rows"]):
                for letter in letters:
                    seats.append(Seat(self.registry, self, f"{row}{letter}", cabin["cabin_class"]))
                row += 1
        return seats

    def label(self):
        return f"{self.aircraft.registration} v{self.version} ({self.name})"

    def seat_numbers(self):
        return {s.number for s in self.seats}

    def seat(self, number):
        for s in self.seats:
            if s.number == number:
                return s
        return None

    def capacity(self, cabin_class=None):
        return len([s for s in self.seats if cabin_class in (None, s.cabin_class)])

    def to_dict(self):
        d = super().to_dict()
        d["seats"] = len(self.seats)
        d["capacity"] = {c["cabin_class"]: self.capacity(c["cabin_class"]) for c in self.cabins}
        return d


class Seat(Record):
    """A seat exists only inside one configuration version.  When the aircraft is
    reconfigured a new set of Seat records is created; the old ones remain so
    that an old SeatAssignment still points at a real seat."""
    prefix = "SEA"

    def __init__(self, registry, configuration, number, cabin_class):
        super().__init__(registry)
        self.configuration = configuration
        self.number = number
        self.cabin_class = cabin_class

    def label(self):
        return f"{self.configuration.aircraft.registration}/{self.number}"


class Component(TemporalRecord):
    """A serialised part installed on an aircraft for a period (engine, APU,
    slide).  Removal ends the period; the record and its defects stay."""
    prefix = "CMP"

    def __init__(self, registry, aircraft, part_number, serial_number, description):
        super().__init__(registry)
        self.aircraft = aircraft
        self.part_number = part_number
        self.serial_number = serial_number
        self.description = description

    def label(self):
        return f"{self.description} S/N {self.serial_number}"
