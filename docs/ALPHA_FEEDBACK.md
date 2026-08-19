# Alpha feedback

Agent Effects Testkit has no telemetry. Early-use feedback is explicit,
voluntary, and submitted only when a tester chooses to share it.

Select the
[Alpha adoption report](https://github.com/eschmidt01/agent-effects-testkit/issues/new?template=alpha_adoption_report.yml)
issue form. Do not attach production data, credentials, customer identifiers,
or an unredacted failure bundle.

The report asks for:

- installation method, Python version, and platform;
- agent framework, if any, and the kind of side effect tested;
- approximate time to a first passing and first intentionally failing contract;
- whether commit-boundary instrumentation was understandable;
- difficulty and time spent modeling, resetting, and snapshotting state;
- whether reduction produced an understandable, useful case;
- confusing documentation or diagnostics and requested integrations;
- whether the trial found a previously unknown defect; and
- whether the tester retained the toolkit after the trial.

Approximate values and incomplete trials are useful. Human onboarding times are
reported only from human participants. Automated validation is described as a
clean-room quickstart, never as evidence of a 15-minute human onboarding claim.

For a repeatable trial procedure, use the
[external onboarding protocol](EXTERNAL_ONBOARDING.md).
