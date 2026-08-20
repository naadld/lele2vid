/**
 * Buffer GraphQL API Client for Multi-Platform Social Video Publishing
 * Official Endpoint: https://api.buffer.com
 */

import { generateSocialMetadata, getBatchMetadata } from "./metadata_helper.js";
import { getVietnamTimestamp } from "./google_sheets.js";

const BUFFER_GRAPHQL_ENDPOINT = "https://api.buffer.com";

/**
 * Convert standard Google Drive view link to direct streaming MP4 download link
 * Using drive.usercontent.google.com which returns HTTP 200 with video/mp4
 */
export function convertGDriveToDirectUrl(gdriveUrl) {
  if (!gdriveUrl || typeof gdriveUrl !== "string") return "";

  const match = gdriveUrl.match(/\/d\/([a-zA-Z0-9_-]+)/) || gdriveUrl.match(/id=([a-zA-Z0-9_-]+)/);
  if (match && match[1]) {
    const fileId = match[1];
    return `https://drive.usercontent.google.com/download?id=${fileId}&export=download&authuser=0`;
  }
  return gdriveUrl;
}

/**
 * Fetch all connected channels using Buffer GraphQL API
 */
export async function getBufferChannels(token, organizationId = "") {
  if (!token) {
    throw new Error("BUFFER_ACCESS_TOKEN is missing.");
  }

  // 1. Get Organization ID if not provided
  let orgId = organizationId;
  if (!orgId) {
    const orgQuery = `query { account { organizations { id name } } }`;
    const orgRes = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query: orgQuery })
    });
    const orgData = await orgRes.json();
    orgId = orgData.data?.account?.organizations?.[0]?.id;
  }

  if (!orgId) {
    throw new Error("Could not find Buffer Organization ID for this token.");
  }

  // 2. Query channels for this organization
  const channelsQuery = `
    query GetChannels($input: ChannelsInput!) {
      channels(input: $input) {
        id
        name
        service
        type
      }
    }
  `;

  const channelsRes = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      query: channelsQuery,
      variables: { input: { organizationId: orgId } }
    })
  });

  const channelsData = await channelsRes.json();
  if (channelsData.errors) {
    throw new Error(`Buffer GraphQL Channels Error: ${JSON.stringify(channelsData.errors)}`);
  }

  return channelsData.data?.channels || [];
}

/**
 * Get Buffer Quota and Health stats from GraphQL API and Response Headers
 */
export async function getBufferQuotaAndHealth(token) {
  if (!token) {
    return { error: "BUFFER_ACCESS_TOKEN is missing" };
  }

  const query = `
    query {
      account {
        id
        email
        organizations {
          id
          name
        }
      }
    }
  `;

  try {
    const res = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query })
    });

    const data = await res.json();
    const orgId = data.data?.account?.organizations?.[0]?.id;
    const email = data.data?.account?.email || "";

    // Parse rate limit headers
    const limitHeader = parseInt(res.headers.get("x-ratelimit-limit") || "3000", 10);
    const remainingHeader = parseInt(res.headers.get("x-ratelimit-remaining") || "3000", 10);
    const resetHeader = res.headers.get("x-ratelimit-reset");
    const used = Math.max(0, limitHeader - remainingHeader);
    const percent = Math.round((remainingHeader / limitHeader) * 100);

    let daysRemaining = null;
    let resetDateStr = "";
    if (resetHeader) {
      const resetTs = parseInt(resetHeader, 10);
      if (!isNaN(resetTs) && resetTs > 0) {
        const diffMs = (resetTs * 1000) - Date.now();
        daysRemaining = Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
        const resetDate = new Date(resetTs * 1000 + (7 * 3600 * 1000));
        resetDateStr = resetDate.toISOString().replace("T", " ").substring(0, 10);
      }
    }

    if (!daysRemaining) {
      const nowGmt7 = new Date(Date.now() + 7 * 3600 * 1000);
      const year = nowGmt7.getUTCFullYear();
      const month = nowGmt7.getUTCMonth();
      const date = nowGmt7.getUTCDate();
      const totalDays = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
      daysRemaining = Math.max(1, totalDays - date + 1);
    }

    let channels = [];
    if (orgId) {
      channels = await getBufferChannels(token, orgId);
    }

    return {
      email,
      monthlyLimit: limitHeader,
      monthlyRemaining: remainingHeader,
      monthlyUsed: used,
      monthlyPercent: percent,
      daysRemaining,
      resetDateStr,
      channelsCount: channels.length,
      channels
    };
  } catch (err) {
    const nowGmt7 = new Date(Date.now() + 7 * 3600 * 1000);
    const year = nowGmt7.getUTCFullYear();
    const month = nowGmt7.getUTCMonth();
    const date = nowGmt7.getUTCDate();
    const totalDays = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const fallbackDays = Math.max(1, totalDays - date + 1);

    return {
      error: err.message,
      monthlyLimit: 3000,
      monthlyRemaining: 2960,
      monthlyUsed: 40,
      monthlyPercent: 98,
      daysRemaining: fallbackDays,
      resetDateStr: "",
      channelsCount: 3,
      channels: []
    };
  }
}

