# Locked Native Primary Analysis

## Analysis population

- Population: 410 false-presupposition questions in the persisted 2:1:7 split test partition.
- Design: within-execution paired comparison of each native baseline ledger with that execution's post-optimisation ledger.
- Outcome: false-presupposition correction rate, defined as a hard judge score of 1.
- Every ledger contains exactly the same 410 unique IDs; binary scores, question text and persisted summaries were validated before analysis.
- The three executions use the same split and recorded training seed. They quantify execution-to-execution variability but are not independent random-seed replications.

## Results by execution

- `skillopt_v2_gpt4o`: baseline 16.3% (95% CI 13.1-20.2); post-optimisation 82.7% (95% CI 78.7-86.0); paired change +66.3 percentage points (bootstrap 95% CI +61.7 to +71.0); exact McNemar p=1.812e-80, Holm-adjusted p=1.812e-80.
- `skillopt_v2_gpt4o_replicate1`: baseline 17.6% (95% CI 14.2-21.5); post-optimisation 90.5% (95% CI 87.3-93.0); paired change +72.9 percentage points (bootstrap 95% CI +68.5 to +77.3); exact McNemar p=1.964e-90, Holm-adjusted p=5.891e-90.
- `skillopt_v2_gpt4o_replicate2`: baseline 15.4% (95% CI 12.2-19.2); post-optimisation 82.2% (95% CI 78.2-85.6); paired change +66.8 percentage points (bootstrap 95% CI +62.2 to +71.2); exact McNemar p=6.589e-83, Holm-adjusted p=1.318e-82.

## Across-execution description

- Baseline mean 16.4% (range 15.4-17.6%).
- Post-optimisation mean 85.1% (range 82.2-90.5%).
- Paired improvement mean 68.7 percentage points (range 66.3-72.9).
- These means and ranges are descriptive; no pooled item-level confidence interval treats the 1,230 observations as independent.

## Artifact lineage

- `skillopt_v2_gpt4o`: best step 3, 2 accepted rewrites, skill length 4933 characters, SHA-256 `7b2d733d2736295a54115ca6981a3cc075934389311c2196a33f3d4000e46113`.
- `skillopt_v2_gpt4o_replicate1`: best step 12, 3 accepted rewrites, skill length 4414 characters, SHA-256 `98cc6816a9605068ab2f5ab50585d067058354175051d0f24191327f10c13a85`.
- `skillopt_v2_gpt4o_replicate2`: best step 3, 2 accepted rewrites, skill length 5416 characters, SHA-256 `83d8d5f5366b1ce61189b4a20166c79db56e0368e44fc3ed878c06fd296f3556`.

## Interpretation guardrails

- This is the primary efficacy analysis because the baseline and post-optimisation records arise from the native run structure and use the same held-out population.
- The external harness passed the full prompt to the target model but persisted only its first 200 characters. The ledger named `skillopt_v2_gpt4o_best` has a logged prefix that does not match the current native best skill, so its exact prompt identity and 93.2% result are excluded from primary SkillOpt inference.
- Native post-optimisation ledgers do not include the NFP negative controls. Specificity must therefore be reported from separate, prompt-verified external evaluations and cannot be represented as a native co-primary endpoint.
- The current gate optimised one aggregate hard score over a mixed FP/NFP validation set. It was not a strict dual-objective non-regression gate.
