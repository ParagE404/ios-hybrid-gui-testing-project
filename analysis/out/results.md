# Results summary (generated)

Logs: experiments/raw/formal.jsonl  
Notes: {'infrastructure_excluded_attempts': 0, 'engine_error_runs': 0, 'runs': 432, 'steps': 1335}

## completion

| config | condition | runs | completed | rate | ci_low | ci_high |
|---|---|---|---|---|---|---|
| a11y | baseline | 72 | 72 | 1.000 | 1.000 | 1.000 |
| a11y | perturbed | 72 | 42 | 0.583 | 0.375 | 0.792 |
| hybrid | baseline | 72 | 72 | 1.000 | 1.000 | 1.000 |
| hybrid | perturbed | 72 | 54 | 0.750 | 0.583 | 0.917 |
| scripted | baseline | 72 | 69 | 0.958 | 0.875 | 1.000 |
| scripted | perturbed | 72 | 3 | 0.042 | 0.000 | 0.125 |

## paired_differences

| condition | comparison | scenarios | diff_pp | ci_low_pp | ci_high_pp | mcnemar_b | mcnemar_c | mcnemar_p |
|---|---|---|---|---|---|---|---|---|
| baseline | hybrid - a11y | 24 | 0.000 | 0.000 | 0.000 | 0 | 0 | 1.000 |
| baseline | hybrid - scripted | 24 | 4.167 | 0.000 | 12.500 | 3 | 0 | 0.250 |
| baseline | a11y - scripted | 24 | 4.167 | 0.000 | 12.500 | 3 | 0 | 0.250 |
| perturbed | hybrid - a11y | 24 | 16.667 | 4.167 | 33.333 | 12 | 0 | 0.000 |
| perturbed | hybrid - scripted | 24 | 70.833 | 50.000 | 87.500 | 51 | 0 | 0.000 |
| perturbed | a11y - scripted | 24 | 54.167 | 33.333 | 75.000 | 39 | 0 | 0.000 |

## category

| category_name | config | runs | completed | rate |
|---|---|---|---|---|
| 1 Identifier change | a11y | 18 | 18 | 1.000 |
| 1 Identifier change | hybrid | 18 | 18 | 1.000 |
| 1 Identifier change | scripted | 18 | 0 | 0.000 |
| 2 Hierarchy change | a11y | 18 | 15 | 0.833 |
| 2 Hierarchy change | hybrid | 18 | 15 | 0.833 |
| 2 Hierarchy change | scripted | 18 | 0 | 0.000 |
| 3 Duplicate/generic label | a11y | 18 | 9 | 0.500 |
| 3 Duplicate/generic label | hybrid | 18 | 9 | 0.500 |
| 3 Duplicate/generic label | scripted | 18 | 3 | 0.167 |
| 4 Weak metadata | a11y | 18 | 0 | 0.000 |
| 4 Weak metadata | hybrid | 18 | 12 | 0.667 |
| 4 Weak metadata | scripted | 18 | 0 | 0.000 |

## recovery

| config | retention_n | retention_rate | after_scripted_break_n | after_scripted_break_rate |
|---|---|---|---|---|
| scripted | 69 | 0.043 | 69 | 0.000 |
| a11y | 72 | 0.583 | 69 | 0.565 |
| hybrid | 72 | 0.750 | 69 | 0.739 |

## steps

| config | condition | target_steps | step_success | structured | vlm_route | fallback_needed |
|---|---|---|---|---|---|---|
| a11y | baseline | 243 | 1.000 | 1.000 | 0.000 | 0.000 |
| a11y | perturbed | 207 | 0.870 | 0.884 | 0.000 | 0.116 |
| hybrid | baseline | 243 | 1.000 | 1.000 | 0.000 | 0.000 |
| hybrid | perturbed | 228 | 0.921 | 0.882 | 0.066 | 0.118 |
| scripted | baseline | 237 | 0.987 | 0.000 | 0.000 | 0.000 |
| scripted | perturbed | 120 | 0.450 | 0.000 | 0.000 | 0.000 |

