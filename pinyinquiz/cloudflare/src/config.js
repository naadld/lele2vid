/**
 * Configuration manager for Cloudflare Worker
 */

export function parseKeyList(val) {
  if (!val) return [];
  return val
    .split(/[\n,]+/)
    .map(k => k.trim())
    .filter(Boolean);
}

export function getConfig(env) {
  return {
    spreadsheetId: env.SPREADSHEET_ID || "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0",
    sheetTabName: env.SHEET_TAB_NAME || "pinyin",
    
    // Service Account Credentials
    gcpClientEmail: env.GCP_SERVICE_ACCOUNT_EMAIL || "",
    gcpPrivateKey: (env.GCP_SERVICE_ACCOUNT_PRIVATE_KEY || "").replace(/\\n/g, "\n"),
    
    // Telegram
    telegramBotToken: env.TELEGRAM_BOT_TOKEN || "",
    telegramChatId: env.TELEGRAM_CHAT_ID || "",
    telegramWebhookSecret: env.TELEGRAM_WEBHOOK_SECRET || "",
    
    // GitHub Actions
    githubRepoOwner: env.GITHUB_REPO_OWNER || "naadld",
    githubRepoName: env.GITHUB_REPO_NAME || "lele2vid",
    githubWorkflowFile: env.GITHUB_WORKFLOW_FILE || "daily_render.yml",
    githubToken: env.GITHUB_TOKEN || "",
    
    // Buffer API
    bufferAccessToken: env.BUFFER_ACCESS_TOKEN || "",
    bufferClientId: env.BUFFER_CLIENT_ID || "4xqN7KBbfGLiK_ctnsgdAPWmc0W_xD8RYHdpDvy_r30",
    bufferClientSecret: env.BUFFER_CLIENT_SECRET || "wpdzWYr_DxooLd7knlEdomAbBX00jfwfMTYHvjljHib38yIPtMO2MpZfbLpOMCwFMoKKIfnVXe1TQeUIzEFlUA",
    bufferProfileIds: parseKeyList(env.BUFFER_PROFILE_IDS),
      
    // AI Providers & Key Rotation:
    // 1. Google AI Studio (6 keys)
    geminiApiKeys: parseKeyList(env.GEMINI_API_KEYS || env.GEMINI_API_KEY),
    geminiModel: env.GEMINI_MODEL || "gemini-3.6-flash",

    // 2. Agnes AI (4 keys)
    agnesApiKeys: parseKeyList(env.AGNES_API_KEYS || env.AGNES_API_KEY),
    agnesBaseUrl: env.AGNES_BASE_URL || "https://apihub.agnes-ai.com/v1",
    agnesModel: env.AGNES_MODEL || "agnes-2.0-flash",

    // 3. Cloudflare Workers AI (1 native)
    aiModel: env.AI_MODEL || "@cf/meta/llama-3.3-70b-instruct"
  };
}
