"""Spike 1: Appium/XCUITest smoke test.

Connects to a running Appium server, opens an app on an iOS simulator, saves the
page source and a screenshot, and times page-source retrieval. The timing is the
first evidence for the "snapshot latency" risk in the proposal.

With --tour (Errands testbed only) it instead walks every screen and saves
<screen>.xml and <screen>.png for each, so scenario locators and labels can be
checked against real page source. --perturb passes "-perturb <flag>" launch args.

Usage:
    appium                      # in another terminal
    python spikes/appium_smoke.py --device "iPhone 16" [--bundle com.apple.Preferences]
    python spikes/appium_smoke.py --device "iPhone 17" --bundle uk.ac.city.parag.Errands \
        --tour --perturb tb05_duplicate_delete --out-dir benchmark/pagesource/tb05_duplicate_delete
"""

import argparse
import statistics
import time
from pathlib import Path

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

OUT = Path(__file__).parent / "out"


def first(driver, locators):
    """Return the first element found by any (by, value) locator; raise if none match."""
    for by, value in locators:
        found = driver.find_elements(by, value)
        if found:
            return found[0]
    raise LookupError(f"none of {locators} found")


def button(label_pred):
    return (AppiumBy.IOS_PREDICATE, f"type == 'XCUIElementTypeButton' AND {label_pred}")


def tour(driver, out: Path) -> None:
    """Walk the Errands screens using locators that survive every perturbation flag."""
    def save(name):
        time.sleep(0.8)  # let animations settle
        (out / f"{name}.xml").write_text(driver.page_source, encoding="utf-8")
        driver.get_screenshot_as_file(str(out / f"{name}.png"))
        print(f"  saved {name}")

    tab_list = [button("label == 'List'")]
    tab_settings = [button("label == 'Settings'")]
    add = [(AppiumBy.ACCESSIBILITY_ID, "addItemButton"), (AppiumBy.ACCESSIBILITY_ID, "addButton_v2"),
           button("label == 'Add item'")]
    cancel = [(AppiumBy.ACCESSIBILITY_ID, "cancelButton"), button("label == 'Cancel'")]  # p06 drops the id
    edit = [(AppiumBy.ACCESSIBILITY_ID, "editButton"), (AppiumBy.ACCESSIBILITY_ID, "button_12")]  # p04 icon

    save("list")

    first(driver, [(AppiumBy.ACCESSIBILITY_ID, "sortMenu")]).click()
    save("sort_menu")
    first(driver, [button("label == 'By name'")]).click()  # default order, so state is unchanged

    first(driver, add).click()
    save("add_form")
    first(driver, cancel).click()

    first(driver, [button("label BEGINSWITH 'Milk'")]).click()
    save("detail")
    first(driver, edit).click()
    save("edit_form")
    first(driver, cancel).click()
    time.sleep(0.5)
    driver.back()

    first(driver, tab_settings).click()
    save("settings")
    first(driver, [(AppiumBy.ACCESSIBILITY_ID, "resetButton")]).click()
    save("reset_alert")
    first(driver, [(AppiumBy.IOS_CLASS_CHAIN,
                    "**/XCUIElementTypeAlert/**/XCUIElementTypeButton[`label == 'Cancel'`]")]).click()
    first(driver, tab_list).click()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--device", required=True, help="Simulator name, e.g. 'iPhone 16'")
    p.add_argument("--platform-version", default=None, help="e.g. '18.5' (optional)")
    p.add_argument("--bundle", default="com.apple.Preferences", help="Bundle id of the app to open")
    p.add_argument("--server", default="http://127.0.0.1:4723")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--perturb", action="append", default=[], help="Errands perturbation flag (repeatable)")
    p.add_argument("--out-dir", type=Path, default=OUT)
    p.add_argument("--tour", action="store_true", help="Errands only: save every screen")
    args = p.parse_args()

    opts = XCUITestOptions()
    opts.device_name = args.device
    if args.platform_version:
        opts.platform_version = args.platform_version
    opts.bundle_id = args.bundle
    opts.new_command_timeout = 120
    # Relaunch on every session so launch arguments take effect and the seeded data is fresh.
    opts.force_app_launch = True
    opts.should_terminate_app = True
    if args.perturb:
        opts.process_arguments = {"args": [a for f in args.perturb for a in ("-perturb", f)]}

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    driver = webdriver.Remote(args.server, options=opts)
    print(f"session start: {time.perf_counter() - t0:.1f}s")

    try:
        if args.tour:
            tour(driver, out)
            return
        timings = []
        source = ""
        for _ in range(args.repeats):
            t = time.perf_counter()
            source = driver.page_source
            timings.append((time.perf_counter() - t) * 1000)
        (out / "page_source.xml").write_text(source, encoding="utf-8")
        driver.get_screenshot_as_file(str(out / "screenshot.png"))
        size = driver.get_window_size()

        print(f"page_source ms: median={statistics.median(timings):.0f} "
              f"min={min(timings):.0f} max={max(timings):.0f} (n={len(timings)})")
        print(f"page_source size: {len(source):,} chars, elements~{source.count('<XCUIElementType'):,}")
        print(f"window (points): {size}")
        print(f"saved: {out / 'page_source.xml'} and {out / 'screenshot.png'}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
