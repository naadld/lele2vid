/**
 * GitHub Actions Workflow Dispatch Client
 * Triggers repository workflow directly from Cloudflare Worker
 */

export async function triggerGitHubRenderWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_WORKFLOW_FILE || "daily_render.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is missing in environment variables.");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const payload = {
    ref: options.ref || "main",
    inputs: {
      quality: options.quality || "qh",
      row_id: options.row_id || "",
      generate_ideas: "false" // Cloudflare Worker has already generated the ideas into Sheet
    }
  };

  console.log(`Triggering GitHub Actions workflow: ${url} on ref '${payload.ref}'`);

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
