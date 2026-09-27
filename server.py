"""
Tiny HTTP server (Python standard library only - nothing to install).

    python server.py            then open  http://localhost:8000

Serves the JavaScript frontend from ./frontend and exposes the Python model
as JSON:

  GET  /api/meta               classes, inheritance tree, operations, demos
  GET  /api/state              every record (except individual seats) + journal
  GET  /api/record/<id>        one record with its full event history
  GET  /api/report             end-of-day explanation
  POST /api/reset              rebuild the seeded day
  POST /api/demo/<name>        run one scenario demo on the current state
  POST /api/demo-all           reset, run every demo in order, return stories
  POST /api/op/<name>          run one business operation with JSON arguments
"""
import json
import os
import threading
from datetime import date, datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from airline.core import DomainError, fmt
from airline.seed import build
from airline import demos as demo_module
from airline.report import end_of_day
from airline.meta import class_catalogue, inheritance_tree, operation_catalogue
from airline import operations as op_module

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(HERE, "frontend")

STATE = {"reg": None, "handles": None, "demo_results": []}
LOCK = threading.Lock()


def reset():
    reg, handles = build()
    STATE["reg"], STATE["handles"], STATE["demo_results"] = reg, handles, []


def coerce(value):
    """Turn the strings the HTML form sends into the types operations expect."""
    if not isinstance(value, str):
        return value
    v = value.strip()
    if v == "":
        return None
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if v[0] in "[{":
        try:
            return json.loads(v)
        except ValueError:
            return v
    for fmt_ in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(v, fmt_)
        except ValueError:
            pass
    try:
        return date.fromisoformat(v)
    except ValueError:
        pass
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def snapshot(reg):
    snap = reg.snapshot()
    seats = snap["records"].pop("Seat", [])
    snap["seat_count"] = len(seats)
    return snap


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONTEND, **kw)

    def log_message(self, *a):        # quieter console
        pass

    # ---- helpers ------------------------------------------------------
    def send_json(self, payload, code=200):
        body = json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- GET ----------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            if path == "/":
                self.path = "/index.html"
            return super().do_GET()
        with LOCK:
            reg = STATE["reg"]
            if path == "/api/meta":
                return self.send_json({
                    "classes": class_catalogue(), "tree": inheritance_tree(), "operations": operation_catalogue(),
                    "demos": [{"name": d.__name__, "title": d.__doc__} for d in demo_module.DEMOS],
                })
            if path == "/api/state":
                return self.send_json(snapshot(reg))
            if path == "/api/report":
                return self.send_json(end_of_day(reg))
            if path.startswith("/api/record/"):
                rid = path.split("/")[-1]
                try:
                    r = reg.get(rid)
                except KeyError:
                    return self.send_json({"error": f"no record {rid}"}, 404)
                return self.send_json({"record": r.to_dict(), "events": [e.to_dict() for e in r.events]})
            if path == "/api/demo-results":
                return self.send_json(STATE["demo_results"])
        self.send_json({"error": "unknown endpoint"}, 404)

    # ---- POST ---------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path
        with LOCK:
            reg = STATE["reg"]
            if path == "/api/reset":
                reset()
                return self.send_json({"ok": True})
            if path == "/api/demo-all":
                reset()
                STATE["demo_results"] = demo_module.run_all(STATE["reg"], STATE["handles"])
                return self.send_json({"ok": True, "results": STATE["demo_results"], "clock": fmt(__import__("airline.core", fromlist=["now"]).now())})
            if path.startswith("/api/demo/"):
                name = path.split("/")[-1]
                fn = next((d for d in demo_module.DEMOS if d.__name__ == name), None)
                if fn is None:
                    return self.send_json({"error": f"no demo {name}"}, 404)
                before = len(reg.journal)
                try:
                    story = fn(reg, STATE["handles"])
                except DomainError as e:
                    return self.send_json({"ok": False, "error": str(e)}, 400)
                result = {"name": name, "title": fn.__doc__, "story": story,
                          "events": [e.to_dict() for e in reg.journal[before:]]}
                STATE["demo_results"].append(result)
                return self.send_json({"ok": True, "result": result})
            if path.startswith("/api/op/"):
                name = path.split("/")[-1]
                fn = None
                for fns in op_module.OPERATIONS.values():
                    fn = next((f for f in fns if f.__name__ == name), fn)
                if fn is None:
                    return self.send_json({"error": f"no operation {name}"}, 404)
                args = {k: coerce(v) for k, v in self.read_json().items()}
                args = {k: v for k, v in args.items() if v is not None}
                before = len(reg.journal)
                try:
                    result = fn(reg, **args)
                except DomainError as e:
                    return self.send_json({"ok": False, "refused": str(e),
                                           "events": [x.to_dict() for x in reg.journal[before:]]}, 200)
                except (KeyError, LookupError, TypeError, ValueError, AttributeError) as e:
                    return self.send_json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 400)
                def describe(r):
                    if hasattr(r, "label"):
                        return {"id": r.id, "label": r.label(), "type": type(r).__name__, "status": r.status}
                    if isinstance(r, (list, tuple)):
                        return [describe(x) for x in r]
                    return str(r)
                return self.send_json({"ok": True, "result": describe(result),
                                       "events": [x.to_dict() for x in reg.journal[before:]]})
        self.send_json({"error": "unknown endpoint"}, 404)

def local_ip():
    """The address other devices on the same Wi-Fi can use to reach this computer."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))          # no data is sent; this just picks the right interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def main():
    reset()
    port = int(os.environ.get("PORT", 8000))
    print(f"Airline operations model running:")
    print(f"  on this computer:   http://localhost:{port}")
    ip = local_ip()
    if ip:
        print(f"  on your phone:      http://{ip}:{port}   (same Wi-Fi)")
    print("(Ctrl+C to stop)")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
