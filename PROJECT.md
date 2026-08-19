# Project: Pipeline 2.0 Upgrade for Lê Lê Học Tiếng Trung (@lelehoctiengtrung)

## Architecture
Pipeline 2.0 implements a High-Security Zero-Secret & Multi-Tier AI Gatekeeper architecture:
1. **Auditor & Control Plane (Cloudflare Worker)**:
   - Resides on Cloudflare Edge with bindings to Workers AI, KV/D1, and Secrets Vault.
   - Holds encrypted Google AI Studio Gemini API keys (`GEMINI_API_KEYS`).
   - Dispatches `ScriptNewIdeation.yml` to GitHub Actions with ephemeral keys in `workflow_dispatch` payload (zero secrets stored in GitHub).
   - Ingests generated ideas via webhook `POST /api/receive-ideas`.
   - Gatekeeper 1 AI Judge (Agnes AI `agnes-2.0-flash` + Workers AI fallback) enforces 5 strict linguistic criteria, manages 2 retries (Step 2 re-gen), and deletes rows from Google Sheet on the 3rd consecutive violation.
   - Triggers 3x daily publishing windows (07:00, 13:00, 19:00 GMT+7) to Buffer GraphQL API (YouTube Shorts, TikTok, Facebook Reels).
2. **Creator & Rendering Plane (GitHub Actions in US)**:
   - High-compute environment with Manim 0.19.0, FFmpeg, OpenCV headless, Python 3.11+.
   - `ScriptNewIdeation.yml`: Step 1 (30 ideas with 60s sequential delay + 6 rotating keys + 100-row Sheet negative context) and Step 2 (single-row re-gen without error recurrence).
   - `Render.yml`: Manim 1080x1920 60fps MP4, 0.75s Cover Intro Frame hold at `00:00:00`, Edge-TTS Chinese audio, uploads to Google Drive (`1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`), sets Sheet to `Video`, auto-triggers `ProductQC.yml`.
   - `ProductQC.yml`: Post-render OpenCV & FFprobe physical inspection (Frame 00:00 brightness in [10, 245], contrast $\ge 15.0$, cover hold stability $\le 60.0$, audio channels $\ge 1$, duration 15-120s), updating status to `Ready` or `QC_Failed`.
