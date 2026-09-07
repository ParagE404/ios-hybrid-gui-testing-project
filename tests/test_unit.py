"""Unit tests: normalisation, intent parsing, scoring, routing, validation.

Origin: original, 
"""

import pytest

from engine import router as R
from engine.intent import parse_step
from engine.normalise import parse_page_source
from engine.resolver import norm_key, resolve, similarity, tokens
from engine.router import route
from engine.validator import validate

from . import fixtures as F


# ---------------------------------------------------------------- normalise

def test_normalise_structure():
    s = parse_page_source(F.HOME)
    assert (s.width, s.height) == (402, 874)
    types = [el.type for el in s.elements]
    assert types[0] == "Application" and "Cell" in types and "TabBar" in types
    add = next(el for el in s.elements if el.label == "Add item")
    assert add.identifier == "addItemButton"           # name differs from label -> developer id
    assert add.center == (372.0, 77.0)
    nav = s.elements[add.parent]
    assert nav.type == "NavigationBar" and nav.idx in add.ancestors


def test_identifier_absent_when_name_equals_label():
    s = parse_page_source(F.HOME)
    milk = next(el for el in s.elements if el.type == "Cell" and el.label == "Milk")
    assert milk.identifier is None


def test_placeholder_and_value():
    s = parse_page_source(F.ADD_TYPED)
    tf = next(el for el in s.elements if el.type == "TextField")
    assert tf.placeholder == "Item name" and tf.value == "Eggs" and tf.label is None


# ---------------------------------------------------------------- intent

@pytest.mark.parametrize("text,action,target,value,hint,context", [
    ("Tap the 'Add item' button", "tap", "Add item", None, "button", None),
    ("Tap ‘Delete’ in the ‘Milk’ row", "tap", "Delete", None, None, "Milk"),
    ("Type 'Eggs' into the 'Item name' field", "type_text", "Item name", "Eggs", "field", None),
    ("Toggle the 'Urgent' switch", "tap", "Urgent", None, "switch", None),
    ("Toggle 'Urgent'", "tap", "Urgent", None, "switch", None),
    ("Swipe up", "swipe", None, "up", None, None),
    ("Go back.", "navigate_back", None, None, None, None),
    ("Wait 2 seconds", "wait", None, "2", None, None),
])
def test_parse_step(text, action, target, value, hint, context):
    i = parse_step(text)
    assert (i.action, i.target, i.value, i.type_hint, i.context) == (action, target, value, hint, context)
    assert i.quoted


def test_unquoted_target_is_flagged():
    i = parse_step("Tap the Save button")
    assert i.target == "Save" and i.type_hint == "button" and i.quoted is False


def test_unsupported_step_raises():
    with pytest.raises(ValueError):
        parse_step("Dance wildly")


# ---------------------------------------------------------------- similarity

def test_tokens_split_identifiers():
    assert tokens("addItemButton") == ["add", "item", "button"]
    assert tokens("item_name-field") == ["item", "name", "field"]
    assert norm_key("addItemButton") == "add item"


def test_similarity_ordering():
    assert similarity("Add item", "addItemButton") == 1.0
    assert similarity("Add item", "Add") > similarity("Add item", "Settings")
    assert similarity("Save", "") == 0.0


# ---------------------------------------------------------------- resolver + router

def _decide(xml, step):
    s = parse_page_source(xml)
    res = resolve(s, parse_step(step))
    return s, res, route(res)


def test_clear_match_routes_structured():
    s, res, d = _decide(F.HOME, "Tap the 'Add item' button")
    assert d.route == "structured" and d.reason == R.OK
    assert d.chosen.element.label == "Add item"


def test_renamed_identifier_still_resolves_by_label():
    _, _, d = _decide(F.HOME_RENAMED, "Tap the 'Add item' button")
    assert d.route == "structured" and d.chosen.element.identifier == "addButton_v2"


