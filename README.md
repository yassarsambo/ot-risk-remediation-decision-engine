# OT Risk & Remediation Decision Engine (OT-RRDE)

This project asks two questions about a security issue in operational technology (OT), the hardware and software that run industrial equipment. How soon should someone investigate? What needs checking before anyone proposes a change?

The prototype runs offline. It reads a fictional case and writes a report with its suggested next step, its reasons and the information still missing. Engineers and asset owners review the findings and authorise any real change.

The latest published set of rules is **v0.2.1**. On this research branch, v0.3 also checks the dates supplied with a forecast about a vulnerability. I’m asking engineers how they handle conflicting records in practice. [Read the short feedback brief](docs/v0.3-product-problem-brief.md).

## What a result means

The report gives a suggested investigation priority. **P1** means look into the issue immediately, **P2** means review it promptly and **P3** means schedule it for normal review. If the case leaves out an important fact, the tool can ask for more information. For example, the team may still need to confirm that the affected software is installed.

A patch proposal has its own checks. The record must show that a patch is available, the supplier has approved it, the team has tested the patch and how to undo it, and a maintenance window has been approved. A P1 investigation can therefore be urgent while a patch still needs testing.

## What changed between versions

**v0.2** added checks for equipment where an outage would have a high or critical impact. The record must show that operations has reviewed and approved the expected impact. If another system cannot take over, the team also needs an approved plan for the downtime. If it’s unclear whether another system can take over, the tool asks the team to check. A case with major or catastrophic safety consequences also requires an engineering safety review. [Availability rules and examples](docs/v0.2-availability-safeguards.md).

**v0.2.1** checks the records for protective measures such as network isolation. A measure counts only if the case identifies its type, records it as verified for the route in question, and gives a check date on or before the case date and no more than 90 days earlier. The 90 days are a setting chosen for this experiment. The code can check whether the entries agree. Checking that a measure works on site is a separate engineering task.

If the record claims that equipment is isolated but lacks the supporting check, the tool asks for evidence. A supported control record by itself never lowers the investigation priority. [Control checks and their limits](docs/v0.2.1-control-evidence-methodology.md).

**v0.3 is in development.** It checks the dates recorded for one score that estimates how likely attackers are to use a vulnerability. A score that arrived after the decision is excluded. A note bringing together conflicting records and later corrections is still a proposal.

## Run it locally

Use Python 3.10 or later. Open a terminal in the folder that contains `main.py`. Python’s standard library is sufficient. The examples use the Windows `py` command. On macOS or Linux, use `python3`.

To run the published v0.2.1 rules on the 15 test cases, use this command.

```powershell
py main.py --input data/challenge_cases_v0.2.1.json --policy policy/v0.2.1.json --output reports/v0.2.1_results.json --report reports/v0.2.1_comparison.md
```

Open `reports/v0.2.1_comparison.md` to read the comparison. The JSON file contains the results for each case. The comparison ranks the cases using severity scores from 0 to 10. The author chose these numbers for the exercise.

To repeat the v0.2 example with the five original cases, run the following.

```powershell
py main.py --policy policy/v0.2.json --output reports/v0.2_results.json --report reports/v0.2_comparison.md
```

Running `py main.py` with no options uses the original v0.1 rules. It writes `reports/example_results.json` and `reports/triage_comparison.md`.

## Check the results

```powershell
py -m unittest discover -s tests -v
py scripts/evaluate_benchmark.py
```

The second command writes `reports/v0.2.1_benchmark.md`. The expected answers for the 15 cases come from the project’s own rules. A match shows that the code followed those rules on that case. Whether its advice helps people make better decisions in practice still needs independent study. [Automated check results](https://github.com/yassarsambo/ot-risk-remediation-decision-engine/actions).

## Where to find things

| What you need | Where to look |
| --- | --- |
| Original question, assumptions and intended use | [Project specification](SPECIFICATION.md) and [use of the software](SECURITY.md) |
| Rules used for a particular run | [v0.1](policy/v0.1.json), [v0.2](policy/v0.2.json) and [v0.2.1](policy/v0.2.1.json) |
| Fictional cases | [Five original examples](data/synthetic_cases_v0.1.json) and [15 cases for v0.2.1](data/challenge_cases_v0.2.1.json) |
| How reports are produced | [Decision rules](src/decision_engine.py), [input checks](src/validator.py) and [report formatting](src/explanation.py) |
| Plan for interviews and independent case reviews | [Study notes, including links to pilot results](docs/v0.3-product-validation-notes.md) |
| How to reproduce the checks | [Tests](tests) and [v0.2.1 comparison script](scripts/evaluate_benchmark.py) |

All examples, scores, approvals and control checks are fictional. Use the software for authorised offline research and education. A person using the results would still need evidence from the actual site.