## routes_reasons

| config | condition | route | reason | steps |
|---|---|---|---|---|
| a11y | baseline | structured | ok | 243 |
| a11y | perturbed | fallback | incompatible_state | 9 |
| a11y | perturbed | fallback | no_match | 15 |
| a11y | perturbed | structured | ok | 183 |
| hybrid | baseline | structured | ok | 243 |
| hybrid | perturbed | structured | ok | 201 |
| hybrid | perturbed | vlm | no_match | 15 |
| hybrid | perturbed | vlm_rejected | incompatible_state | 9 |
| hybrid | perturbed | vlm_rejected | no_match | 3 |

## vlm

| condition | steps_with_vlm | vlm_calls | accepted | accepted_and_correct | median_call_ms | mean_image_kb | mean_input_chars | mean_output_chars |
|---|---|---|---|---|---|---|---|---|
| perturbed | 27 | 40 | 15 | 12 | 3549.763 | 237.288 | 260.685 | 11.593 |

## vlm_reject_reasons

| reason | rejections |
|---|---|
| not_interactive | 13 |
| outside_candidate_set | 6 |
| not_text_input | 6 |

## latency

| config | condition | step_median_ms | step_p90_ms | step_p95_ms | snapshot_median_ms | resolution_median_ms | vlm_total_s | scenario_median_s | scenario_p90_s | scenario_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|
| a11y | baseline | 2423.859 | 3543.149 | 3900.642 | 682.359 | 1.970 | 0.000 | 15.017 | 20.184 | 22.837 |
| a11y | perturbed | 2284.414 | 3273.364 | 3631.354 | 615.717 | 1.979 | 0.000 | 12.038 | 19.455 | 20.214 |
| hybrid | baseline | 2408.038 | 3552.690 | 3935.582 | 690.891 | 1.991 | 0.000 | 15.021 | 20.015 | 23.028 |
| hybrid | perturbed | 2630.075 | 5334.487 | 7063.717 | 586.456 | 1.965 | 142.006 | 17.000 | 20.642 | 21.614 |
| scripted | baseline | 2430.832 | 3392.270 | 4004.965 | 693.545 |  | 0.000 | 17.199 | 26.200 | 28.940 |
| scripted | perturbed | 1693.935 | 2796.312 | 2860.641 | 594.542 |  | 0.000 | 7.480 | 15.124 | 16.236 |

## latency_tests

| condition | comparison | scenarios | median_diff_s | wilcoxon_p |
|---|---|---|---|---|
| baseline | hybrid - a11y | 24 | 0.002 | 0.877 |
| baseline | hybrid - scripted | 24 | -2.880 | 0.000 |
| baseline | a11y - scripted | 24 | -2.890 | 0.000 |
| perturbed | hybrid - a11y | 24 | 0.048 | 0.027 |
| perturbed | hybrid - scripted | 24 | 5.048 | 0.000 |
| perturbed | a11y - scripted | 24 | 2.997 | 0.012 |

## failures

| config | condition | failure | runs |
|---|---|---|---|
| a11y | perturbed | not_executed:fallback:incompatible_state | 9 |
| a11y | perturbed | not_executed:fallback:no_match | 15 |
| a11y | perturbed | postcondition_failed | 3 |
| a11y | perturbed | wrong_target:structured | 3 |
| hybrid | perturbed | not_executed:vlm_rejected:incompatible_state | 9 |
| hybrid | perturbed | postcondition_failed | 3 |
| hybrid | perturbed | wrong_target:structured | 3 |
| hybrid | perturbed | wrong_target:vlm | 3 |
| scripted | baseline | scripted_locator_not_found | 3 |
| scripted | perturbed | postcondition_failed | 3 |
| scripted | perturbed | scripted_locator_not_found | 66 |
