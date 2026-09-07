"""Synthetic XCUITest page sources for tests.

Shapes follow real XCUITest page source (XCUIElementType* nodes with type, name,
label, value, enabled, visible, accessible, x, y, width, height). Replace or extend
with real dumps from spikes/out/ once the simulator works.
"""

from xml.sax.saxutils import quoteattr


def e(type_, *children, name=None, label=None, value=None, placeholder=None,
      enabled=True, visible=True, accessible=None, rect=(0, 0, 0, 0)):
    t = f"XCUIElementType{type_}"
    attrs = {"type": t, "enabled": str(enabled).lower(), "visible": str(visible).lower(),
             "accessible": str(accessible if accessible is not None else type_ not in ("Other", "Window", "Application")).lower(),
             "x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]}
    if name is not None:
        attrs["name"] = name
    if label is not None:
        attrs["label"] = label
    if value is not None:
        attrs["value"] = value
    if placeholder is not None:
        attrs["placeholderValue"] = placeholder
    a = " ".join(f"{k}={quoteattr(str(v))}" for k, v in attrs.items())
    return f"<{t} {a}>{''.join(children)}</{t}>"


def page(*children):
    app = e("Application", e("Window", *children, rect=(0, 0, 402, 874)),
            name="Testbed", label="Testbed", rect=(0, 0, 402, 874))
    return f'<?xml version="1.0" encoding="UTF-8"?><AppiumAUT>{app}</AppiumAUT>'


def cell(label, y, *extra, name=None):
    return e("Cell", e("StaticText", name=label, label=label, rect=(20, y + 12, 200, 20)), *extra,
             name=name or label, label=label, rect=(0, y, 402, 44))


def home(items=("Milk", "Bread"), add_name="addItemButton", add_label="Add item", with_delete=False):
    rows = []
    for i, it in enumerate(items):
        extra = [e("Button", name="deleteButton", label="Delete", rect=(330, 140 + i * 44 + 7, 60, 30))] if with_delete else []
        rows.append(cell(it, 140 + i * 44, *extra))
    return page(
        e("NavigationBar",
          e("StaticText", name="Shopping List", label="Shopping List", rect=(130, 60, 140, 22)),
          e("Button", name=add_name, label=add_label, rect=(350, 55, 44, 44)),
          name="Shopping List", rect=(0, 50, 402, 54)),
        e("Table", *rows, rect=(0, 120, 402, 600)),
        e("TabBar",
          e("Button", name="List", label="List", value="1", rect=(0, 800, 201, 50)),
          e("Button", name="Settings", label="Settings", rect=(201, 800, 201, 50)),
          rect=(0, 790, 402, 84)),
    )


def add_screen(typed=None):
    return page(
        e("NavigationBar",
          e("Button", name="cancelButton", label="Cancel", rect=(10, 55, 70, 44)),
          e("StaticText", name="New Item", label="New Item", rect=(150, 60, 100, 22)),
          e("Button", name="saveButton", label="Save", enabled=typed is not None, rect=(330, 55, 60, 44)),
          name="New Item", rect=(0, 50, 402, 54)),
        e("TextField", name="itemNameField", value=typed, placeholder="Item name", rect=(20, 130, 362, 44)),
        e("Switch", name="urgentSwitch", label="Urgent", value="0", rect=(20, 190, 362, 44)),
    )


HOME = home()
HOME_RENAMED = home(add_name="addButton_v2")
HOME_WEAK = home(add_name="button_3", add_label="")     # icon-only button, generic id, no label
HOME_DELETE = home(with_delete=True)                      # duplicate 'Delete' labels
ADD = add_screen()
ADD_TYPED = add_screen("Eggs")
HOME_EGGS = home(items=("Milk", "Bread", "Eggs"))
