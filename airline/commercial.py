"""Commercial records: bookings, travel documents, check-in, seating, special
service requests, and charter agreements.

  Booking (PNR)     the commercial contract with one or more passengers.
  FlightSegment     one passenger on one flight under a booking.  This is the
                    unit that gets confirmed, checked in, boarded, rebooked or
                    cancelled.  Rebooking creates a NEW segment and links it,
                    so both the missed and the new flight remain in history.
  SeatAssignment    dated: points to a Seat inside a specific configuration
                    version.  A substitution supersedes it rather than editing.
  CheckIn           the airport transaction; offloading reverses it with a reason.
  CharterAgreement  the customer contract that a charter Flight operates under.
                    A charter is a commercial arrangement, not a kind of flight.
"""
from .core import Record, TemporalRecord, now


class Booking(Record):
    prefix = "PNR"

    def __init__(self, registry, locator, booked_by, contact_email, corporate=None):
        super().__init__(registry, status="confirmed")
        self.locator = locator
        self.booked_by = booked_by
        self.contact_email = contact_email
        self.corporate = corporate          # Organisation or None
        self.total_fare = 0.0

    def label(self):
        return self.locator

    def segments(self):
        return [s for s in self.registry.all(FlightSegment) if s.booking is self]


class FlightSegment(Record):
    prefix = "SEG"

    def __init__(self, registry, booking, passenger, flight, cabin_class, fare):
        super().__init__(registry, status="confirmed")
        self.booking = booking
        self.passenger = passenger
        self.flight = flight
        self.cabin_class = cabin_class
        self.fare = fare
        self.rebooked_from = None
        self.rebooked_to = None
        self.connecting_to = None           # another FlightSegment on the same booking

    def label(self):
        return f"{self.passenger.label()} on {self.flight.label()}"

    def seat_assignment(self):
        for s in self.registry.all(SeatAssignment):
            if s.segment is self and s.is_current():
                return s
        return None

    def check_in(self):
        for c in self.registry.all(CheckIn):
            if c.segment is self:
                return c
        return None

    def to_dict(self):
        d = super().to_dict()
        sa = self.seat_assignment()
        d["seat"] = sa.seat.number if sa else None
        d["booking_locator"] = self.booking.locator
        d["flight_label"] = self.flight.label()
        d["passenger_name"] = self.passenger.label()
        return d


class SeatAssignment(TemporalRecord):
    prefix = "SAS"

    def __init__(self, registry, segment, seat, reason):
        super().__init__(registry, status="assigned")
        self.segment = segment
        self.seat = seat                    # Seat in a specific CabinConfiguration
        self.configuration = seat.configuration
        self.reason = reason

    def label(self):
        return f"{self.segment.passenger.label()} seat {self.seat.number} ({self.configuration.label()})"


class TravelDocument(Record):
    prefix = "DOC"

    def __init__(self, registry, holder, kind, number, issuing_country, expires):
        super().__init__(registry, status="valid")
        self.holder = holder
        self.kind = kind                    # passport | national_id | visa
        self.number = number
        self.issuing_country = issuing_country
        self.expires = expires

    def label(self):
        return f"{self.kind} {self.number}"


class CheckIn(Record):
    prefix = "CKI"

    def __init__(self, registry, segment, agent, channel):
        super().__init__(registry, status="checked_in")
        self.segment = segment
        self.agent = agent                  # GroundStaff or None for online
        self.channel = channel              # counter | online | kiosk
        self.boarding_pass_seq = None
        self.boarded_at = None
        self.offload_reason = None

    def label(self):
        return f"check-in {self.segment.label()}"


class SpecialServiceRequest(Record):
    """IATA-style SSR codes attached to a segment: INFT infant, WCHR wheelchair,
    UMNR unaccompanied minor, MEDA medical."""
    prefix = "SSR"

    def __init__(self, registry, segment, code, detail):
        super().__init__(registry, status="requested")
        self.segment = segment
        self.code = code
        self.detail = detail

    def label(self):
        return f"{self.code} for {self.segment.passenger.label()}"


class CharterAgreement(Record):
    prefix = "CHA"

    def __init__(self, registry, customer, flight, agreed_passengers, price):
        super().__init__(registry, status="agreed")
        self.customer = customer            # Organisation
        self.flight = flight
        self.agreed_passengers = agreed_passengers
        self.price = price
        self.amendments = []                # list of dicts, oldest first

    def label(self):
        return f"Charter {self.customer.name} {self.flight.label()}"