def test_cell_and_child_text_are_collapsed_not_duplicates():
    _, res, d = _decide(F.HOME, "Tap the 'Milk' row")
    assert d.route == "structured" and d.chosen.element.type == "Cell"
    assert res.collapsed, "child StaticText should be merged into the Cell"


def test_weak_metadata_has_no_match():
    _, _, d = _decide(F.HOME_WEAK, "Tap the 'Add item' button")
    assert d.route == "fallback" and d.reason in (R.NO_MATCH, R.LOW_SCORE)


def test_duplicate_labels_go_to_fallback():
    _, _, d = _decide(F.HOME_DELETE, "Tap the 'Delete' button")
    assert d.route == "fallback" and d.reason == R.DUPLICATE_LABEL


def test_context_disambiguates_duplicates():
    s, _, d = _decide(F.HOME_DELETE, "Tap 'Delete' in the 'Milk' row")
    assert d.route == "structured"
    owner = s.elements[d.chosen.element.parent]
    assert owner.label == "Milk"


def test_disabled_target_is_incompatible_state():
    _, _, d = _decide(F.ADD, "Tap the 'Save' button")
    assert d.route == "fallback" and d.reason == R.INCOMPATIBLE_STATE


def test_type_text_resolves_by_placeholder():
    _, _, d = _decide(F.ADD, "Type 'Eggs' into the 'Item name' field")
    assert d.route == "structured" and d.chosen.element.type == "TextField"
    assert d.chosen.matched_field in ("placeholder", "identifier")


def test_targetless_actions_skip_resolution():
    _, _, d = _decide(F.HOME, "Swipe up")
    assert d.route == "structured" and d.reason == R.NOT_APPLICABLE


# ---------------------------------------------------------------- validator

def _v(raw, step="Tap the 'Add item' button", xml=F.HOME, cands=None):
    s = parse_page_source(xml)
    return validate(raw, parse_step(step), s, cands)


def test_valid_relative_tap_snaps_to_element():
    a = _v({"action": "tap", "x": 372 / 402, "y": 77 / 874, "relative": True})
    assert a.kind == "tap" and a.element_idx is not None


@pytest.mark.parametrize("raw,reason", [
    ("not a dict", "malformed_output"),
    ({"action": "delete_app"}, "unsupported_action"),
    ({"action": "swipe", "direction": "up"}, "intent_mismatch"),
    ({"action": "tap", "x": 1.5, "y": 0.2, "relative": True}, "out_of_bounds"),
    ({"action": "tap", "x": 900, "y": 10}, "out_of_bounds"),
    ({"action": "tap"}, "missing_point"),
    ({"action": "tap", "x": True, "y": 3}, "missing_point"),
])
def test_validator_rejections(raw, reason):
    a = _v(raw)
    assert a.kind == "reject" and a.reason == reason


def test_outside_candidate_set_rejected():
    s = parse_page_source(F.HOME)
    settings = next(el for el in s.elements if el.label == "Settings")
    add = next(el for el in s.elements if el.label == "Add item")
    x, y = settings.center
    a = validate({"action": "tap", "x": x, "y": y}, parse_step("Tap the 'Add item' button"), s, {add.idx})
    assert a.kind == "reject" and a.reason == "outside_candidate_set"


def test_type_text_must_land_on_input():
    a = _v({"action": "type_text", "x": 0.5, "y": 77 / 874, "relative": True, "text": "Eggs"},
           step="Type 'Eggs' into the 'Item name' field", xml=F.ADD)
    assert a.kind == "reject" and a.reason == "not_text_input"


def test_combined_label_segment_match():
    from engine.resolver import label_similarity
    sim, key = label_similarity("Milk", "Milk, Qty 1", 0.95)
    assert sim == 0.95 and key == "milk"
    assert label_similarity("Milk", "Bread, Qty 1", 0.95)[0] < 0.5


