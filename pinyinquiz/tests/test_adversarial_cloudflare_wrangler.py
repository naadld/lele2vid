import os
import sys
import tomllib
import subprocess
import pytest
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOUDFLARE_DIR = os.path.join(PROJECT_ROOT, "cloudflare")
WRANGLER_TOML = os.path.join(CLOUDFLARE_DIR, "wrangler.toml")


class TestAdversarialCloudflareWorkerAndWrangler:
    """Adversarial validation of Cloudflare Worker configuration, bindings, crons, and JS syntax."""

    @pytest.fixture
    def wrangler_config(self):
        assert os.path.exists(WRANGLER_TOML), f"wrangler.toml missing at {WRANGLER_TOML}"
        with open(WRANGLER_TOML, "rb") as f:
            data = tomllib.load(f)
        return data

    def test_wrangler_toml_basic_structure_and_flags(self, wrangler_config):
        assert wrangler_config["name"] == "lele-pinyinquiz"
        assert wrangler_config["main"] == "src/index.js"
        assert "nodejs_compat" in wrangler_config.get("compatibility_flags", [])

    def test_cloudflare_ai_binding(self, wrangler_config):
        ai = wrangler_config.get("ai")
        assert ai is not None, "Missing [ai] section in wrangler.toml"
        assert ai.get("binding") == "AI", "Workers AI binding must be named 'AI'"

    def test_cron_expressions_syntax_and_limits(self, wrangler_config):
        triggers = wrangler_config.get("triggers")
        assert triggers is not None, "Missing [triggers] section in wrangler.toml"
        crons = triggers.get("crons", [])
        
        # Cloudflare Free Plan limit: max 5 cron triggers
        assert len(crons) <= 5, f"Too many cron triggers ({len(crons)} > 5)"
        assert len(crons) >= 2, f"Expected at least 2 cron triggers, got {len(crons)}"

        # Validate each cron format (5 standard fields)
        cron_field_regex = re.compile(r"^[0-9\*\,\-\/]+$")
        for c in crons:
            parts = c.split()
            assert len(parts) == 5, f"Cron '{c}' does not have exactly 5 fields"
            for p in parts:
                assert cron_field_regex.match(p), f"Invalid cron field '{p}' in '{c}'"

        # Verify specific required production crons
        # 1. Saturday 00:01 GMT+7 / Friday 17:01 UTC
        assert "1 17 * * 5" in crons
        # 2. 3x Daily Buffer publishing (00:00, 06:00, 12:00 UTC)
        assert "0 0,6,12 * * *" in crons or ("0 0 * * *" in crons and "0 6 * * *" in crons and "0 12 * * *" in crons)

    def test_environment_variables_bindings(self, wrangler_config):
        vars_dict = wrangler_config.get("vars", {})
        required_vars = [
            "SPREADSHEET_ID",
            "SHEET_TAB_NAME",
            "GITHUB_REPO_OWNER",
            "GITHUB_REPO_NAME",
            "CF_WEBHOOK_URL",
            "GEMINI_MODEL",
            "AGNES_MODEL",
            "AGNES_BASE_URL"
        ]
        for rv in required_vars:
            assert rv in vars_dict, f"Missing required env var '{rv}' in wrangler.toml [vars]"

    def test_javascript_syntax_validity_all_sources(self):
        """Validate that all JavaScript files in cloudflare/src/ pass Node.js syntax check."""
        src_dir = os.path.join(CLOUDFLARE_DIR, "src")
        assert os.path.exists(src_dir)

        js_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".js")]
        assert len(js_files) > 0, "No JS files found in cloudflare/src/"

        for js_path in js_files:
            cmd = ["node", "--check", js_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            assert res.returncode == 0, f"JavaScript syntax error in {js_path}: {res.stderr}"