3. **Database & Storage Plane**:
   - Google Sheet: 16-column database (`#`, `Topic`, `Level`, `Status`, `Word 1`..`Word 5`, `metadata`, `Video`, `Youtube`, `Tiktok`, `Facebook`, `Created At`, `Notes`).
   - Google Drive: Central video asset archive (`1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `ScriptNewIdeation.yml` Batch 30 | 30 ideas weekly with 60s delay, 6-key rotation, 100-row Sheet negative context | M1 | Survey |
| 2 | `ScriptNewIdeation.yml` Single-Row Re-gen | Targeted single-row re-generation upon Gatekeeper rejection | M1 | Survey |
| 3 | `Render.yml` Manim High-Quality Render | 1080x1920 60fps, 0.75s Cover frame, Edge-TTS audio, GDrive upload, auto-QC trigger | M1 | Survey |
| 4 | `ProductQC.yml` Physical Video Inspection | OpenCV & FFprobe check (brightness, contrast, cover stability, audio, duration) | M1 | Survey |
| 5 | Gatekeeper 1 AI Judge | Agnes AI + Workers AI fallback independent linguistic evaluation | M2 | Survey |
| 6 | 5 Strict Linguistic & Content Criteria | 100% Simplified Chinese, Single Topic Only, 100% VN meaning, 1:1 Pinyin tone, zero pair repetition | M2 | Survey |
| 7 | Retry 2x & 3rd-Violation Row Deletion | Retry tracking with Step 2 dispatch, row deletion from Google Sheet on 3rd failure | M2 | Survey |
| 8 | `POST /api/receive-ideas` Webhook | Ingests ideas from GitHub Actions, runs Gatekeeper 1, updates Google Sheet | M2 | Survey |
| 9 | Dynamic Ephemeral Key Dispatch | Injects Gemini keys into GitHub workflow_dispatch payload (zero GitHub secrets) | M2 | Survey |
| 10 | Production & 3x Publishing Crons | Saturday 00:01 GMT+7 ideation; 07:00, 13:00, 19:00 GMT+7 Buffer publishing | M2 | Survey |
| 11 | Buffer GraphQL Multi-Platform Publishing | Publishes video to YouTube Shorts, TikTok, Facebook Reels with tailored metadata | M2 | Survey |
| 12 | `generate_daily_batches.py` Dynamic Key Engine | Supports dynamic keys, 100-row Sheet negative context, 60s delay, single-row re-gen, webhook POST | M3 | Survey |
| 13 | Direct Google AI Studio Integration | `llm_client.py` direct Gemini 3.7 Flash API calls with model failover and key rotation | M3 | Survey |
| 14 | Pipeline 2.0 Runner Updates | Update `run_batch.py` and `run_qc.py` for GDrive folder ID and workflow chaining | M3 | Survey |
| 15 | Corrupted Asset Cleanup | Remove/fix corrupted font `NotoSansSC-Bold.otf` | M3 | Survey |
| 16 | Comprehensive Test Suite (Tiers 1-4) | Unit & integration tests for validators, QC inspector, Pinyin utils, Gatekeeper rules | M4 | Survey |
| 17 | Cloudflare Worker Node 22 Deployment | Deploy Cloudflare Worker with Wrangler CLI and verify live diagnostic endpoints | M5 | Survey |
| 18 | Git Commit & Push | Commit with message `"feat: upgrade pipeline to v2.0 with zero-secret GitHub Actions and multi-tier gatekeeper"` | M5 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | GitHub Actions 3-Workflow Architecture | Create `ScriptNewIdeation.yml`, `Render.yml`, `ProductQC.yml` | None | PLANNED |
| M2 | Cloudflare Worker Gatekeeper & Control Plane | Implement `gatekeeper.js`, update `index.js`, `github_trigger.js`, `wrangler.toml` | None | PLANNED |
| M3 | Python Engine & Script Optimization | Overhaul `generate_daily_batches.py`, `llm_client.py`, `run_batch.py`, clean assets | None | PLANNED |
| M4 | Comprehensive Unit & E2E Testing Suite | Build and run test suite across Tiers 1-4; publish `TEST_READY.md` | M1, M2, M3 | PLANNED |
| M5 | Deployment, Verification & Git Commit/Push | Deploy worker with Node 22 Wrangler, verify endpoints, git commit & push | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### GitHub Actions (`ScriptNewIdeation.yml`) ↔ Cloudflare Worker (`/api/receive-ideas`)
- Method: `POST https://<worker-domain>/api/receive-ideas`
- Payload:
  ```json
  {
    "row_id": "batch_20260819_01",
    "topic": "Đồ Dùng Nhà Bếp",
    "level": "HSK 1",
    "words": [
      { "hanzi": "筷子", "pinyin": "kuài zi", "hidden_pinyin": "k _ _ _   z _", "meaning": "Đôi đũa" }
    ],
    "metadata": { "yt_title": "...", "description": "...", "tags": "..." },
    "retry_count": 0
  }
  ```
- Response (Pass): `HTTP 200 { "success": true, "status": "Pending", "row_id": "...", "action": "saved_to_sheet" }`
- Response (Reject Retry 1-2): `HTTP 200 { "success": false, "status": "Rejected", "action": "call_step_2", "retry_count": 1, "error_reasons": ["..."] }`
- Response (Reject Strike 3): `HTTP 200 { "success": false, "status": "Deleted", "action": "delete_row", "retry_count": 3, "error_reasons": ["..."] }`

### Cloudflare Worker (`github_trigger.js`) ↔ GitHub Actions (`workflow_dispatch`)
- Method: `POST https://api.github.com/repos/naadld/lele2vid/actions/workflows/ScriptNewIdeation.yml/dispatches`
- Payload:
  ```json
  {
    "ref": "main",
    "inputs": {
      "mode": "batch",
      "count": "30",
      "gemini_api_keys": "key1,key2,key3,key4,key5,key6",
      "cf_webhook_url": "https://lele-pinyinquiz.aleron-dt.workers.dev/api/receive-ideas"
    }
  }
  ```

### Render Workflow (`Render.yml`) ↔ QC Workflow (`ProductQC.yml`)
- Trigger: Upon successful render and GDrive upload, `Render.yml` triggers `ProductQC.yml` via GitHub API with `row_id`.

## Code Layout
```
/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/
├── .github/workflows/
│   ├── ScriptNewIdeation.yml
│   ├── Render.yml
│   └── ProductQC.yml
├── pinyinquiz/
│   ├── cloudflare/
│   │   ├── wrangler.toml
│   │   ├── package.json
│   │   └── src/
│   │       ├── index.js
│   │       ├── gatekeeper.js
│   │       ├── github_trigger.js
│   │       ├── buffer_publisher.js
│   │       ├── google_sheets.js
│   │       ├── ai_ideation.js
│   │       ├── metadata_helper.js
│   │       ├── pinyin_helper.js
│   │       ├── telegram.js
│   │       └── config.js
│   ├── src/
│   │   ├── config.py
│   │   ├── pinyin_utils.py
│   │   ├── audio_generator.py
│   │   ├── metadata_generator.py
│   │   ├── thumbnail_generator.py
│   │   ├── scene_generator.py
│   │   ├── render_engine.py
│   │   ├── pre_render_validator.py
│   │   ├── qc_inspector.py
│   │   ├── gsheet_manager.py
│   │   ├── gdrive_uploader.py
│   │   └── llm_client.py
│   ├── scripts/
│   │   ├── generate_daily_batches.py
│   │   ├── run_batch.py
│   │   └── run_qc.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_linguistic_validator.py
│   │   ├── test_pinyin_utils.py
│   │   ├── test_qc_inspector.py
│   │   ├── test_metadata_generator.py
│   │   └── test_gatekeeper_rules.py
│   └── assets/
```
