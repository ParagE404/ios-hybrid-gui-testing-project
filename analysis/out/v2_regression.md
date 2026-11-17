# Engine v2 evaluation (generated, exploratory)

Held-out log: experiments/raw/heldout.jsonl. Rule: D-029.

## Held-out scenarios (primary)

- runs: 192; engine errors: 0; cells: 64; cells whose repetitions disagree: 0
- cells matching the committed prediction: 50 of 64
- runs where scroll_to_find fired: 0; where relax_candidate_set fired: 18
- added scrolling latency when it fired: median 0.0 s, max 0.0 s over 0 runs

Completion by scenario class and configuration:

| class | config | runs | completed | rate |
|---|---|---|---|---|
| below_fold | a11y-v1 | 18 | 0 | 0.000 |
| below_fold | a11y-v2 | 18 | 0 | 0.000 |
| below_fold | hybrid-v1 | 18 | 0 | 0.000 |
| below_fold | hybrid-v2 | 18 | 0 | 0.000 |
| control | a11y-v1 | 12 | 12 | 1.000 |
| control | a11y-v2 | 12 | 12 | 1.000 |
| control | hybrid-v1 | 12 | 12 | 1.000 |
| control | hybrid-v2 | 12 | 12 | 1.000 |
| hidden_candidate | a11y-v1 | 18 | 0 | 0.000 |
| hidden_candidate | a11y-v2 | 18 | 0 | 0.000 |
| hidden_candidate | hybrid-v1 | 18 | 0 | 0.000 |
| hidden_candidate | hybrid-v2 | 18 | 12 | 0.667 |

Completion by configuration and condition:

| config | condition | runs | completed | rate |
|---|---|---|---|---|
| a11y-v1 | baseline | 24 | 6 | 0.250 |
| a11y-v1 | perturbed | 24 | 6 | 0.250 |
| a11y-v2 | baseline | 24 | 6 | 0.250 |
| a11y-v2 | perturbed | 24 | 6 | 0.250 |
| hybrid-v1 | baseline | 24 | 6 | 0.250 |
| hybrid-v1 | perturbed | 24 | 6 | 0.250 |
| hybrid-v2 | baseline | 24 | 12 | 0.500 |
| hybrid-v2 | perturbed | 24 | 12 | 0.500 |

Scenario cells gained or lost by v2 (all repetitions):

| pair | scenario | condition | change |
|---|---|---|---|
| hybrid-v1 -> hybrid-v2 | h-05 | baseline | gained |
| hybrid-v1 -> hybrid-v2 | h-05 | perturbed | gained |
| hybrid-v1 -> hybrid-v2 | h-06 | baseline | gained |
| hybrid-v1 -> hybrid-v2 | h-06 | perturbed | gained |

Cells (prediction from the scenario file, committed before v2 code):

| scenario | config | condition | runs | completed | reps_agree | first_failure | scroll_fired | relax_fired | class | predicted_complete | prediction_met |
|---|---|---|---|---|---|---|---|---|---|---|---|
| h-01 | a11y-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-01 | a11y-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-01 | a11y-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-01 | a11y-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-01 | hybrid-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-01 | hybrid-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-01 | hybrid-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-01 | hybrid-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-02 | a11y-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-02 | a11y-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-02 | a11y-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-02 | a11y-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-02 | hybrid-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-02 | hybrid-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-02 | hybrid-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-02 | hybrid-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-03 | a11y-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-03 | a11y-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-03 | a11y-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-03 | a11y-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-03 | hybrid-v1 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-03 | hybrid-v1 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | False | True |
| h-03 | hybrid-v2 | baseline | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-03 | hybrid-v2 | perturbed | 3 | 0 | True | post | 0 | 0 | below_fold | True | False |
| h-04 | a11y-v1 | baseline | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | a11y-v1 | perturbed | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | a11y-v2 | baseline | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | a11y-v2 | perturbed | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | hybrid-v1 | baseline | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | hybrid-v1 | perturbed | 3 | 0 | True | step/2/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-04 | hybrid-v2 | baseline | 3 | 0 | True | post | 0 | 3 | hidden_candidate | True | False |
| h-04 | hybrid-v2 | perturbed | 3 | 0 | True | post | 0 | 3 | hidden_candidate | True | False |
| h-05 | a11y-v1 | baseline | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | a11y-v1 | perturbed | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | a11y-v2 | baseline | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | a11y-v2 | perturbed | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | hybrid-v1 | baseline | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | hybrid-v1 | perturbed | 3 | 0 | True | step/1/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-05 | hybrid-v2 | baseline | 3 | 3 | True | pass | 0 | 3 | hidden_candidate | True | True |
| h-05 | hybrid-v2 | perturbed | 3 | 3 | True | pass | 0 | 3 | hidden_candidate | True | True |
| h-06 | a11y-v1 | baseline | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | a11y-v1 | perturbed | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | a11y-v2 | baseline | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | a11y-v2 | perturbed | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | hybrid-v1 | baseline | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | hybrid-v1 | perturbed | 3 | 0 | True | step/3/not_executed | 0 | 0 | hidden_candidate | False | True |
| h-06 | hybrid-v2 | baseline | 3 | 3 | True | pass | 0 | 3 | hidden_candidate | True | True |
| h-06 | hybrid-v2 | perturbed | 3 | 3 | True | pass | 0 | 3 | hidden_candidate | True | True |
| h-07 | a11y-v1 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | a11y-v1 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | a11y-v2 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | a11y-v2 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | hybrid-v1 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | hybrid-v1 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | hybrid-v2 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-07 | hybrid-v2 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | a11y-v1 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | a11y-v1 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | a11y-v2 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | a11y-v2 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | hybrid-v1 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | hybrid-v1 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | hybrid-v2 | baseline | 3 | 3 | True | pass | 0 | 0 | control | True | True |
| h-08 | hybrid-v2 | perturbed | 3 | 3 | True | pass | 0 | 0 | control | True | True |