def test_combined_label_row_routes_structured():
    xml = F.page(F.e("Table",
                     F.e("Cell", F.e("Button", name="Milk, Qty 1", label="Milk, Qty 1", rect=(0, 140, 330, 44)),
                         rect=(0, 140, 402, 44)),
                     F.e("Cell", F.e("Button", name="Bread, Qty 1", label="Bread, Qty 1", rect=(0, 184, 330, 44)),
                         rect=(0, 184, 402, 44)),
                     rect=(0, 120, 402, 600)))
    _, _, d = _decide(xml, "Tap the 'Milk' row")
    assert d.route == "structured" and d.chosen.element.label == "Milk, Qty 1"


def test_above_postcondition():
    from engine.matchers import check
    s = parse_page_source(F.HOME)
    assert check(s, {"check": "above", "element": {"label": "Milk"}, "other": {"label": "Bread"}})[0]
    assert not check(s, {"check": "above", "element": {"label": "Bread"}, "other": {"label": "Milk"}})[0]


def test_switch_tap_point_is_trailing_edge():
    s = parse_page_source(F.ADD)
    sw = next(el for el in s.elements if el.type == "Switch")
    x, y = sw.tap_point
    assert x == sw.x + sw.width - 32 and y == sw.y + sw.height / 2


def test_context_matches_combined_row_label():
    xml = F.page(F.e("Table", *[
        F.e("Cell",
            F.e("Button", name=f"{n}, Qty 1", label=f"{n}, Qty 1", rect=(0, y, 300, 44)),
            F.e("Button", name="deleteButton", label="Delete", rect=(330, y + 7, 60, 30)),
            rect=(0, y, 402, 44))
        for n, y in (("Milk", 140), ("Eggs", 184), ("Bread", 228))], rect=(0, 120, 402, 600)))
    s, _, d = _decide(xml, "Tap 'Delete' in the 'Eggs' row")
    assert d.route == "structured"
    assert d.chosen.element.y == 191


def test_in_row_matcher():
    from engine.matchers import find
    xml = F.page(F.e("Table", *[
        F.e("Cell",
            F.e("Button", name=f"{n}, Qty 1", label=f"{n}, Qty 1", rect=(0, y, 300, 44)),
            F.e("Button", name="deleteButton", label="Delete", rect=(330, y + 7, 60, 30)),
            rect=(0, y, 402, 44))
        for n, y in (("Milk", 140), ("Eggs", 184))], rect=(0, 120, 402, 600)))
    s = parse_page_source(xml)
    hits = find(s, {"type": "Button", "label": "Delete", "in_row": "Eggs"})
    assert len(hits) == 1 and hits[0].y == 191


def test_validator_rejects_static_text_without_interactive_ancestor():
    alert = F.page(F.e("Alert",
                       F.e("StaticText", name="Reset all data?", label="Reset all data?", rect=(71, 409, 260, 21)),
                       F.e("Button", name="Cancel", label="Cancel", rect=(57, 450, 140, 48)),
                       F.e("Button", name="OK", label="OK", rect=(205, 450, 140, 48)),
                       name="Reset all data?", label="Reset all data?", rect=(41, 388, 320, 126)))
    s = parse_page_source(alert)
    a = validate({"action": "tap", "x": 0.5, "y": 0.47, "relative": True}, parse_step("Tap the 'Reset' button"), s)
    assert a.kind == "reject" and a.reason == "not_interactive"
    ok = validate({"action": "tap", "x": 275, "y": 474}, parse_step("Tap the 'Reset' button"), s)
    assert ok.kind == "tap" and s.elements[ok.element_idx].label == "OK"


def test_validator_snaps_label_inside_button_to_button():
    s = parse_page_source(F.HOME)
    milk_text = next(e for e in s.elements if e.type == "StaticText" and e.label == "Milk")
    x, y = milk_text.center
    a = validate({"action": "tap", "x": x, "y": y}, parse_step("Tap the 'Milk' row"), s)
    assert a.kind == "tap" and s.elements[a.element_idx].type == "Cell"
