# Seeded-fault study (generated)

Log: experiments/raw/faults.jsonl; reference: experiments/raw/formal.jsonl. Rule: D-028.

- runs analysed: 216 (planned 216); scenario x config x condition cells: 72 (planned 72)
- false passes: 0; detections: 171; fragility (masked): 45; other: 0; engine errors: 0
- runs with a substitute action (executed step, oracle false): 54
- repetitions disagreeing within a cell: 0
- cells matching the pre-registered prediction: 72 of 72

## By configuration and condition (rates are scenario means; 95% scenario-cluster bootstrap)

| config | condition | runs | false_pass | detection | fragility | other | engine_error | substitute_runs | runner_completed | false_pass_rate | false_pass_ci_low | false_pass_ci_high | detection_rate | detection_ci_low | detection_ci_high |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a11y | baseline | 36 | 0 | 36 | 0 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| a11y | perturbed | 36 | 0 | 30 | 6 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 0.833 | 0.583 | 1.000 |
| hybrid | baseline | 36 | 0 | 36 | 0 | 0 | 0 | 15 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| hybrid | perturbed | 36 | 0 | 36 | 0 | 0 | 0 | 15 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| scripted | baseline | 36 | 0 | 30 | 6 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.833 | 0.583 | 1.000 |
| scripted | perturbed | 36 | 0 | 3 | 33 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.083 | 0.000 | 0.250 |

## By fault class

| fault_class | config | condition | runs | false_pass | detection | fragility | other | engine_error | substitute_runs | runner_completed | false_pass_rate | false_pass_ci_low | false_pass_ci_high | detection_rate | detection_ci_low | detection_ci_high |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| behavioural | a11y | baseline | 24 | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| behavioural | a11y | perturbed | 24 | 0 | 18 | 6 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.750 | 0.375 | 1.000 |
| behavioural | hybrid | baseline | 24 | 0 | 24 | 0 | 0 | 0 | 3 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| behavioural | hybrid | perturbed | 24 | 0 | 24 | 0 | 0 | 0 | 3 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| behavioural | scripted | baseline | 24 | 0 | 21 | 3 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.875 | 0.625 | 1.000 |
| behavioural | scripted | perturbed | 24 | 0 | 3 | 21 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.125 | 0.000 | 0.375 |
| lure | a11y | baseline | 12 | 0 | 12 | 0 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| lure | a11y | perturbed | 12 | 0 | 12 | 0 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| lure | hybrid | baseline | 12 | 0 | 12 | 0 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| lure | hybrid | perturbed | 12 | 0 | 12 | 0 | 0 | 0 | 12 | 0 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| lure | scripted | baseline | 12 | 0 | 9 | 3 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.750 | 0.250 | 1.000 |
| lure | scripted | perturbed | 12 | 0 | 0 | 12 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Scenario level

