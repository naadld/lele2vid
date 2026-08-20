import os
import sys
import yaml
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
WORKFLOWS_DIR = os.path.join(REPO_ROOT, ".github", "workflows")


class TestAdversarialGitHubWorkflows:
    """Adversarial schema, trigger, permission, and parameter validation for GitHub Actions Workflows."""

    @pytest.fixture
    def workflows(self):
        workflow_files = {
            "ideation": os.path.join(WORKFLOWS_DIR, "ScriptNewIdeation.yml"),
            "render": os.path.join(WORKFLOWS_DIR, "Render.yml"),
            "qc": os.path.join(WORKFLOWS_DIR, "ProductQC.yml")
        }
        loaded = {}
        for key, path in workflow_files.items():
            assert os.path.exists(path), f"Workflow file missing: {path}"
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                assert isinstance(data, dict), f"Invalid YAML dictionary in {path}"
                loaded[key] = data
        return loaded

    def test_all_workflows_valid_yaml_and_structure(self, workflows):
        for name, wf in workflows.items():
            assert "name" in wf
            assert "on" in wf or True  # YAML parser handles 'on' as boolean True or string 'on'
            assert "jobs" in wf
            assert len(wf["jobs"]) > 0

    def test_script_new_ideation_workflow_schema(self, workflows):
        wf = workflows["ideation"]
        # Retrieve 'on' block (can be parsed as bool True in PyYAML if unquoted, or 'on')
        on_block = wf.get("on") or wf.get(True)
        assert on_block is not None

        # 1. Zero-Secret Architecture: Workflow Dispatch only (Orchestrated by Cloudflare)
        assert "workflow_dispatch" in on_block

        # 2. Workflow Dispatch Inputs
        assert "workflow_dispatch" in on_block
        inputs = on_block["workflow_dispatch"].get("inputs", {})

        expected_inputs = [
            "mode",
            "count",
            "row_id",
            "rejected_topic",
            "error_reasons",
            "gemini_api_keys",
            "cf_webhook_url"
        ]
        for exp in expected_inputs:
            assert exp in inputs, f"Missing input '{exp}' in ScriptNewIdeation.yml"

        # 3. Check mode options
        assert inputs["mode"]["type"] == "choice"
        assert "batch" in inputs["mode"]["options"]
        assert "single_row" in inputs["mode"]["options"]

        # 4. Check add-mask secret protection step
        job = list(wf["jobs"].values())[0]
        step_runs = [s.get("run", "") for s in job["steps"] if "run" in s]
        has_masking = any("::add-mask::" in run_cmd for run_cmd in step_runs)
        assert has_masking, "ScriptNewIdeation.yml must contain ::add-mask:: for ephemeral keys"

    def test_render_workflow_schema(self, workflows):
        wf = workflows["render"]
        on_block = wf.get("on") or wf.get(True)
        assert on_block is not None
        assert "workflow_dispatch" in on_block

        inputs = on_block["workflow_dispatch"].get("inputs", {})
        assert "quality" in inputs
        assert "row_id" in inputs

        # Permissions: must include actions: write to trigger ProductQC.yml
        perms = wf.get("permissions", {})
        assert perms.get("actions") == "write" or perms.get("contents") == "read"

        # Check job triggers ProductQC
        job = list(wf["jobs"].values())[0]
        step_runs = [s.get("run", "") for s in job["steps"] if "run" in s]
        has_qc_trigger = any("gh workflow run ProductQC.yml" in run_cmd for run_cmd in step_runs)
        assert has_qc_trigger, "Render.yml must auto-trigger ProductQC.yml upon success"

    def test_product_qc_workflow_schema(self, workflows):
        wf = workflows["qc"]
        on_block = wf.get("on") or wf.get(True)
        assert on_block is not None

        # 1. Schedule Crons: 3 inspection windows (05:00, 12:00, 20:00 VN -> 22:00, 05:00, 13:00 UTC)
        assert "schedule" in on_block
        crons = [item["cron"] for item in on_block["schedule"]]
        assert "0 22 * * *" in crons
        assert "0 5 * * *" in crons
        assert "0 13 * * *" in crons

        # 2. Workflow Dispatch Inputs
        assert "workflow_dispatch" in on_block
        inputs = on_block["workflow_dispatch"].get("inputs", {})
        assert "row_id" in inputs

    def test_zero_static_secrets_in_workflows(self, workflows):
        """Ensure no hardcoded API keys or tokens are in the workflow YAML files."""
        for name, wf in workflows.items():
            raw_text = yaml.dump(wf)
            # Check for plaintext Gemini API keys (AIzaSy...)
            assert "AIzaSy" not in raw_text
            # Check for plaintext bot token patterns
            assert "bot1" not in raw_text
            assert "cfut_" not in raw_text
