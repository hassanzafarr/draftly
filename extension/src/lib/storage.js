export const getVoiceProfile = () =>
  chrome.storage.local.get('voiceProfile').then(r => r.voiceProfile ?? null);

export const saveVoiceProfile = (data) =>
  chrome.storage.local.set({ voiceProfile: data });

export const getApiKey = () =>
  chrome.storage.sync.get('geminiApiKey').then(r => r.geminiApiKey ?? '');

export const saveApiKey = (key) =>
  chrome.storage.sync.set({ geminiApiKey: key });

export const getSettings = () =>
  chrome.storage.sync.get([
    'geminiApiKey',
    'feedScannerEnabled',
    'feedScannerThreshold',
    'replyEnabled',
    'defaultTone',
  ]).then(r => ({
    geminiApiKey: r.geminiApiKey ?? '',
    feedScannerEnabled: r.feedScannerEnabled ?? true,
    feedScannerThreshold: r.feedScannerThreshold ?? 60,
    replyEnabled: r.replyEnabled ?? true,
    defaultTone: r.defaultTone ?? 'professional',
  }));

export const saveSettings = (settings) =>
  chrome.storage.sync.set(settings);
