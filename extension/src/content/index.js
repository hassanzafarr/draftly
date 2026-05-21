import { getCurrentPlatform, PLATFORM_CONFIG } from './platform.js';
import { initFeedScanner, teardownFeedScanner } from './feedScanner.js';
import { initReplyButtons } from './replyButton.js';

const platform = getCurrentPlatform();

if (platform) {
  const config = PLATFORM_CONFIG[platform];

  // Fetch settings from SW before initializing features
  chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }).then(settings => {
    if (!settings || settings.error) return;

    if (settings.feedScannerEnabled) {
      initFeedScanner(platform, config, settings.feedScannerThreshold);
    }

    if (settings.replyEnabled) {
      initReplyButtons(platform, config);
    }
  }).catch(() => {
    // Extension context may not be ready yet on fresh installs — fail silently
  });

  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    teardownFeedScanner();
  });
}
