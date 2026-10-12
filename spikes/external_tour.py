"""Tour the external apps (SyncUps, NetNewsWire) and save page source + screenshot per screen.

Origin: original,  Spike only, not part of
the engine. Every launch passes -resetData (apps/external/<app>.patch), so state is seeded.

Usage (Appium running, apps installed):
    python spikes/external_tour.py syncups --out-dir benchmark/pagesource/syncups/baseline
    python spikes/external_tour.py netnewswire --determinism   # two launches, compare page source
"""

import argparse
import re
import time
from pathlib import Path

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

BUNDLES = {"syncups": "co.pointfree.SyncUps", "netnewswire": "uk.ac.city.parag.NetNewsWire.iOS-DEBUG"}


def P(pred):
    return (AppiumBy.IOS_PREDICATE, pred)


def button(label_pred):
    return P(f"type == 'XCUIElementTypeButton' AND {label_pred}")


def cell(label_pred):
    return P(f"type == 'XCUIElementTypeCell' AND {label_pred}")


# Each step: ("capture", name) | ("tap", [locators]) | ("back",) | ("alert",) dismiss any alert
# | ("swipe", direction). Locators list fallbacks so the tour works under every perturbation flag.
ID = AppiumBy.ACCESSIBILITY_ID
TOURS = {
    "syncups": [
        ("capture", "list"),
        ("tap", [button("label == 'Add'"), (ID, "plus"), (ID, "plus.circle")]), ("capture", "new_syncup"),
        ("tap", [button("label == 'Dismiss'")]),
        ("tap", [button("label BEGINSWITH 'Design'"), button("label CONTAINS ', 6, 1 min'")]), ("capture", "detail"),
        ("tap", [button("label == 'Edit'")]), ("capture", "edit"),
        ("tap", [(ID, "button_3"), button("label == 'Theme'")]), ("capture", "theme_menu"),
        ("tap", [button("label == 'Orange'")]),                      # re-select the current theme
        ("tap", [button("label == 'Cancel'")]),
        ("back",),
        ("tap", [button("label BEGINSWITH 'Engineering'"), button("label CONTAINS ', 2, 10 min'")]),
        ("swipe", "up"), ("capture", "detail_delete"),
        ("tap", [button("label == 'Delete'"), (ID, "button_9")]), ("capture", "delete_alert"),
        ("tap", [button("label == 'Nevermind'"), button("label == 'Cancel'")]),
    ],
    "netnewswire": [
        ("capture", "feeds"),
        ("tap", [(ID, "addButton"), (ID, "addFeedOrFolderButton"), (ID, "button_5")]), ("capture", "add_menu"),
        ("tap", [button("label BEGINSWITH 'Add Folder'")]), ("capture", "add_folder"),
        ("tap", [button("label == 'Cancel'")]),
        ("tap", [(ID, "settingsButton"), (ID, "button_6"), button("label == 'Settings'")]), ("capture", "settings"),
        ("tap", [button("label == 'Done'")]),
        ("tap", [cell("label == 'Today'"), cell("label == 'Smart Feed'")]), ("capture", "today_timeline"),
    ],
}

KEYBOARD_KEYS = {"shift", "return", "Emoji", "Dictate", "delete", "space", "Next keyboard", "more", "Return"}
CONTROL_TYPES = ("Button", "Cell", "TextField", "SecureTextField", "Switch", "Slider", "SearchField",
                 "SegmentedControl", "Stepper", "MenuItem", "Link", "TextView")


def main_controls(xml: str) -> list[str]:
    """Interactive elements with a name or label, for the report (deduplicated, in order)."""
    out, seen = [], set()
    for t, attrs in re.findall(r"<XCUIElementType(\w+)( [^>]*)>", xml):
        if t not in CONTROL_TYPES or 'visible="true"' not in attrs:
            continue
        lab = re.search(r' label="([^"]*)"', attrs)
        name = re.search(r' name="([^"]*)"', attrs)
        ph = re.search(r' placeholderValue="([^"]*)"', attrs)
        text = next((m.group(1) for m in (lab, name, ph) if m and m.group(1)), "").strip()
        if text in KEYBOARD_KEYS or (t == "Button" and len(text) == 1):
            continue
        if text and (t, text) not in seen:
            seen.add((t, text))
            out.append(f"{t}:{text}")
    return out


def session(app, device, platform_version, server, perturb=()):
    o = XCUITestOptions()
    o.device_name, o.platform_version, o.bundle_id = device, platform_version, BUNDLES[app]
    o.force_app_launch = o.should_terminate_app = True
    o.process_arguments = {"args": ["-resetData"] + [a for f in perturb for a in ("-perturb", f)]}
    o.new_command_timeout = 120
    return webdriver.Remote(server, options=o)


def first(d, locators):
    for by, value in locators:
        found = d.find_elements(by, value)
        if found:
            return found[0]
    raise LookupError(f"none of {locators} found")


def dismiss_alert(d):
    for label in ("Don’t Allow", "Don't Allow", "Cancel", "OK"):
        try:
            d.execute_script("mobile: alert", {"action": "dismiss", "buttonLabel": label})
            time.sleep(0.8)
            return label
        except Exception:
            continue
    return None


def tour(app, d, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for step in TOURS[app]:
        kind = step[0]
        if kind == "capture":
            time.sleep(1.0)
            xml = d.page_source
            (out / f"{step[1]}.xml").write_text(xml, encoding="utf-8")
            d.get_screenshot_as_file(str(out / f"{step[1]}.png"))
            print(f"[{step[1]}] " + " | ".join(main_controls(xml)))
        elif kind == "tap":
            first(d, step[1]).click()
            time.sleep(0.8)
        elif kind == "back":
            d.back()
            time.sleep(0.8)
        elif kind == "swipe":
            d.execute_script("mobile: swipe", {"direction": step[1]})
            time.sleep(1.0)
        elif kind == "alert":
            time.sleep(1.5)
            print(f"  (alert dismissed: {dismiss_alert(d)})")


def determinism(app, args):
    """Launch twice with -resetData; the first screen's page source must be byte-identical."""
    sources = []
    for _ in range(2):
        d = session(app, args.device, args.platform_version, args.server)
        try:
            time.sleep(2.0)
            # processId is per-launch Appium metadata, not UI; everything else must match.
            sources.append(re.sub(r' processId="\d+"', "", d.page_source))
        finally:
            d.quit()
    same = sources[0] == sources[1]
    print(f"determinism {app}: identical={same} chars={len(sources[0])},{len(sources[1])}")
    if not same:
        a, b = sources[0].splitlines(), sources[1].splitlines()
        for x, y in zip(a, b):
            if x != y:
                print("  first difference:\n   ", x.strip()[:200], "\n   ", y.strip()[:200])
                break


def main():
    p = argparse.ArgumentParser()
    p.add_argument("app", choices=sorted(TOURS))
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--determinism", action="store_true")
    p.add_argument("--perturb", action="append", default=[], help="perturbation flag (repeatable)")
    p.add_argument("--device", default="iPhone 17")
    p.add_argument("--platform-version", default="27.0")
    p.add_argument("--server", default="http://127.0.0.1:4723")
    a = p.parse_args()
    if a.determinism:
        determinism(a.app, a)
        return
    d = session(a.app, a.device, a.platform_version, a.server, a.perturb)
    try:
        tour(a.app, d, a.out_dir or Path(f"benchmark/pagesource/{a.app}/baseline"))
    finally:
        d.quit()


if __name__ == "__main__":
    main()
