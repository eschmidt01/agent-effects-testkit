"""Regenerate the public synthetic report from the checked-in verified fixture."""

from __future__ import annotations

from pathlib import Path

from agent_effects.artifacts import FailureBundle
from agent_effects.report import write_bundle_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "failure_bundles" / "refund-lost-ack"
OUTPUT = ROOT / "docs" / "reports" / "refund-lost-ack.html"


def main() -> int:
    bundle = FailureBundle.load(FIXTURE)
    path = write_bundle_report(bundle, OUTPUT)
    print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
