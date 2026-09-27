"""Engineering and maintenance.

Second inheritance structure discovered from the domain:

    Record
     └── EngineeringRecord      anything written into the aircraft's technical
          │                     log: who raised it, on which aircraft, which
          │                     engineer certified it
          ├── Inspection        a check performed (pre-departure, A-check ...)
          ├── Defect            a fault found; may be rectified, DEFERRED under
          │                     the MEL, or ground the aircraft
          └── WorkOrder         planned maintenance work with a due time

Deferred defects are a STATUS of Defect with a MEL reference and an expiry, not
a subclass (rejected hierarchy #3): the same defect moves open -> deferred ->
rectified and must stay one record.
"""
from .core import Record, now


class EngineeringRecord(Record):
    prefix = "ENR"

    def __init__(self, registry, aircraft, raised_by, description, status="open"):
        super().__init__(registry, status=status)
        self.aircraft = aircraft
        self.raised_by = raised_by          # MaintenanceEngineer
        self.description = description
        self.certified_by = None
        self.closed_at = None

    def label(self):
        return f"{type(self).__name__} {self.id} {self.aircraft.registration}"

    def close(self, engineer, note=""):
        self.certified_by = engineer
        self.closed_at = now()
        self.set_status("closed", note)


class Inspection(EngineeringRecord):
    prefix = "INS"

    def __init__(self, registry, aircraft, raised_by, description, check_type):
        super().__init__(registry, aircraft, raised_by, description)
        self.check_type = check_type        # pre_departure | daily | A | C
        self.findings = []                  # Defects found during this inspection

    def label(self):
        return f"{self.check_type} check {self.aircraft.registration}"


class Defect(EngineeringRecord):
    prefix = "DEF"

    def __init__(self, registry, aircraft, raised_by, description, ata_chapter, component=None, inspection=None):
        super().__init__(registry, aircraft, raised_by, description)
        self.ata_chapter = ata_chapter      # e.g. "32" landing gear
        self.component = component
        self.inspection = inspection
        self.mel_reference = None           # set when deferred
        self.deferral_expires = None
        self.grounding = False

    def label(self):
        return f"Defect {self.id} {self.aircraft.registration} ATA{self.ata_chapter}"


class WorkOrder(EngineeringRecord):
    prefix = "WOR"

    def __init__(self, registry, aircraft, raised_by, description, due_at, estimated_hours, defect=None):
        super().__init__(registry, aircraft, raised_by, description, status="planned")
        self.due_at = due_at
        self.estimated_hours = estimated_hours
        self.defect = defect
        self.started_at = None

    def label(self):
        return f"WO {self.id} {self.aircraft.registration} due {self.due_at:%H:%M}"
