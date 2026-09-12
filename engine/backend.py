"""Execution backends: Appium XCUITest (real) and a fake (tests).

Origin: original,  The Appium
backend uses the Appium Python client and XCUITest 'mobile:' commands
(Appium Project, 2026a). Verified on an iOS 27.0 simulator (18 Oct 2026) for tap,
type_text, back, scripted and reset; swipe and screenshot_png not yet exercised live.

All configurations act through the same primitives, so differences in results come
from how the target was chosen, not from how it was executed:
  - structured and VLM routes tap at screen coordinates (element centre or model point)
  - the scripted baseline finds the element by its fixed locator and taps it
"""

from __future__ import annotations

import time
from typing import Optional, Protocol

from .normalise import parse_page_source
from .model import Snapshot


class Backend(Protocol):
    def snapshot(self) -> Snapshot: ...
    def screenshot_png(self) -> bytes: ...
    def tap(self, x: float, y: float) -> None: ...
    def type_text(self, x: float, y: float, text: str) -> None: ...
    def swipe(self, direction: str) -> None: ...
    def back(self) -> None: ...
    def wait(self, seconds: float) -> None: ...
    def scripted(self, locator: dict, action: str, text: Optional[str]) -> bool: ...
    def reset(self, launch_args: list[str]) -> None: ...


class AppiumBackend:
    def __init__(self, driver, bundle_id: str, settle_s: float = 0.5):
        self.d = driver
        self.bundle_id = bundle_id
        self.settle_s = settle_s

    # -- observation
    def snapshot(self) -> Snapshot:
        t = time.perf_counter()
        xml = self.d.page_source
        return parse_page_source(xml, retrieval_ms=(time.perf_counter() - t) * 1000)

    def screenshot_png(self) -> bytes:
        return self.d.get_screenshot_as_png()

    # -- actions
    def _settle(self):
        time.sleep(self.settle_s)

    def tap(self, x, y):
        self.d.execute_script("mobile: tap", {"x": x, "y": y})
        self._settle()

    def type_text(self, x, y, text, keyboard_timeout_s: float = 2.0):
        # Tap to focus, then type into whatever now has focus. WDA 16.16 on iOS 27 has no
        # hasKeyboardFocus attribute, so the old "hasKeyboardFocus == 1" predicate never
        # matched; the active element is the field the tap focused.
        self.d.execute_script("mobile: tap", {"x": x, "y": y})
        deadline = time.perf_counter() + keyboard_timeout_s
        while not self.d.is_keyboard_shown() and time.perf_counter() < deadline:
            time.sleep(0.1)
        self.d.switch_to.active_element.send_keys(text)
        self._settle()

    def swipe(self, direction):
        self.d.execute_script("mobile: swipe", {"direction": direction})
        self._settle()

    def back(self):
        self.d.back()
        self._settle()

    def wait(self, seconds):
        time.sleep(seconds)

    def scripted(self, locator, action, text):
        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.common.exceptions import WebDriverException
        by = {"accessibility_id": AppiumBy.ACCESSIBILITY_ID, "xpath": AppiumBy.XPATH,
              "predicate": AppiumBy.IOS_PREDICATE, "class_chain": AppiumBy.IOS_CLASS_CHAIN}[locator["strategy"]]
        try:
            el = self.d.find_element(by, locator["value"])
            r = el.rect
            if el.get_attribute("type") == "XCUIElementTypeSwitch" and r["width"] > 120:
                # Same activation rule as Element.tap_point, so scripted is not disadvantaged.
                self.d.execute_script("mobile: tap", {"x": r["x"] + r["width"] - 32,
                                                      "y": r["y"] + r["height"] / 2})
            else:
                el.click()
            if action == "type_text":
                el.send_keys(text)
        except WebDriverException:
            return False
        self._settle()
        return True

    def reset(self, launch_args):
        self.d.execute_script("mobile: terminateApp", {"bundleId": self.bundle_id})
        self.d.execute_script("mobile: launchApp", {"bundleId": self.bundle_id, "arguments": launch_args})
        time.sleep(1.0)


class FakeBackend:
    """Screen-graph simulator for tests: tapping an element by label moves between screens."""

    def __init__(self, screens: dict[str, str], start: str, transitions: dict[tuple[str, str], str],
                 locators: Optional[dict[str, str]] = None):
        self.screens, self.current, self.start = screens, start, start
        self.transitions = transitions          # (screen, tapped label or identifier) -> next screen
        self.locators = locators or {}          # scripted locator value -> label on current screen
        self.actions: list[dict] = []

    def snapshot(self):
        return parse_page_source(self.screens[self.current], retrieval_ms=0.0)

    def screenshot_png(self):
        return b"\x89PNG fake"

    def _hit(self, x, y):
        snap = self.snapshot()
        hits = [e for e in snap.elements if e.contains(x, y) and e.type not in ("Application", "Window", "Other")]
        return min(hits, key=lambda e: e.area) if hits else None

    def _go(self, el):
        if el is None:
            return
        for key in (el.label, el.name):
            nxt = self.transitions.get((self.current, key))
            if nxt:
                self.current = nxt
                return
        for a in el.ancestors:
            anc = self.snapshot().elements[a]
            for key in (anc.label, anc.name):
                nxt = self.transitions.get((self.current, key))
                if nxt:
                    self.current = nxt
                    return

    def tap(self, x, y):
        el = self._hit(x, y)
        self.actions.append({"tap": el.label if el else None})
        self._go(el)

    def type_text(self, x, y, text):
        el = self._hit(x, y)
        self.actions.append({"type": text, "into": el.label if el else None})
        nxt = self.transitions.get((self.current, f"type:{text}"))
        if nxt:
            self.current = nxt

    def swipe(self, direction):
        self.actions.append({"swipe": direction})

    def back(self):
        self.actions.append({"back": True})
        nxt = self.transitions.get((self.current, "back"))
        if nxt:
            self.current = nxt

    def wait(self, seconds):
        self.actions.append({"wait": seconds})

    def scripted(self, locator, action, text):
        snap = self.snapshot()
        target = [e for e in snap.elements if e.name == locator["value"]]
        if not target:
            return False
        e = target[0]
        cx, cy = e.tap_point
        if action == "type_text":
            self.type_text(cx, cy, text)
        else:
            self.tap(cx, cy)
        return True

    def reset(self, launch_args):
        self.current = self.start
        self.actions.append({"reset": launch_args})
