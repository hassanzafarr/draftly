import { mountReplyPanel, unmountReplyPanel } from './replyPanel.js';

const TRIGGER_ATTR = 'data-draftly-trigger';
let hoverTimer = null;

export function initReplyButtons(platform, config) {
  // Event delegation on document body — efficient, handles dynamically added posts
  document.addEventListener('mouseover', (e) => {
    const post = e.target.closest(config.feedPostSelector);
    if (!post || post.querySelector(`[${TRIGGER_ATTR}]`)) return;

    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => injectTriggerButton(post, platform, config), 400);
  });

  document.addEventListener('mouseout', (e) => {
    const post = e.target.closest(config.feedPostSelector);
    if (post) {
      clearTimeout(hoverTimer);
    }
  });
}

function injectTriggerButton(post, platform, config) {
  if (post.querySelector(`[${TRIGGER_ATTR}]`)) return;

  const anchor = post.querySelector(config.replyButtonAnchor);
  if (!anchor) return;

  const btn = document.createElement('button');
  btn.setAttribute(TRIGGER_ATTR, 'true');
  btn.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    background: #7c3aed;
    color: white;
    border: none;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: system-ui, sans-serif;
    margin-left: 8px;
    transition: background 0.15s;
    white-space: nowrap;
    vertical-align: middle;
  `;
  btn.innerHTML = '✦ Draft Reply';

  btn.addEventListener('mouseenter', () => { btn.style.background = '#6d28d9'; });
  btn.addEventListener('mouseleave', () => { btn.style.background = '#7c3aed'; });

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();

    const textEl = post.querySelector(config.postTextSelector);
    const postText = textEl ? (textEl.innerText || textEl.textContent || '') : '';

    mountReplyPanel(postText, platform, btn);
  });

  // Clean up button when post node leaves the DOM
  const cleanupObserver = new MutationObserver(() => {
    if (!document.contains(post)) {
      btn.remove();
      unmountReplyPanel();
      cleanupObserver.disconnect();
    }
  });
  cleanupObserver.observe(document.body, { childList: true, subtree: true });

  anchor.appendChild(btn);
}