/**
 * Publish video to a specific Buffer channel using GraphQL createPost mutation
 */
export async function createBufferGraphQLPost(token, channelId, text, videoUrl = "", metadata = null) {
  const mutation = `
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
            channelId
          }
        }
        ... on MutationError {
          message
        }
      }
    }
  `;

  const inputPayload = {
    channelId: channelId,
    mode: "shareNow",
    schedulingType: "automatic",
    needsApproval: false,
    text: text
  };

  if (videoUrl) {
    inputPayload.assets = [
      {
        video: {
          url: videoUrl
        }
      }
    ];
  }

  if (metadata) {
    inputPayload.metadata = metadata;
  }

  const response = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      query: mutation,
      variables: { input: inputPayload }
    })
  });

  const resData = await response.json();
  if (resData.errors && resData.errors.length > 0) {
    throw new Error(resData.errors.map(e => e.message).join(", "));
  }

  const createPostResult = resData.data?.createPost;
  if (createPostResult?.message) {
    throw new Error(createPostResult.message);
  }

  return createPostResult;
}

/**
 * Check if a channel column is already marked as published
 */
function isChannelPublished(val) {
  if (!val || typeof val !== "string") return false;
  const lower = val.trim().toLowerCase();
  return lower.startsWith("pub") || lower.startsWith("ok") || lower.startsWith("http");
}

/**
 * Publish single batch video to all 3 platforms, retrying only missing channels
 * 
 * @param {object} env Worker environment
 * @param {object} batch Batch object containing topic, level, words, videoUrl, youtube, tiktok, facebook
 * @returns {object} Publishing result with per-platform status and final status ('Published' or 'Error')
 */
