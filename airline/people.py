"""People and organisations.

The multi-level hierarchy discovered from the domain:

    Record
     └── Person                 identity + travel/ID documents
          ├── Passenger         a person who travels (frequent-flyer no., SSR needs)
          └── Employee          a person the airline employs (staff no., base)
               ├── CrewMember   licensed operating crew: duty limits, positioning
               │    ├── FlightDeckCrew   holds type ratings, a licence number
               │    └── CabinCrew        holds cabin-type qualifications, SEP check
               ├── MaintenanceEngineer  holds certifying-staff authorisations
               └── GroundStaff          airport-side roles (dispatch, ramp, check-in)

Why the shared information sits where it does is argued in docs/inheritance.md.
Job TITLE is deliberately NOT a subclass: an employee's title changes over time,
so it is a dated RoleAssignment.  Old crew assignments keep the role that was
held on the day.
"""
from .core import Record, TemporalRecord, now


class Organisation(Record):
    """A company the airline deals with: corporate travel coordinator, cargo
    customer, freight agent, third-party ground handler, airport authority."""
    prefix = "ORG"

    def __init__(self, registry, name, kind):
        super().__init__(registry)
        self.name = name
        self.kind = kind          # corporate | freight_agent | shipper | handler | authority | charter_customer

    def label(self):
        return self.name


class Person(Record):
    prefix = "PER"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality):
        super().__init__(registry)
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.nationality = nationality

    def label(self):
        return f"{self.first_name} {self.last_name}"

    def documents(self):
        from .commercial import TravelDocument
        return [d for d in self.registry.all(TravelDocument) if d.holder is self]


class Passenger(Person):
    prefix = "PAX"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, frequent_flyer=None):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality)
        self.frequent_flyer = frequent_flyer

    def is_infant(self, on_date):
        return (on_date - self.date_of_birth).days < 730


class Employee(Person):
    prefix = "EMP"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality)
        self.staff_number = staff_number
        self.base = base                  # Airport
        self.employment_status = "employed"

    def label(self):
        return f"{self.first_name} {self.last_name} ({self.staff_number})"

    def role_at(self, t):
        for r in self.registry.all(RoleAssignment):
            if r.employee is self and r.is_valid_at(t):
                return r
        return None

    def current_role(self):
        return self.role_at(now())

    def qualifications_at(self, t):
        return [q for q in self.registry.all(Qualification) if q.holder is self and q.is_valid_at(t)]

    def to_dict(self):
        d = super().to_dict()
        r = self.current_role()
        d["role"] = r.title if r else None
        d["qualifications"] = [q.label() for q in self.qualifications_at(now())]
        return d


class CrewMember(Employee):
    prefix = "CRW"
    max_duty_hours = 13

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality, staff_number, base)
        self.position_location = base      # where the crew member physically is (positioning)

    def holds_qualification(self, kind, subject_code, at=None):
        t = at or now()
        return any(q.kind == kind and q.subject_code == subject_code for q in self.qualifications_at(t))

    def qualified_for(self, aircraft_type, at=None):
        raise NotImplementedError

    def assignments_on(self, date):
        return [a for a in self.registry.all(CrewAssignment)
                if a.crew is self and a.flight.date == date and a.is_current()]

    def duty_hours_on(self, date):
        return sum(a.flight.block_hours() if hasattr(a.flight, "block_hours") else 2 for a in self.assignments_on(date))


class FlightDeckCrew(CrewMember):
    prefix = "FDC"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base, licence_number):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality, staff_number, base)
        self.licence_number = licence_number

    def qualified_for(self, aircraft_type, at=None):
        # pilots need a TYPE RATING on the exact type
        return self.holds_qualification("type_rating", aircraft_type.code, at)


class CabinCrew(CrewMember):
    prefix = "CAB"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base, languages):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality, staff_number, base)
        self.languages = languages

    def qualified_for(self, aircraft_type, at=None):
        # cabin crew need a cabin (safety & emergency procedures) qualification on the type
        return self.holds_qualification("cabin_type", aircraft_type.code, at)


class MaintenanceEngineer(Employee):
    prefix = "ENG"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base, authorisation):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality, staff_number, base)
        self.authorisation = authorisation   # e.g. "B1" airframe/engines, "B2" avionics

    def can_certify(self, aircraft_type):
        return self.holds_qualification("certifying", aircraft_type.code)

    def holds_qualification(self, kind, subject_code, at=None):
        t = at or now()
        return any(q.kind == kind and q.subject_code == subject_code for q in self.qualifications_at(t))


class GroundStaff(Employee):
    prefix = "GND"

    def __init__(self, registry, first_name, last_name, date_of_birth, nationality, staff_number, base, department):
        super().__init__(registry, first_name, last_name, date_of_birth, nationality, staff_number, base)
        self.department = department          # dispatch | ramp | check_in | cargo | ops_control


class RoleAssignment(TemporalRecord):
    """A job title held for a period.  Promotion ends the old one and opens a
    new one; nothing is overwritten."""
    prefix = "ROL"

    def __init__(self, registry, employee, title, department):
        super().__init__(registry)
        self.employee = employee
        self.title = title
        self.department = department

    def label(self):
        return f"{self.employee.label()} as {self.title}"


class Qualification(TemporalRecord):
    """A dated certificate: type rating, cabin-type qualification, licence,
    certifying-staff authorisation, medical.  Expiry or revocation ends the
    validity period; the record remains so old assignments stay explainable."""
    prefix = "QUA"

    def __init__(self, registry, holder, kind, subject_code, issued_by, expires=None):
        super().__init__(registry, valid_to=expires)
        self.holder = holder
        self.kind = kind                # type_rating | cabin_type | licence | certifying | medical
        self.subject_code = subject_code
        self.issued_by = issued_by

    def label(self):
        return f"{self.kind}:{self.subject_code}"


class CrewAssignment(TemporalRecord):
    """One crew member in one position on one flight.  A swap ends this record
    (status 'replaced') and creates a new one, keeping the original visible."""
    prefix = "CAS"

    def __init__(self, registry, flight, crew, position, role_title):
        super().__init__(registry, status="assigned")
        self.flight = flight
        self.crew = crew
        self.position = position          # CP | FO | SCCM | CC
        self.role_title = role_title      # the title held WHEN assigned (frozen on purpose)
        self.replaced_by = None

    def label(self):
        return f"{self.crew.label()} {self.position} on {self.flight.label()}"


class DutyPeriod(TemporalRecord):
    """A rostered block of duty or rest; used to check availability."""
    prefix = "DTY"

    def __init__(self, registry, crew, kind, valid_from, valid_to, location):
        super().__init__(registry, valid_from=valid_from, valid_to=valid_to)
        self.crew = crew
        self.kind = kind                  # duty | rest | standby | leave
        self.location = location

    def label(self):
        return f"{self.crew.label()} {self.kind} {self.valid_from:%H:%M}-{self.valid_to:%H:%M}"
