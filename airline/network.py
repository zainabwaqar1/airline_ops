"""Network: airports, routes, the planned schedule, and the flights that
actually operate on a date.

Answers the question "planned service vs flight on a date vs movement":
  ScheduledService   the commercial plan: PK301 LHE-KHI departs 05:30 daily.
  Flight             PK301 on 24 Sep 2026.  Bookings, crew, bags, cargo and
                     disruptions all hang off this record.
  AircraftAssignment which airframe operates the flight, for a period.  A
                     substitution ends one assignment and opens another, so the
                     flight can change aircraft twice and still show all three.
  FlightMovement     what physically happened: off-blocks, airborne, landed,
                     and where.  A diversion changes the movement, not the plan.
"""
from datetime import datetime, timedelta
from .core import Record, TemporalRecord, now


class Airport(Record):
    prefix = "APT"

    def __init__(self, registry, iata, name, city, country, operator):
        super().__init__(registry)
        self.iata = iata
        self.name = name
        self.city = city
        self.country = country
        self.operator = operator            # the airport authority (not the airline)

    def label(self):
        return self.iata

    def restrictions_at(self, t):
        return [r for r in self.registry.all(AirportRestriction) if r.airport is self and r.is_valid_at(t)]


class AirportRestriction(TemporalRecord):
    """Something the airport authority imposes for a period: weather capacity
    cut, runway closure, curfew.  Owned by the airport, not the airline."""
    prefix = "RST"

    def __init__(self, registry, airport, kind, description, capacity_factor=1.0):
        super().__init__(registry)
        self.airport = airport
        self.kind = kind
        self.description = description
        self.capacity_factor = capacity_factor

    def label(self):
        return f"{self.airport.iata} {self.kind}"


class Route(Record):
    prefix = "RTE"

    def __init__(self, registry, origin, destination, distance_km, international):
        super().__init__(registry)
        self.origin = origin
        self.destination = destination
        self.distance_km = distance_km
        self.international = international

    def label(self):
        return f"{self.origin.iata}-{self.destination.iata}"


class ScheduledService(Record):
    prefix = "SVC"

    def __init__(self, registry, flight_number, route, dep_time, arr_time, days_of_week, service_kind="scheduled"):
        super().__init__(registry)
        self.flight_number = flight_number
        self.route = route
        self.dep_time = dep_time            # "05:30"
        self.arr_time = arr_time
        self.days_of_week = days_of_week    # "1234567"
        self.service_kind = service_kind    # scheduled | charter  (an attribute, not a subclass)

    def label(self):
        return f"{self.flight_number} {self.route.label()} {self.dep_time}"


class Flight(Record):
    prefix = "FLT"

    def __init__(self, registry, service, date):
        super().__init__(registry, status="planned")
        self.service = service
        self.date = date
        h, m = map(int, service.dep_time.split(":"))
        self.std = datetime(date.year, date.month, date.day, h, m)    # scheduled time of departure
        h, m = map(int, service.arr_time.split(":"))
        self.sta = datetime(date.year, date.month, date.day, h, m)
        self.etd = self.std                                           # estimated, moves with delays
        self.eta = self.sta

    def label(self):
        return f"{self.service.flight_number}/{self.date.strftime('%d%b').upper()}"

    @property
    def origin(self):
        return self.service.route.origin

    @property
    def destination(self):
        return self.service.route.destination

    # -- assignments ---------------------------------------------------------
    def aircraft_assignments(self):
        return [a for a in self.registry.all(AircraftAssignment) if a.flight is self]

    def current_aircraft(self):
        for a in self.aircraft_assignments():
            if a.is_current():
                return a.aircraft
        return None

    def aircraft_at(self, t):
        for a in self.aircraft_assignments():
            if a.is_valid_at(t):
                return a.aircraft
        return None

    def crew_assignments(self, current_only=True):
        from .people import CrewAssignment
        out = [c for c in self.registry.all(CrewAssignment) if c.flight is self]
        return [c for c in out if c.is_current()] if current_only else out

    def segments(self, active_only=True):
        from .commercial import FlightSegment
        out = [s for s in self.registry.all(FlightSegment) if s.flight is self]
        return [s for s in out if s.status in ("confirmed", "checked_in", "boarded")] if active_only else out

    def movement(self):
        for mv in self.registry.all(FlightMovement):
            if mv.flight is self:
                return mv
        return None

    def to_dict(self):
        d = super().to_dict()
        ac = self.current_aircraft()
        d["flight_number"] = self.service.flight_number
        d["route"] = self.service.route.label()
        d["service_kind"] = self.service.service_kind
        d["aircraft"] = ac.registration if ac else None
        d["std_time"] = self.std.strftime("%H:%M")
        d["etd_time"] = self.etd.strftime("%H:%M")
        d["delay_min"] = int((self.etd - self.std).total_seconds() // 60)
        d["passengers"] = len([s for s in self.segments(active_only=False)
                               if s.status in ("confirmed", "checked_in", "boarded", "flown", "seat_pending")])
        d["crew"] = len(self.crew_assignments())
        return d


class AircraftAssignment(TemporalRecord):
    prefix = "AAS"

    def __init__(self, registry, flight, aircraft, reason):
        super().__init__(registry)
        self.flight = flight
        self.aircraft = aircraft
        self.reason = reason
        self.superseded_by = None

    def label(self):
        return f"{self.flight.label()} on {self.aircraft.registration}"


class FlightMovement(Record):
    """The physical operation of a flight: actual times and actual airports.
    Created when the flight departs; a diversion changes actual_destination."""
    prefix = "MOV"

    def __init__(self, registry, flight, aircraft):
        super().__init__(registry, status="airborne")
        self.flight = flight
        self.aircraft = aircraft
        self.actual_departure = now()
        self.actual_arrival = None
        self.planned_destination = flight.destination
        self.actual_destination = flight.destination

    def label(self):
        return f"{self.flight.label()} movement"
