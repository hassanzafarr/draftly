import { callGemini } from '../lib/gemini.js';
import { buildReplyPrompt, buildDraftPostPrompt, buildScoringPrompt } from '../lib/prompts.js';
import { getApiKey, getSettings, saveSettings, getVoiceProfile, saveVoiceProfile } from '../lib/storage.js';

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  handleMessage(msg).then(sendResponse).catch(err => sendResponse({ error: err.message }));
  return true; // keep channel open for async response
});

async function handleMessage(msg) {
  switch (msg.type) {
    case 'GENERATE_REPLY': return await generateReply(msg);
    case 'DRAFT_POST':     return await draftPost(msg);
    case 'SCORE_POST':     return await scorePost(msg);
    case 'GET_SETTINGS':   return await getAllSettings();
    case 'SAVE_SETTINGS':  return await persistSettings(msg);
    case 'GET_VOICE':      return await getVoiceProfile();
    case 'SAVE_VOICE':     return await saveVoiceProfile(msg.voiceProfile);
    case 'TEST_API_KEY':   return await testApiKey(msg.apiKey);
    default: throw new Error(`Unknown message type: ${msg.type}`);
  }
}

async function generateReply({ postText, platform }) {
  const [apiKey, voiceProfile] = await Promise.all([getApiKey(), getVoiceProfile()]);
  const prompt = buildReplyPrompt({ postText, voiceProfile, platform });
  const raw = await callGemini(prompt, apiKey);
  const suggestions = JSON.parse(raw);
  if (!Array.isArray(suggestions)) throw new Error('PARSE_ERROR');
  return { suggestions };
}

async function draftPost({ topic, platform, tone }) {
  const [apiKey, voiceProfile] = await Promise.all([getApiKey(), getVoiceProfile()]);
  const prompt = buildDraftPostPrompt({ topic, platform, tone, voiceProfile });
  const raw = await callGemini(prompt, apiKey);
  // draft prompt returns plain text, not JSON
  const draft = typeof raw === 'string' ? raw.replace(/^"|"$/g, '').trim() : raw;
  return { draft };
}

async function scorePost({ postText, platform }) {
  const apiKey = await getApiKey();
  if (!apiKey) {
    // fall back to heuristic if no API key
    return { score: 50, reasons: ['Heuristic score — set API key for AI scoring'] };
  }
  const prompt = buildScoringPrompt({ postText, platform });
  const raw = await callGemini(prompt, apiKey);
  return JSON.parse(raw);
}

async function getAllSettings() {
  const [settings, voiceProfile] = await Promise.all([getSettings(), getVoiceProfile()]);
  return { ...settings, voiceProfile };
}

async function persistSettings({ settings, voiceProfile }) {
  const tasks = [];
  if (settings) tasks.push(saveSettings(settings));
  if (voiceProfile !== undefined) tasks.push(saveVoiceProfile(voiceProfile));
  await Promise.all(tasks);
  return { ok: true };
}

async function testApiKey(apiKey) {
  try {
    await callGemini('Return the JSON: {"ok": true}', apiKey);
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}
