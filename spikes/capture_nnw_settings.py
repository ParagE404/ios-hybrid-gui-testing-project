# Origin: AI-generated and reviewed by the author.
"""Capture NetNewsWire feeds and Settings (top, after one swipe, bottom) for the held-out scenarios (D-029).

Usage: python spikes/capture_nnw_settings.py OUT_DIR [--perturb FLAG]
"""
import argparse
import time
from pathlib import Path

from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy

B = "uk.ac.city.parag.NetNewsWire.iOS-DEBUG"
p = argparse.ArgumentParser()
p.add_argument("out", type=Path)
p.add_argument("--perturb", action="append", default=[])
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
o = XCUITestOptions(); o.device_name = "iPhone 17"; o.platform_version = "27.0"; o.bundle_id = B
o.new_command_timeout = 120; o.force_app_launch = True; o.should_terminate_app = True
o.process_arguments = {"args": ["-resetData"] + [x for f in a.perturb for x in ("-perturb", f)]}
d = webdriver.Remote("http://127.0.0.1:4723", options=o)


def save(name):
    time.sleep(1.0)
    (a.out / f"{name}.xml").write_text(d.page_source, encoding="utf-8")
    d.get_screenshot_as_file(str(a.out / f"{name}.png"))


try:
    time.sleep(1.5)
    save("feeds")
    d.find_element(AppiumBy.IOS_PREDICATE, "type == 'XCUIElementTypeButton' AND label == 'Settings'").click()
    save("settings")
    d.execute_script("mobile: swipe", {"direction": "up"})
    save("settings_scrolled")
    d.execute_script("mobile: swipe", {"direction": "up"})
    save("settings_bottom")
finally:
    d.quit()
