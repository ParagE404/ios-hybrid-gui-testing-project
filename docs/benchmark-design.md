# Benchmark design


## 1. Apps (D-003)

| Slot | App | UI framework | Licence | Why | Risks to check on Day 2 |
|---|---|---|---|---|---|
| A | **Testbed** (purpose-built, "Errands") | SwiftUI | own | Full control of identifiers, hierarchy and labels; every perturbation is a launch argument | none beyond build time |
| B | **SyncUps** (Point-Free's modern rebuild of Apple's Scrumdinger) | SwiftUI | MIT | Real-world architecture: sheets, drill-downs, alerts, forms, local persistence; no login | Avoid the timer/speech screens (non-deterministic, permissions); SPM dependencies must resolve on the pinned Xcode |
| C | **NetNewsWire** (Ranchero Software) | mostly UIKit | MIT (confirm LICENSE file) | Mature production app; adds UIKit diversity; builds without a paid developer account via `setup.sh` | Feed refresh needs network, so scenarios stay on local-only features (settings, folders, account screens); confirm the "On My iPhone" account works offline |
| Backup | Apple Landmarks tutorial app | SwiftUI | Apple sample code licence | Simple, deterministic | Less realistic |

Selection gates (proposal risk register): licence permits use; builds on the pinned Xcode; runs offline with no login; resettable; deterministic. Pin the commit hash for B and C.

Why this mix: one controlled app (internal validity), two independent real apps (external validity), and both SwiftUI and UIKit, because they expose accessibility metadata differently.

## 2. Perturbation categories (D-004)

Balanced design: **3 apps x 4 categories x 2 scenarios = 24 formal scenarios.** Each category can then be analysed on its own (6 scenarios each), and H2 ("locator-changing") maps cleanly to categories 1 and 2.

| # | Category (proposal wording) | Example change, behaviour unchanged | Expected effect (to test, not assume) |
|---|---|---|---|
| 1 | Identifier rename / removal | `addItemButton` renamed to `addButton_v2`, or identifier deleted | Scripted fails; a11y should recover via label |
| 2 | Hierarchy insertion / restructuring | Rows wrapped in an extra container; control moved into a new section; breaks XPath | Scripted (XPath) fails; a11y mostly unaffected |
| 3 | Duplicate or generic labels | Several "Delete" buttons; "Sort" relabelled "Options" | a11y uncertain (duplicate_label / low_score); hybrid may recover |
| 4 | Visually clear, weak metadata | Icon-only button with no accessibility label and a generic id; colour chips with no labels | a11y fails (no_match); hybrid is the only route |

Benchmark-construction bias (a named threat): the perturbations are drawn from documented causes of locator breakage, fixed before any formal run, and include cases where vision is also expected to struggle (e.g. similar-looking icons). Write the expected outcome for each scenario BEFORE running, so the results can contradict it.

Implementation:
- Testbed: launch arguments (`-perturb <flag>`), one build.
- SyncUps and NetNewsWire: one small git patch per perturbed scenario on the pinned commit, built as a separate variant app. Patches are listed in appendices.

Scripted baseline locator policy (D-011): developer accessibility id if set; otherwise XPath on the element's unique name; otherwise positional XPath. Applied mechanically to the baseline build, recorded per step in the YAML.

## 3. Testbed app spec ("Errands")

Tabs: **List**, **Settings**.
- **List:** navigation title "Errands"; toolbar "Add item" (+) button; sort menu; search field; rows of items (name, quantity, category colour dot, done checkmark); swipe or inline "Delete" button per row; filter chips by category (colour + text).
- **Add / Edit item sheet:** TextField "Item name", Stepper "Quantity", Picker "Category" (Food, Home, Work), Toggle "Urgent", "Save" (disabled until a name is entered) and "Cancel".
- **Item detail:** name, quantity, category, "Mark as done" button, "Favourite" star (icon-only), "Share" (icon-only).
- **Settings:** Toggle "Show completed", Toggle "Compact rows", segmented control "Sort by" (Name / Date), "Reset data" with a confirmation alert.
- Launch arguments: `-resetData` (seed: Milk, Bread, Eggs, Batteries), `-perturb <flag>` (repeatable).
- Every control has a stable `accessibilityIdentifier` in the baseline, so category 1 perturbations have something to break.

## 4. Testbed scenarios (8)

| ID | Task | Steps (approx.) | Category | Perturbation |
|---|---|---|---|---|
| TB-01 | Add an item "Coffee" with quantity 2 | 5 | 1 | Add button id renamed |
| TB-02 | Edit "Bread" and mark it urgent | 4 | 1 | Urgent toggle and Save ids removed |
| TB-03 | Mark "Milk" as done from its detail page | 3 | 2 | Pinned section inserted above; rows gain a category caption, changing the combined label |
| TB-04 | Turn off "Show completed" in Settings | 3 | 2 | Toggle moved into a new Display section with a subtitle |
| TB-05 | Delete "Eggs" then "Bread" | 2 | 3 | Every row's delete button is just "Delete" with one shared id |
| TB-06 | Sort the list by date | 3 | 3 | Sort menu relabelled "Options" |
| TB-07 | Favourite "Batteries" | 3 | 4 | Star button loses its accessibility label; id becomes `button_7` |
| TB-08 | Filter to "Home" and mark "Light bulbs" done | 3 | 4 | Category chips become icon-only, unlabelled |

SyncUps (SU-01 to 08) and NetNewsWire (NN-01 to 08) scenarios are written on Day 2 after exploring each app's real page source, using the same 2-per-category quota.

Pilot set (never analysed): 2 extra scenarios per app with different screens and perturbations, used only to calibrate the router threshold and margin (D-005).

## 5. Run budget
432 core runs (24 x 2 conditions x 3 configs x 3 reps). At about 3 to 6 steps per run, 0.5 s settle per step, about 1 s page source and about 3.2 s per VLM fallback, the full set should take roughly 4 to 7 hours: one overnight batch.
