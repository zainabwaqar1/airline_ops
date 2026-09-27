"""Introspection used by the frontend's Design tab and by main.py: which
classes exist, what each inherits from, and which operations exist with
their parameters.  Nothing here is hand-maintained, so the counts are honest."""
import inspect
from .core import Record
from . import fleet, network, people, commercial, baggage, cargo, maintenance, disruption
from .operations import OPERATIONS

MODULES = [fleet, network, people, commercial, baggage, cargo, maintenance, disruption]


def _all_record_classes():
    seen = {}
    def walk(cls):
        for sub in cls.__subclasses__():
            seen[sub.__name__] = sub
            walk(sub)
    walk(Record)
    return seen


def class_catalogue():
    out = []
    for name, cls in _all_record_classes().items():
        base = cls.__bases__[0]
        chain = []
        c = cls
        while c is not Record and c is not object:
            chain.append(c.__name__)
            c = c.__bases__[0]
        out.append({
            "name": name,
            "module": cls.__module__.split(".")[-1],
            "base": base.__name__,
            "depth": len(chain),                    # 1 = directly under Record
            "doc": (cls.__doc__ or "").strip().split("\n")[0],
            "prefix": cls.prefix,
        })
    return sorted(out, key=lambda c: (c["module"], c["depth"], c["name"]))


def inheritance_tree():
    classes = _all_record_classes()
    def node(cls):
        kids = [node(k) for k in cls.__subclasses__() if k.__name__ in classes or cls is Record]
        return {"name": cls.__name__, "children": sorted(kids, key=lambda k: k["name"])}
    return node(Record)


def operation_catalogue():
    out = {}
    for area, fns in OPERATIONS.items():
        out[area] = []
        for fn in fns:
            sig = inspect.signature(fn)
            params = []
            for p in list(sig.parameters.values())[1:]:     # skip `reg`
                params.append({"name": p.name,
                               "required": p.default is inspect.Parameter.empty,
                               "default": None if p.default is inspect.Parameter.empty else repr(p.default)})
            out[area].append({"name": fn.__name__, "doc": (fn.__doc__ or "").strip(), "params": params})
    return out
