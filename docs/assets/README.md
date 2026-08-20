# Visual asset provenance

All assets are local, synthetic, and free of remote fonts, scripts, analytics,
tracking pixels, stock imagery, and model-generated art.

| Asset | Source and maintenance |
| --- | --- |
| `hero-lost-ack-light.svg` | Manually maintained semantic transaction diagram. |
| `hero-lost-ack-dark.svg` | Manually maintained dark-mode counterpart with the same content and accessible description. |
| `agent-effects-demo.gif` | Generated from `source/agent-effects-demo.tape`; the recording uses the packaged CLI and synthetic refund example. |
| `failure-report.png` | Browser capture of the deterministic synthetic report in `docs/reports/refund-lost-ack.html`. |
| `social-preview.png` | Generated from `source/social-preview.svg` at 1280×640. |

Regenerate the report before capturing screenshots:

```bash
python scripts/generate_failure_report.py
vhs docs/assets/source/agent-effects-demo.tape
```

The GIF source assumes an environment where `agent-effects` resolves to the
current built/installed package. Review the terminal output before committing a
new recording. The report screenshot is intentionally a raster capture; the
report HTML and hero SVGs remain the accessible source artifacts.
