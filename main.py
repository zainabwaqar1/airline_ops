"""
Run the whole operating day in the terminal (no browser needed):

    python main.py

Seeds the day, runs all scenario demos in order, prints each story, and then
prints the end-of-day report.  Use `python main.py --json` for raw JSON.
"""
import json
import sys
from airline.seed import build
from airline.demos import run_all
from airline.report import end_of_day
from airline.meta import class_catalogue, operation_catalogue


def main():
    reg, handles = build()
    results = run_all(reg, handles)
    report = end_of_day(reg)
    if "--json" in sys.argv:
        print(json.dumps({"demos": results, "report": report}, indent=2, default=str))
        return

    print("=" * 78)
    print("INTEGRATED AIRLINE OPERATIONS - THURSDAY 24 SEP 2026")
    print("=" * 78)
    for r in results:
        print()
        print(f"--- {r['name']}")
        print(f"    {r['title']}")
        for line in r["story"]:
            tag = {"step": "  ", "refused": "!!", "check": "=>"}[line["kind"]]
            print(f"  {line['time']} {tag} {line['text']}")

    print()
    print("=" * 78)
    print("END OF DAY REPORT")
    print("=" * 78)
    for f in report["flights"]:
        print(f"{f['flight']:<12} {f['route']:<8} {f['status']:<15} STD {f['std']} ETD {f['etd']} (+{f['delay_min']})  "
              f"aircraft: {' -> '.join(f['aircraft_chain']) or '-'}")
        print(f"             pax {f['passengers_by_status']}  bags {f['bags']}  cargo {f['cargo_loads']}")
    print()
    print("Disruptions:")
    for d in report["disruptions"]:
        print(f"  {d['declared']} {d['type']:<21} {d['flight']:<12} {d['reason']} {d['description']}")
        print(f"        -> {d['resolution']}; affected {len(d['affected'])} records")
    print()
    print("Refused attempts (business rules that fired):")
    for e in report["refused_attempts"]:
        print(f"  {e['time']} {e['subject_label']}: {e['detail']}")
    print()
    print("Open items at close of day:")
    for o in report["open_items"]:
        print("  - " + o)
    print()
    cls = class_catalogue()
    ops = operation_catalogue()
    print(f"Classes: {len(cls)}   Operations: {sum(len(v) for v in ops.values())}   "
          f"Records: {report['totals']['records']}   Events: {report['totals']['events']}")


if __name__ == "__main__":
    main()
