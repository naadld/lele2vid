/**
 * GitHub Actions Workflow Dispatch Client for Pipeline 2.0
 * Triggers repository workflows directly from Cloudflare Worker with Zero-Secret dynamic parameters.
 */

/**
 * Format and extract comma-separated Gemini API keys from environment
 */
function getEphemeralGeminiKeys(env) {
  const raw = env.GEMINI_API_KEYS || env.GEMINI_API_KEY || "";
  if (!raw) return "";
  if (Array.isArray(raw)) {
    return raw.map(k => String(k).trim()).filter(Boolean).join(",");
  }
  return String(raw)
    .split(/[\n,]+/)
    .map(k => k.trim())
    .filter(Boolean)
    .join(",");
}

/**
 * Trigger Ideation Workflow (ScriptNewIdeation.yml)
 * Supports Step 1 (Batch 30) and Step 2 (Single-Row Re-generation)
 */
export async function triggerGitHubIdeationWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_IDEATION_WORKFLOW_FILE || "vocabvn_ideation.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is missing in environment variables.");
  }

  const ephemeralGeminiKeys = getEphemeralGeminiKeys(env);
  const webhookUrl = options.cf_webhook_url || env.CF_WEBHOOK_URL || "https://lele-pinyinquiz.hothihuong113.workers.dev/api/receive-ideas";

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const payload = {
    ref: options.ref || "main",
    inputs: {
      mode: options.mode || "batch",
      count: String(options.count || "5"),
      level: String(options.level || ""),
      row_id: String(options.row_id || ""),
      rejected_topic: String(options.rejected_topic || ""),
      error_reasons: String(options.error_reasons || ""),
      gemini_api_keys: ephemeralGeminiKeys,
      cf_webhook_url: webhookUrl
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching '${workflow}' (mode: ${payload.inputs.mode}, row_id: '${payload.inputs.row_id}') to ${owner}/${repo}`);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "Cloudflare-Worker-LeLeHocTiengTrung",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (response.status === 204) {
    return {
      success: true,
      message: `Đã kích hoạt thành công GitHub Action '${workflow}' (Mode: ${payload.inputs.mode}) trên repo ${owner}/${repo}!`
    };
  }

  const errBody = await response.text();
  throw new Error(`GitHub API Error (${response.status}): ${errBody}`);
}

/**
 * Trigger Video Render Workflow (Render.yml)
 */
export async function triggerGitHubRenderWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_WORKFLOW_FILE || "Render.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is missing in environment variables.");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const payload = {
    ref: options.ref || "main",
    inputs: {
      quality: options.quality || "qh",
      row_id: String(options.row_id || "")
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching Render workflow: ${url} on ref '${payload.ref}' (row_id: '${payload.inputs.row_id}')`);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "Cloudflare-Worker-LeLeHocTiengTrung",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (response.status === 204) {
    return {
      success: true,
      message: `Đã kích hoạt thành công GitHub Action workflow '${workflow}' trên repo ${owner}/${repo}!`
    };
  }

  const errBody = await response.text();
  throw new Error(`GitHub API Error (${response.status}): ${errBody}`);
}

/**
 * Trigger Auto-QC Physical Video Inspection Workflow (ProductQC.yml)
 */
export async function triggerGitHubQCWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_QC_WORKFLOW_FILE || "vocabvn_qc.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is missing in environment variables.");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const payload = {
    ref: options.ref || "main",
    inputs: {
      row_id: String(options.row_id || "")
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching Auto-QC workflow: ${url} on ref '${payload.ref}' (row_id: '${payload.inputs.row_id}')`);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "Cloudflare-Worker-LeLeHocTiengTrung",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (response.status === 204) {
    return {
      success: true,
      message: `Đã kích hoạt thành công ProductQC workflow '${workflow}' trên repo ${owner}/${repo}!`
    };
  }

  const errBody = await response.text();
  throw new Error(`GitHub API Error (${response.status}): ${errBody}`);
}
