# Visual asset provenance

All assets are local, synthetic, and free of remote fonts, scripts, analytics,
tracking pixels, stock imagery, and model-generated art.

| Asset | Source and maintenance |
| --- | --- |
| `hero-lost-ack-light.svg` | Manually maintained incident-style transaction trace using flat system colors and no generated artwork. |
| `hero-lost-ack-dark.svg` | Manually maintained dark-mode counterpart with identical content and accessible description. |
| `agent-effects-demo.gif` | Generated from `source/agent-effects-demo.tape`; the recording uses the packaged CLI and synthetic refund example. |
| `failure-report.png` | Browser capture of the deterministic synthetic report in `docs/reports/refund-lost-ack.html`. |
| `social-preview.png` | Generated from the manually maintained `source/social-preview.svg` at 1280×640. |

Regenerate the report before capturing screenshots:

```bash
python scripts/generate_failure_report.py
vhs docs/assets/source/agent-effects-demo.tape
```

The GIF source assumes an environment where `agent-effects` resolves to the
current built/installed package and `.agent-effects/` does not already exist.
Generate it from a clean checkout or move prior local artifacts aside first;
this keeps the bundle wildcard unambiguous without deleting user data. Before
committing a new recording, inspect its first, middle, and final frames and
confirm that no absolute path, username, failed command, or unfinished command
is visible. The report screenshot is intentionally a raster capture; the report
HTML and hero SVGs remain the accessible source artifacts.