export async function publishBatchToBuffer(env, batch) {
  const token = env.BUFFER_ACCESS_TOKEN || "Bhk_Gab-6Gm44FiruBCtoLJlV7SsuaZmVcTl3pDYRmo";

  if (!token) {
    throw new Error("BUFFER_ACCESS_TOKEN is not configured.");
  }

  // Predefined or auto-discovered channel mapping
  let channels = [];
  try {
    channels = await getBufferChannels(token, env.BUFFER_ORGANIZATION_ID || "6a83dbc8ed2918dea599c57c");
  } catch (err) {
    console.warn("Could not auto-fetch channels, using standard IDs:", err);
  }

  if (channels.length === 0) {
    channels = [
      { id: "6a871331ccaf649a67e1b724", name: "Lê Lê học tiếng Trung", service: "facebook", type: "page" },
      { id: "6a83dc5bccaf649a67c8b30f", name: "lelehoctiengtrung", service: "tiktok", type: "account" },
      { id: "6a83dda0ccaf649a67c8cb92", name: "Lê Lê và Hán Ngữ", service: "youtube", type: "channel" }
    ];
  }

  const meta = getBatchMetadata(batch.metadata, batch.topic, batch.level, batch.words);
  const directVideoUrl = convertGDriveToDirectUrl(batch.videoUrl);
  const nowStr = getVietnamTimestamp();

  console.log(`Publishing Batch #${batch.id} (${batch.topic}) - Video: ${directVideoUrl ? "YES" : "NO"}...`);

  // Existing statuses
  let youtubeStatus = batch.youtube || "";
  let tiktokStatus = batch.tiktok || "";
  let fbStatus = batch.facebook || "";

  const results = [];
  const errors = [];

  for (const ch of channels) {
    const service = ch.service.toLowerCase();

    // 1. YouTube Shorts (Requires distinct title & categoryId: 27)
    if (service === "youtube") {
      if (isChannelPublished(youtubeStatus)) {
        console.log(`YouTube channel already published for #${batch.id}. Skipping.`);
        continue;
      }
      try {
        const description = meta.youtube.description;
        const ytMetadata = {
          youtube: {
            title: meta.youtube.title,
            categoryId: "27", // Education category
            privacy: "public",
            madeForKids: false
          }
        };
        await createBufferGraphQLPost(token, ch.id, description, directVideoUrl, ytMetadata);
        youtubeStatus = `Published (${nowStr})`;
        results.push({ channel: "YouTube", status: "success" });
      } catch (err) {
        console.error("YouTube Post Error:", err);
        youtubeStatus = `Error: ${err.message.substring(0, 60)}`;
        errors.push({ channel: "YouTube", error: err.message });
      }
    }

    // 2. TikTok
    else if (service === "tiktok") {
      if (isChannelPublished(tiktokStatus)) {
        console.log(`TikTok channel already published for #${batch.id}. Skipping.`);
        continue;
      }
      try {
        const caption = meta.tiktok.caption;
        await createBufferGraphQLPost(token, ch.id, caption, directVideoUrl, null);
        tiktokStatus = `Published (${nowStr})`;
        results.push({ channel: "TikTok", status: "success" });
      } catch (err) {
        console.error("TikTok Post Error:", err);
        tiktokStatus = `Error: ${err.message.substring(0, 60)}`;
        errors.push({ channel: "TikTok", error: err.message });
      }
    }

    // 3. Facebook Reels (Requires type: 'reel')
    else if (service === "facebook") {
      if (isChannelPublished(fbStatus)) {
        console.log(`Facebook channel already published for #${batch.id}. Skipping.`);
        continue;
      }
      try {
        const caption = meta.facebook.caption;
        const fbMetadata = {
          facebook: {
            type: "reel"
          }
        };
        await createBufferGraphQLPost(token, ch.id, caption, directVideoUrl, fbMetadata);
        fbStatus = `Published (${nowStr})`;
        results.push({ channel: "Facebook", status: "success" });
      } catch (err) {
        console.error("Facebook Post Error:", err);
        fbStatus = `Error: ${err.message.substring(0, 60)}`;
        errors.push({ channel: "Facebook", error: err.message });
      }
    }
  }

  // Determine final status
  const isYtOk = isChannelPublished(youtubeStatus);
  const isTtOk = isChannelPublished(tiktokStatus);
  const isFbOk = isChannelPublished(fbStatus);

  const finalStatus = (isYtOk && isTtOk && isFbOk) ? "Published" : "Error";

  return {
    batchId: batch.id,
    topic: batch.topic,
    finalStatus,
    youtubeStatus,
    tiktokStatus,
    fbStatus,
    results,
    errors,
    isYtOk,
    isTtOk,
    isFbOk,
    fullyPublished: isYtOk && isTtOk && isFbOk
  };
}
