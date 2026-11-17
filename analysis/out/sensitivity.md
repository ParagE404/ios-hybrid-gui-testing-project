# Sensitivity of frozen thresholds and resolver weights (generated)

Log: experiments/raw/formal.jsonl. Post-hoc analysis after the formal experiment (D-027); engine unchanged.

## Data

- a11y targeted step records: 450; unique steps (scenario, condition, step): 150
- steps whose repetitions disagree: 2 [('tb-04', 'baseline', 0), ('tb-04', 'perturbed', 0)]
- top candidate correct (logged oracle_ok): 141 of 150

## B1 Router thresholds (exact, from logs)

- Recomputed route at frozen (tau 0.66, delta 0.09) agrees with the logged route for 150 of 150 unique steps.
- Frozen cell: coverage 0.947 (142 accepted), precision 0.993, wrong accepted 1.
- Grid 46 x 31 = 1426 cells; cells where no step changes route: 252.
- Holding delta at 0.09, tau can move over (0.5, 0.7) with no route change; holding tau at 0.66, delta over (0.0, 0.11).
- Wrong top candidate accepted at the frozen cell: [{'scenario': 'nn-06', 'condition': 'perturbed', 'step_index': 1, 'top_score': 0.8529, 'top': ('StaticText', 'Confirm Mark All as Read', None)}].
- In the a11y configuration the route does not change the action (best_effort acts on the top candidate either way, D-007), so a route change here matters only for hybrid, where it decides whether the VLM is called.
- Over the whole grid: route changes up to 49 steps; coverage 0.620 to 0.947.
- Over the whole grid: min precision on accepted steps 0.992, max wrong accepted 1.

Steps nearest the frozen boundary (gap = score minus threshold, or margin minus delta):

| scenario | condition | step_index | top_score | second_score | gap_tau | gap_delta | logged_route | oracle_ok | nearest |
|---|---|---|---|---|---|---|---|---|---|
| tb-08 | baseline | 1 | 0.906 | 0.788 | 0.246 | 0.028 | structured | True | 0.028 |
| tb-06 | perturbed | 0 | 0.705 |  | 0.045 |  | structured | True | 0.045 |
| tb-05 | baseline | 1 | 0.800 | 0.659 | 0.140 | 0.051 | structured | True | 0.051 |
| nn-08 | baseline | 1 | 1.000 | 0.853 | 0.340 | 0.057 | structured | True | 0.057 |
| tb-04 | baseline | 2 | 1.000 | 0.853 | 0.340 | 0.057 | structured | True | 0.057 |
| nn-03 | perturbed | 1 | 0.965 | 0.818 | 0.305 | 0.057 | structured | True | 0.057 |
| tb-04 | perturbed | 2 | 1.000 | 0.853 | 0.340 | 0.057 | structured | True | 0.057 |
| nn-03 | baseline | 1 | 1.000 | 0.853 | 0.340 | 0.057 | structured | True | 0.057 |

## B2 Resolver weights (replay on saved page sources)

- Replayable steps (screen saved): 150 of 150; no screen / missing file: 0 
- Replay agrees with log (same top candidate and score, same route and reason, same oracle result): 141 of 150 (94.0%); identical full candidate list: 139.
- Steps used for the weight sweep: 141.

Excluded steps (saved screen differs from the live one):

| scenario | condition | step_index | screen | same_top | same_route | same_oracle | logged_top | replayed_top |
|---|---|---|---|---|---|---|---|---|
| nn-01 | baseline | 3 | netnewswire/baseline/add_folder.xml | False | False | False | ('Button', 'Add', None) | ('StaticText', 'Add Folder', None) |
| nn-01 | perturbed | 3 | netnewswire/nn01_add_id_renamed/add_folder.xml | False | False | False | ('Button', 'Add', None) | ('StaticText', 'Add Folder', None) |
| nn-04 | baseline | 3 | netnewswire/baseline/add_folder.xml | False | False | False | ('Button', 'Add', None) | ('StaticText', 'Add Folder', None) |
| nn-04 | perturbed | 3 | netnewswire/nn04_add_menu_restructured/add_folder.xml | False | False | False | ('Button', 'Add', None) | ('StaticText', 'Add Folder', None) |
| nn-07 | baseline | 3 | netnewswire/baseline/add_folder.xml | False | False | False | ('Button', 'Add', None) | ('StaticText', 'Add Folder', None) |
| su-07 | baseline | 4 | syncups/baseline/theme_menu.xml | False | False | False | ('Button', 'Seafoam', 'paintpalette') | ('Button', 'Seafoam', 'paintpalette') |
| tb-01 | baseline | 3 | baseline/add_form.xml | False | False | False | ('Button', 'Save', 'saveButton') | ('Button', 'Save', 'saveButton') |
| tb-01 | perturbed | 3 | tb01_add_id_renamed/add_form.xml | False | False | False | ('Button', 'Save', 'saveButton') | ('Button', 'Save', 'saveButton') |
| tb-04 | perturbed | 0 | tb04_section_inserted/list.xml | False | True | True | ('Button', 'Settings', 'gearshape') | ('Button', 'Settings', None) |

