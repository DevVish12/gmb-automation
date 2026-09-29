#!/usr/bin/env python3
"""Seed realistic DEMO data for testing the GMB Automation Platform.

Creates one demo client ("Sharma Dental Clinic", Pune) with keywords, audit,
content calendar, queue drafts, reviews, media, competitors and tracker history.

Usage:
    python seed_demo.py            # create demo data (fails if demo client exists)
    python seed_demo.py --reset    # delete existing demo data first, then recreate

Run with the Flask app STOPPED (both write to the same SQLite DB).
Then start the app:  python app.py  ->  http://127.0.0.1:5003

TIP: you can also do this from the UI — Settings -> Demo data -> "Add demo client".

All data is clearly dummy — for testing/demo only, not real business data.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import yaml
from gmb.tracker import Tracker
from gmb import seed as seed_mod

CFG = yaml.safe_load(open(BASE_DIR / "config.yaml"))
tracker = Tracker(str(BASE_DIR / CFG["app"].get("db_path", "gmb_automation.db")))

RESET = "--reset" in sys.argv


def main():
    if RESET:
        seed_mod.reset_demo_data(tracker)
        print("Old demo data cleared.")
    try:
        summary = seed_mod.seed_demo_data(tracker, CFG.get("posting", {}) or {})
    except ValueError as e:
        print(f"{e}  (use --reset to recreate)")
        return
    print(f"Demo client created: {summary['name']} (slug: {summary['slug']})")
    print(f"  audit score {summary['audit_score']}, {summary['keywords']} keywords, "
          f"{summary['calendar_slots']} calendar slots, {summary['queue_drafts']} drafts, "
          f"{summary['reviews']} reviews, {summary['media']} media, "
          f"{summary['competitors']} competitors, {summary['activities']} activities")
    print("\nDone! Start the app (python app.py) and open http://127.0.0.1:5003")
    print("NOTE: all data is dummy, for testing/demo only.")


if __name__ == "__main__":
    main()
