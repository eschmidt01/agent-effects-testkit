# External onboarding protocol

This is a self-contained, asynchronous trial for an engineer who has not worked
in this repository. It is not an interview and the toolkit sends no telemetry.
Record actual elapsed times rather than trying to meet a target.

## Before starting

Use a disposable directory and synthetic data. Obtain the wheel from a verified
GitHub prerelease, or directly from the maintainer for a pre-release trial.
Record the wheel filename, Python version, operating system, and start time.

## Trial

1. Create a virtual environment and install the wheel plus pytest.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install ./agent_effects_testkit-0.1.0a1-py3-none-any.whl pytest
   agent-effects doctor
   ```

2. Generate and run the normal passing starter.

   ```bash
   mkdir passing-trial
   cd passing-trial
   agent-effects init .
   pytest -q
   cd ..
   ```

3. Run the explicit lost-acknowledgment demonstration.

   ```bash
   agent-effects init lost-ack-trial --template lost-ack
   cd lost-ack-trial
   pytest -q
   ```

   The test is intentionally expected to fail for a duplicate effect and print
   a failure-bundle path.

4. Inspect, verify, and reproduce the bundle. Verification and inspection do
   not execute adapter code. Reproduction executes installed registered code.

   ```bash
   agent-effects bundle verify .agent-effects/failures/<bundle>
   agent-effects bundle inspect .agent-effects/failures/<bundle>
   agent-effects reproduce --dry-run .agent-effects/failures/<bundle>
   agent-effects reproduce .agent-effects/failures/<bundle>
   ```

5. Follow the generated README to enable stable idempotency and rerun `pytest
   -q`; the same contracts should pass.

6. Where practical, adapt one deterministic contract to a small stateful
   workflow of your own. Use only a test environment and synthetic data. Record
   time spent modeling state and locating the operation's durable commit
   boundary separately.

7. Submit the voluntary **Alpha adoption report** issue form. A partial report is
   welcome if the trial could not be completed.

## Metrics to record

```text
Install succeeded: yes / no
Time to first test result:
Time to first custom contract:
Time spent modeling/resetting/snapshotting state:
Time spent locating the durable commit boundary:
Reduced case understandable: yes / partly / no / not produced
Previously unknown defect found: yes / no / unsure
Toolkit retained after trial: yes / no / decision pending
Blocking or confusing step:
```

An automated clean-room quickstart exists in `scripts/clean_room_acceptance.py`.
It validates packaging and the documented mechanics, but it is not a human
onboarding-time measurement.
