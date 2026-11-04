# Writer queue verification

The four AWS queue checks failed against workflow revision `2c4ac0c06afe9d5001c21f70bbd6bcd4a34329fb`. The existing action suite passed 10/14 before and 14/14 after moving the four writer groups. The final ingress suite passed 9/9 against its loopback AWS CLI fixture. The actionlint check returned zero diagnostics with only the previously documented `queue` parser exception. The runtime publisher and collector both retain lease 97813003.

Run from the repository root. For the pre-change replay, create a disposable checkout of the reviewed implementation and restore just the four workflow YAML files from `2c4ac0c06afe9d5001c21f70bbd6bcd4a34329fb` inside it. This keeps the new contract check and uses the original real workflows. Provision the local dependencies described in the [action verification protocol](../PROTOCOL.md).

```sh
node docs/verification/aws-actions-20261104/run.mjs concurrency-before
# In the final checkout
node docs/verification/aws-actions-20261104/run.mjs concurrency-after
python3 docs/verification/aws-actions-20261104/ingress_e2e.py concurrency-ingress
```

[Baseline](../concurrency-before/results.json) · [Final workflow and bootstrap verification](../concurrency-after/results.json) · [Final ingress verification](../concurrency-ingress/results.json)

Suggested commit `ci: serialize AWS writers independently of the legacy ingestion queue`.
