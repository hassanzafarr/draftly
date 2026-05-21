import { scorePost } from '../lib/scorer.js';

const HIGHLIGHT_ATTR = 'data-draftly-scanned';
const BADGE_ATTR = 'data-draftly-badge';

let scannerObserver = null;
let processingQueue = new Set();
let debounceTimer = null;

export function initFeedScanner(platform, config, threshold = 60) {
  if (scannerObserver) return;

  scannerObserver = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => processQueue(platform, config, threshold), 300);
  });

  scannerObserver.observe(document.body, { childList: true, subtree: true });

  // Initial scan of already-loaded posts
  setTimeout(() => processQueue(platform, config, threshold), 800);
}

export function teardownFeedScanner() {
  if (scannerObserver) {
    scannerObserver.disconnect();
    scannerObserver = null;
  }
  clearTimeout(debounceTimer);
}

function processQueue(platform, config, threshold) {
  const posts = document.querySelectorAll(config.feedPostSelector);

  posts.forEach(post => {
    if (post.hasAttribute(HIGHLIGHT_ATTR) || processingQueue.has(post)) return;
    processingQueue.add(post);
    post.setAttribute(HIGHLIGHT_ATTR, 'true');

    const textEl = post.querySelector(config.postTextSelector);
    if (!textEl) { processingQueue.delete(post); return; }

    const postText = textEl.innerText || textEl.textContent || '';
    const engagementMeta = extractEngagement(post, platform);
    const score = scorePost(postText, engagementMeta);

    if (score >= threshold) {
      applyHighlight(post, score);
    }

    processingQueue.delete(post);
  });
}

function extractEngagement(post, platform) {
  const meta = { likes: 0, comments: 0, reposts: 0 };
  try {
    const text = post.innerText || '';
    const nums = text.match(/[\d,]+/g)?.map(n => parseInt(n.replace(/,/g, ''), 10)) || [];
    if (nums.length >= 1) meta.likes = nums[0];
    if (nums.length >= 2) meta.comments = nums[1];
  } catch (_) {}
  return meta;
}

function applyHighlight(postNode, score) {
  if (postNode.querySelector(`[${BADGE_ATTR}]`)) return;

  // Inject a subtle left-border highlight via a wrapper div
  postNode.style.borderLeft = '3px solid #8b5cf6';
  postNode.style.paddingLeft = '4px';

  const badge = document.createElement('div');
  badge.setAttribute(BADGE_ATTR, 'true');
  badge.style.cssText = `
    position: absolute;
    top: 8px;
    right: 8px;
    background: #8b5cf6;
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 12px;
    z-index: 9999;
    pointer-events: none;
    font-family: system-ui, sans-serif;
    letter-spacing: 0.02em;
  `;
  badge.textContent = `★ ${score}`;

  // Ensure the post node has relative positioning for absolute badge placement
  const existingPosition = window.getComputedStyle(postNode).position;
  if (existingPosition === 'static') {
    postNode.style.position = 'relative';
  }

  postNode.appendChild(badge);
}
