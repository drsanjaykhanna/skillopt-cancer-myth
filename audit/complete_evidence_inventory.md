# Complete evidence inventory

This registry inventories raw experimental evidence without deciding the final manuscript narrative.
Human-review artifacts are intentionally out of scope and remain the final validation task.

## Evaluation ledgers

- Total JSONL ledgers: 153.
- Experiment families: 8.
- Usable without integrity findings: 125.
- Usable with conservative missing-as-failure handling: 27.
- Excluded pending repair: 1.
- External harness ledgers persist only the first 200 prompt characters; exact prompt identity requires linkage to launch records or immutable manifests.

## Family coverage

| Family | Ledgers | Models | FP | NFP | Status summary |
|---|---:|---:|---:|---:|---|
| Baseline capability | 18 | 8 | 8 | 8 | 13 usable; 4 usable with conservative missing-as-failure analysis; 1 exclude pending repair |
| Composite intervention | 4 | 2 | 2 | 2 | 1 usable with conservative missing-as-failure analysis; 3 usable |
| Compression | 14 | 7 | 7 | 7 | 2 usable with conservative missing-as-failure analysis; 12 usable |
| Generalisation | 27 | 3 | 18 | 9 | 5 usable with conservative missing-as-failure analysis; 22 usable |
| Legacy optimisation | 2 | 1 | 1 | 1 | 2 usable |
| Prompt strategy | 58 | 8 | 29 | 29 | 10 usable with conservative missing-as-failure analysis; 48 usable |
| Skill evaluation | 5 | 4 | 1 | 4 | 5 usable |
| Skill portability | 25 | 7 | 15 | 10 | 20 usable; 5 usable with conservative missing-as-failure analysis |

## Native optimisation runs

| Run | Target | Optimiser | Steps | Accepted | Native baseline | Native final | Delta | Skill chars |
|---|---|---|---:|---:|---:|---:|---:|---:|
| skillopt_v2_gpt4o | gpt-4o-2024-11-20 | gpt-5.4 | 24 | 2 | 16.3% | 82.7% | 66.3% | 4933 |
| skillopt_v2_gpt4o_replicate1 | gpt-4o-2024-11-20 | gpt-5.4 | 12 | 3 | 17.6% | 90.5% | 72.9% | 4414 |
| skillopt_v2_gpt4o_replicate2 | gpt-4o-2024-11-20 | gpt-5.4 | 12 | 2 | 15.4% | 82.2% | 66.8% | 5416 |
| skillopt_v2_gpt4o_compact | gpt-4o-2024-11-20 | gpt-5.4 | 24 | 2 | 15.1% | 61.2% | 46.1% | 2874 |
| skillopt_v2_gpt4o_selfopt | gpt-4o-2024-11-20 | gpt-4o-2024-11-20 | 12 | - | 16.8% | - | - | 128 |
| skillopt_v2_gpt4o_luna_opt | gpt-4o-2024-11-20 | gpt-5.6-luna | 12 | 3 | 17.6% | 58.8% | 41.2% | 7051 |
| skillopt_v2_gpt54 | gpt-5.4-2026-03-05 | gpt-5.4 | 12 | 2 | 59.5% | 89.8% | 30.2% | 5352 |
| skillopt_v2_gemini_flash | gemini-2.5-flash | gpt-5.4-2026-03-05 | 12 | 3 | 2.0% | 20.5% | 18.5% | 4806 |
| skillopt_v2_gemini35_flash | gemini-3.5-flash | gpt-5.4 | - | - | - | - | - | - |
| skillopt_v2_llama8b | us.meta.llama3-1-8b-instruct-v1:0 | gpt-5.4 | 3 | - | - | - | - | - |
| skillopt_v2_llama70b | us.meta.llama3-3-70b-instruct-v1:0 | gpt-5.4 | 4 | - | - | - | - | - |
| skillopt_v2_luna | gpt-5.6-luna | gpt-5.4 | - | - | - | - | - | - |

## Manuscript-relevant experimental layers

1. Native repeated optimisation efficacy and item-level reproducibility.
2. Optimiser-target capability and self- versus externally optimised learning curves.
3. Cross-provider and cross-scale skill portability.
4. Portability differences among independently learned skill formulations.
5. Rules versus examples across recipient-model capability.
6. Prompt-length response surfaces across model families.
7. Full versus compact learned-skill efficacy-specificity trade-offs.
8. Composite skill-plus-example interventions.
9. Near-transfer, far-transfer and adversarial true-premise controls.
10. Alternative automated-judge sensitivity analysis.
11. Thematic convergence and divergence of independently learned skills.
12. Human validation (deferred final task; not included in the current evidence base).
