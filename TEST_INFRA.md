# E2E Test Infra: Pipeline 2.0 (Lê Lê Học Tiếng Trung)

## Test Philosophy
- Requirement-driven, opaque-box and component-level verification.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Application Scenarios.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 (Unit) | Tier 2 (Boundary) | Tier 3 (Integration) | Tier 4 (Scenario) |
|---|---------|--------|:-------------:|:-----------------:|:--------------------:|:-----------------:|
| 1 | `ScriptNewIdeation.yml` Workflow | TECHNICAL_MIGRATION §3 | 5 | 5 | ✓ | ✓ |
| 2 | `Render.yml` Workflow | TECHNICAL_MIGRATION §3 | 5 | 5 | ✓ | ✓ |
| 3 | `ProductQC.yml` Workflow | TECHNICAL_MIGRATION §3 | 5 | 5 | ✓ | ✓ |
| 4 | Cloudflare Gatekeeper 1 Rules | TECHNICAL_MIGRATION §4 | 5 | 5 | ✓ | ✓ |
| 5 | Cloudflare Control Plane Endpoints | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 6 | Python Batch Generator & Dynamic Keys | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 7 | PreRenderValidator & OpenCV QC | TECHNICAL_MIGRATION §3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Framework**: `pytest` for Python engine components, Node/Wrangler test runners for Cloudflare Worker, and YAML schema validator for GitHub Actions.
- **Directories**:
  - `pinyinquiz/tests/test_linguistic_validator.py`: Tests 5 Gatekeeper linguistic criteria (Simplified Chinese, single topic, Vietnamese meaning, Pinyin 1:1, pair repetition).
  - `pinyinquiz/tests/test_pinyin_utils.py`: Tests Pinyin generation, tone marks, hidden syllable masks.
  - `pinyinquiz/tests/test_qc_inspector.py`: Tests OpenCV physical checks, brightness/contrast, cover stability, audio stream inspection.
  - `pinyinquiz/tests/test_metadata_generator.py`: Tests YouTube Shorts, TikTok, Facebook Reels formatted metadata.
  - `pinyinquiz/tests/test_batch_generator.py`: Tests dual mode, 6-key rotation logic, single-row re-gen parameter parsing.
  - `pinyinquiz/tests/test_gatekeeper_mock.py`: Tests Gatekeeper 1 decision trees, retry counters (1, 2), and 3rd-strike deletion trigger.
  - `pinyinquiz/tests/test_workflows_syntax.py`: Tests YAML syntax, triggers, inputs, steps for all 3 workflows.

## Coverage Goals
- Minimum 35 unit test cases (Tier 1 & 2)
- Zero test failures
- Strict verification before deployment