## Formal scenarios with v2 (secondary: regression check)

Regression log: experiments/raw/v2_regression.jsonl; v1 reference: experiments/raw/formal.jsonl. SU-03, SU-05 and SU-07 motivated the fixes, so gains there are not held-out evidence.

- v2 runs: 288; engine errors: 0; scroll_to_find fired in 30 runs, relax_candidate_set in 9
- cells lost by v2: 0; gained: 0 (of which on motivating scenarios: 0)

| config | condition | runs | completed | rate |
|---|---|---|---|---|
| a11y-v1 | baseline | 72 | 72 | 1.000 |
| a11y-v1 | perturbed | 72 | 42 | 0.583 |
| a11y-v2 | baseline | 72 | 72 | 1.000 |
| a11y-v2 | perturbed | 72 | 42 | 0.583 |
| hybrid-v1 | baseline | 72 | 72 | 1.000 |
| hybrid-v1 | perturbed | 72 | 54 | 0.750 |
| hybrid-v2 | baseline | 72 | 72 | 1.000 |
| hybrid-v2 | perturbed | 72 | 54 | 0.750 |

Changed cells:

_(none)_

Added scrolling latency when scroll_to_find fired: median 6.7 s, max 12.9 s over 30 runs

Cells where a v2 option fired:

| scenario | config | condition | runs | completed | scroll_fired | relax_fired | first_failure | median_scroll_s |
|---|---|---|---|---|---|---|---|---|
| nn-07 | a11y-v2 | perturbed | 3 | 0 | 3 | 0 | step/0/not_executed | 6.6 |
| nn-07 | hybrid-v2 | perturbed | 3 | 3 | 3 | 0 | pass | 6.7 |
| nn-08 | a11y-v2 | perturbed | 3 | 0 | 3 | 0 | step/0/not_executed | 6.6 |
| nn-08 | hybrid-v2 | perturbed | 3 | 0 | 3 | 0 | step/1/not_executed | 12.8 |
| su-03 | hybrid-v2 | perturbed | 3 | 0 | 0 | 3 | step/2/not_executed | 0.0 |
| su-05 | hybrid-v2 | perturbed | 3 | 0 | 0 | 3 | step/2/not_executed | 0.0 |
| su-07 | hybrid-v2 | perturbed | 3 | 0 | 0 | 3 | post | 0.0 |
| su-08 | a11y-v2 | perturbed | 3 | 0 | 3 | 0 | step/2/not_executed | 6.7 |
| su-08 | hybrid-v2 | perturbed | 3 | 3 | 3 | 0 | pass | 6.7 |
| tb-07 | a11y-v2 | perturbed | 3 | 0 | 3 | 0 | step/1/not_executed | 6.2 |
| tb-07 | hybrid-v2 | perturbed | 3 | 3 | 3 | 0 | pass | 6.2 |
| tb-08 | a11y-v2 | perturbed | 3 | 0 | 3 | 0 | step/0/not_executed | 7.0 |
| tb-08 | hybrid-v2 | perturbed | 3 | 3 | 3 | 0 | pass | 7.0 |