Component-weight simplex (step 0.05, 230 points, (0,0,1) skipped): 190 points give exactly the frozen set of correct top candidates; nearest point that changes any step: text=0.70 type=0.30 context=0.00 (Euclidean distance 0.187). Interior points (every weight >= 0.05): 171, of which 171 are unchanged; all changes lie on the edges where a weight is 0. Most steps gained by any point: 0; most lost: 11.

Attribute weights and ablations:

| kind | variant | top_correct | steps_gained | steps_lost | route_changes | scenario_pairs_changed |
|---|---|---|---|---|---|---|
| frozen | frozen | 132 | 0 | 0 | 0 | 0 |
| attribute | label 0.80 (-0.2) | 132 | 0 | 0 | 1 | 0 |
| attribute | label 1.20 (+0.2) | 132 | 0 | 0 | 0 | 0 |
| attribute | identifier 0.70 (-0.2) | 132 | 0 | 0 | 1 | 0 |
| attribute | identifier 1.10 (+0.2) | 132 | 0 | 0 | 1 | 0 |
| attribute | placeholder 0.65 (-0.2) | 132 | 0 | 0 | 0 | 0 |
| attribute | placeholder 1.05 (+0.2) | 132 | 0 | 0 | 0 | 0 |
| attribute | value 0.40 (-0.2) | 132 | 0 | 0 | 0 | 0 |
| attribute | value 0.80 (+0.2) | 132 | 0 | 0 | 0 | 0 |
| ablation | text only (type 0, context 0) | 121 | 0 | 11 | 13 | 10 |
| ablation | no context (context 0) | 129 | 0 | 3 | 4 | 2 |
| ablation | no type (type 0) | 124 | 0 | 8 | 9 | 8 |

Steps that change under attribute or ablation variants:

| variant | scenario | condition | step_index | frozen_correct | variant_correct | variant_top |
|---|---|---|---|---|---|---|
| text only (type 0, context 0) | nn-02 | baseline | 1 | True | False | ('StaticText', 'Group by Feed', None) |
| text only (type 0, context 0) | nn-02 | perturbed | 1 | True | False | ('StaticText', 'Group by Feed', None) |
| text only (type 0, context 0) | nn-03 | baseline | 1 | True | False | ('StaticText', 'Sort Oldest to Newest', None) |
| text only (type 0, context 0) | nn-03 | perturbed | 1 | True | False | ('StaticText', 'Sort Oldest to Newest, Timeline order', None) |
| text only (type 0, context 0) | nn-06 | baseline | 1 | True | False | ('StaticText', 'Confirm Mark All as Read', None) |
| text only (type 0, context 0) | nn-08 | baseline | 1 | True | False | ('StaticText', 'Refresh to Clear Read Articles', None) |
| text only (type 0, context 0) | tb-04 | baseline | 2 | True | False | ('StaticText', 'List', None) |
| text only (type 0, context 0) | tb-04 | perturbed | 2 | True | False | ('StaticText', 'List', None) |
| text only (type 0, context 0) | tb-05 | baseline | 1 | True | False | ('Button', 'Delete Eggs', 'delete_Eggs') |
| text only (type 0, context 0) | tb-05 | perturbed | 0 | True | False | ('Button', 'Delete', 'deleteButton') |
| text only (type 0, context 0) | tb-05 | perturbed | 1 | True | False | ('Button', 'Delete', 'deleteButton') |
| no context (context 0) | tb-05 | baseline | 1 | True | False | ('Button', 'Delete Eggs', 'delete_Eggs') |
| no context (context 0) | tb-05 | perturbed | 0 | True | False | ('Button', 'Delete', 'deleteButton') |
| no context (context 0) | tb-05 | perturbed | 1 | True | False | ('Button', 'Delete', 'deleteButton') |
| no type (type 0) | nn-02 | baseline | 1 | True | False | ('StaticText', 'Group by Feed', None) |
| no type (type 0) | nn-02 | perturbed | 1 | True | False | ('StaticText', 'Group by Feed', None) |
| no type (type 0) | nn-03 | baseline | 1 | True | False | ('StaticText', 'Sort Oldest to Newest', None) |
| no type (type 0) | nn-03 | perturbed | 1 | True | False | ('StaticText', 'Sort Oldest to Newest, Timeline order', None) |
| no type (type 0) | nn-06 | baseline | 1 | True | False | ('StaticText', 'Confirm Mark All as Read', None) |
| no type (type 0) | nn-08 | baseline | 1 | True | False | ('StaticText', 'Refresh to Clear Read Articles', None) |
| no type (type 0) | tb-04 | baseline | 2 | True | False | ('StaticText', 'List', None) |
| no type (type 0) | tb-04 | perturbed | 2 | True | False | ('StaticText', 'List', None) |

Caveats: the replay covers only steps the a11y run logged (a run stops at its first failed step), on one saved screen per step; scenario_pairs_changed counts (scenario, condition) pairs whose all-steps-correct status flips, which approximates but is not the same as scenario completion. The type and state gates are hard rules, not weights, and stay on in every variant.