| scenario | fault_class | config | condition | class | where | predicted | prediction_met | substitutes |
|---|---|---|---|---|---|---|---|---|
| f-01 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-01 | behavioural | a11y | perturbed | detection | postcondition | detection | True |  |
| f-01 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-01 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-01 | behavioural | scripted | baseline | detection | postcondition | detection | True |  |
| f-01 | behavioural | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-02 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-02 | behavioural | a11y | perturbed | detection | postcondition | detection | True |  |
| f-02 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-02 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-02 | behavioural | scripted | baseline | detection | postcondition | detection | True |  |
| f-02 | behavioural | scripted | perturbed | fragility | step 2 (not_executed) | fragility | True |  |
| f-03 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-03 | behavioural | a11y | perturbed | detection | postcondition | detection | True |  |
| f-03 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-03 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-03 | behavioural | scripted | baseline | detection | postcondition | detection | True |  |
| f-03 | behavioural | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-04 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-04 | behavioural | a11y | perturbed | detection | postcondition | detection | True |  |
| f-04 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-04 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-04 | behavioural | scripted | baseline | fragility | step 0 (not_executed) | fragility | True |  |
| f-04 | behavioural | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-05 | behavioural | a11y | baseline | detection | fault step | detection | True |  |
| f-05 | behavioural | a11y | perturbed | detection | fault step | detection | True |  |
| f-05 | behavioural | hybrid | baseline | detection | fault step | detection | True |  |
| f-05 | behavioural | hybrid | perturbed | detection | fault step | detection | True |  |
| f-05 | behavioural | scripted | baseline | detection | fault step | detection | True |  |
| f-05 | behavioural | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-06 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-06 | behavioural | a11y | perturbed | detection | postcondition | detection | True |  |
| f-06 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-06 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-06 | behavioural | scripted | baseline | detection | postcondition | detection | True |  |
| f-06 | behavioural | scripted | perturbed | detection | postcondition | detection | True |  |
| f-07 | behavioural | a11y | baseline | detection | postcondition | detection | True |  |
| f-07 | behavioural | a11y | perturbed | fragility | step 1 (not_executed) | fragility | True |  |
| f-07 | behavioural | hybrid | baseline | detection | postcondition | detection | True |  |
| f-07 | behavioural | hybrid | perturbed | detection | postcondition | detection | True |  |
| f-07 | behavioural | scripted | baseline | detection | postcondition | detection | True |  |
| f-07 | behavioural | scripted | perturbed | fragility | step 1 (not_executed) | fragility | True |  |
| f-08 | behavioural | a11y | baseline | detection | fault step | detection | True |  |
| f-08 | behavioural | a11y | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-08 | behavioural | hybrid | baseline | detection | fault step | detection | True | s1 vlm 'None'; s2 vlm 'None' |
| f-08 | behavioural | hybrid | perturbed | detection | fault step | detection | True | s1 vlm 'None'; s2 vlm 'None' |
| f-08 | behavioural | scripted | baseline | detection | fault step | detection | True |  |
| f-08 | behavioural | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-09 | lure | a11y | baseline | detection | postcondition | detection | True | s3 structured 'Save draft' |
| f-09 | lure | a11y | perturbed | detection | postcondition | detection | True | s3 structured 'Save draft' |
| f-09 | lure | hybrid | baseline | detection | postcondition | detection | True | s3 structured 'Save draft' |
| f-09 | lure | hybrid | perturbed | detection | postcondition | detection | True | s3 structured 'Save draft' |
| f-09 | lure | scripted | baseline | detection | fault step | detection | True |  |
| f-09 | lure | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-10 | lure | a11y | baseline | detection | postcondition | detection | True | s1 structured 'Mark all as done' |
| f-10 | lure | a11y | perturbed | detection | postcondition | detection | True | s1 structured 'Mark all as done' |
| f-10 | lure | hybrid | baseline | detection | postcondition | detection | True | s1 structured 'Mark all as done' |
| f-10 | lure | hybrid | perturbed | detection | postcondition | detection | True | s1 structured 'Mark all as done' |
| f-10 | lure | scripted | baseline | detection | fault step | detection | True |  |
| f-10 | lure | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-11 | lure | a11y | baseline | detection | postcondition | detection | True | s1 structured 'Show completed first' |
| f-11 | lure | a11y | perturbed | detection | postcondition | detection | True | s1 structured 'Show completed first, Includes finished errands' |
| f-11 | lure | hybrid | baseline | detection | postcondition | detection | True | s1 structured 'Show completed first' |
| f-11 | lure | hybrid | perturbed | detection | postcondition | detection | True | s1 structured 'Show completed first, Includes finished errands' |
| f-11 | lure | scripted | baseline | fragility | step 0 (not_executed) | fragility | True |  |
| f-11 | lure | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |
| f-12 | lure | a11y | baseline | detection | fault step | detection | True | s0 best_effort 'Delete Milk' |
| f-12 | lure | a11y | perturbed | detection | fault step | detection | True | s0 best_effort 'Delete' |
| f-12 | lure | hybrid | baseline | detection | fault step | detection | True | s0 vlm 'Delete Bread'; s1 vlm 'Delete Batteries' |
| f-12 | lure | hybrid | perturbed | detection | fault step | detection | True | s0 vlm 'Delete'; s1 vlm 'Delete' |
| f-12 | lure | scripted | baseline | detection | fault step | detection | True |  |
| f-12 | lure | scripted | perturbed | fragility | step 0 (not_executed) | fragility | True |  |

## False passes (each needs a one-line cause in the write-up)

_(none)_

## Other failures and engine errors

_(none)_

## Cells that missed the prediction

_(none)_
