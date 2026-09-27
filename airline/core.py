"""
Core building blocks shared by every business record.

Design rules embodied here (see docs/assumptions.md):
  * Nothing is ever deleted.  A record changes status (cancelled, retired,
    superseded, archived ...) and keeps its full event history.
  * Every status change is written to an Event, both on the record itself and
    in the registry-wide journal, so an end-of-day explanation can be produced.
  * Records that are only true for a period of time (a qualification, a cabin
    configuration, a crew assignment) extend TemporalRecord so historical
    queries can ask "what was true at 05:30?".
"""
from datetime import datetime, timedelta

# --------------------------------------------------------------------------
# Simulated operational clock (the demos move through one operating day)
# --------------------------------------------------------------------------
_clock = {"now": datetime(2026, 9, 24, 4, 0)}


def now():
    return _clock["now"]


def set_clock(dt):
    _clock["now"] = dt


def advance(minutes):
    _clock["now"] = _clock["now"] + timedelta(minutes=minutes)
    return _clock["now"]


def fmt(dt):
    return dt.strftime("%H:%M") if isinstance(dt, datetime) else str(dt)


# --------------------------------------------------------------------------
# Event: one immutable line of operational history
# --------------------------------------------------------------------------
class Event:
    _seq = 0

    def __init__(self, subject, action, detail="", actor="system"):
        Event._seq += 1
        self.id = Event._seq
        self.at = now()
        self.subject_id = subject.id
        self.subject_type = type(subject).__name__
        self.subject_label = subject.label()
        self.action = action
        self.detail = detail
        self.actor = actor

    def to_dict(self):
        return {
            "id": self.id, "at": self.at.isoformat(), "time": fmt(self.at),
            "subject_id": self.subject_id, "subject_type": self.subject_type,
            "subject_label": self.subject_label, "action": self.action,
            "detail": self.detail, "actor": self.actor,
        }


# --------------------------------------------------------------------------
# Registry: the in-memory "database"
# --------------------------------------------------------------------------
class Registry:
    def __init__(self):
        self.items = {}
        self.journal = []
        self.counters = {}

    def next_id(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}-{n:03d}"

    def add(self, rec):
        self.items[rec.id] = rec

    def get(self, rec_id):
        rec = self.items.get(rec_id)
        if rec is None:
            raise KeyError(f"No record with id {rec_id!r}")
        return rec

    def all(self, cls=None):
        if cls is None:
            return list(self.items.values())
        return [r for r in self.items.values() if isinstance(r, cls)]

    def find(self, cls, **criteria):
        out = []
        for r in self.all(cls):
            if all(getattr(r, k, None) == v for k, v in criteria.items()):
                out.append(r)
        return out

    def one(self, cls, **criteria):
        found = self.find(cls, **criteria)
        if not found:
            raise LookupError(f"No {cls.__name__} matching {criteria}")
        return found[0]

    def snapshot(self):
        """Every record grouped by concrete class name, plus the journal."""
        groups = {}
        for r in self.items.values():
            groups.setdefault(type(r).__name__, []).append(r.to_dict())
        return {"clock": now().isoformat(), "records": groups,
                "journal": [e.to_dict() for e in self.journal]}


# --------------------------------------------------------------------------
# Record: base of every business object
# --------------------------------------------------------------------------
def _plain(value):
    """Convert attribute values into JSON-friendly data, replacing record
    references by their ids so the graph is not serialised recursively."""
    if isinstance(value, Record):
        return value.id
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return value


class Record:
    prefix = "REC"

    def __init__(self, registry, status="active"):
        self.registry = registry
        self.id = registry.next_id(self.prefix)
        self.status = status
        self.created_at = now()
        self.events = []
        registry.add(self)

    # -- history -----------------------------------------------------------
    def log(self, action, detail="", actor="system"):
        e = Event(self, action, detail, actor)
        self.events.append(e)
        self.registry.journal.append(e)
        return e

    def set_status(self, new_status, reason="", actor="system"):
        old = self.status
        if old == new_status:
            return
        self.status = new_status
        self.log("status", f"{old} -> {new_status}" + (f": {reason}" if reason else ""), actor)

    def archive(self, reason="", actor="system"):
        self.set_status("archived", reason, actor)

    # -- presentation ------------------------------------------------------
    def label(self):
        return self.id

    def to_dict(self):
        d = {"type": type(self).__name__, "label": self.label()}
        for k, v in self.__dict__.items():
            if k in ("registry", "events"):
                continue
            d[k] = _plain(v)
        d["event_count"] = len(self.events)
        return d

    def __repr__(self):
        return f"<{type(self).__name__} {self.label()} [{self.status}]>"


class TemporalRecord(Record):
    """A record that is true for a period.  valid_to is None while current.

    Used for anything the airline must be able to ask "what was in force at
    time T?" about: configurations, qualifications, roles, assignments,
    airport restrictions.  Ending the period never deletes the record.
    """
    prefix = "TMP"

    def __init__(self, registry, valid_from=None, valid_to=None, status="active"):
        super().__init__(registry, status)
        self.valid_from = valid_from or now()
        self.valid_to = valid_to

    def is_valid_at(self, t):
        return self.valid_from <= t and (self.valid_to is None or t < self.valid_to)

    def is_current(self):
        return self.is_valid_at(now())

    def end(self, reason="", new_status="ended", actor="system"):
        if self.valid_to is None:
            self.valid_to = now()
        self.set_status(new_status, reason, actor)


class DomainError(Exception):
    """A business rule refused an operation.  The refusal itself is logged by
    the operation so that 'what was attempted and rejected' is part of the
    day's history."""
