import { createRoot } from 'react-dom/client';
import { createElement } from 'react';
import ReplyPanel from '../components/ReplyPanel.jsx';

const HOST_ID = 'draftly-reply-host';

let currentRoot = null;
let currentHost = null;
let outsideClickHandler = null;

export function mountReplyPanel(postText, platform, anchorNode) {
  unmountReplyPanel();

  const host = document.createElement('div');
  host.id = HOST_ID;
  host.style.cssText = `
    position: fixed;
    z-index: 2147483647;
    top: 0;
    left: 0;
    width: 0;
    height: 0;
    overflow: visible;
  `;

  const shadow = host.attachShadow({ mode: 'open' });

  // Inject Tailwind CSS into shadow DOM via a link to the web-accessible resource
  const style = document.createElement('style');
  style.textContent = getShadowStyles();
  shadow.appendChild(style);

  const mountPoint = document.createElement('div');
  mountPoint.id = 'draftly-panel-root';
  shadow.appendChild(mountPoint);

  document.body.appendChild(host);
  currentHost = host;

  // Position panel near the anchor
  const rect = anchorNode.getBoundingClientRect();
  mountPoint.style.cssText = `
    position: fixed;
    top: ${Math.min(rect.bottom + 8, window.innerHeight - 380)}px;
    left: ${Math.max(rect.left, 8)}px;
    width: 380px;
    z-index: 2147483647;
  `;

  currentRoot = createRoot(mountPoint);
  currentRoot.render(
    createElement(ReplyPanel, {
      postText,
      platform,
      onClose: unmountReplyPanel,
    })
  );

  // Close on outside click
  outsideClickHandler = (e) => {
    if (!host.contains(e.target) && e.target !== anchorNode) {
      unmountReplyPanel();
    }
  };
  setTimeout(() => document.addEventListener('click', outsideClickHandler), 100);
}

export function unmountReplyPanel() {
  if (outsideClickHandler) {
    document.removeEventListener('click', outsideClickHandler);
    outsideClickHandler = null;
  }
  if (currentRoot) {
    currentRoot.unmount();
    currentRoot = null;
  }
  if (currentHost) {
    currentHost.remove();
    currentHost = null;
  }
}

function getShadowStyles() {
  // Minimal reset + utility classes used by the panel
  // Full Tailwind reset is intentionally excluded to avoid page style conflicts
  return `
    *, *::before, *::after { box-sizing: border-box; }
    :host { all: initial; }
    #draftly-panel-root {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: #f1f5f9;
    }
    .panel {
      background: #1e1b4b;
      border: 1px solid #4c1d95;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      width: 380px;
    }
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    .panel-title {
      font-size: 13px;
      font-weight: 600;
      color: #a78bfa;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .close-btn {
      background: none;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      font-size: 18px;
      padding: 0 4px;
      line-height: 1;
    }
    .close-btn:hover { color: #f1f5f9; }
    .loading {
      text-align: center;
      color: #94a3b8;
      padding: 24px 0;
      font-size: 13px;
    }
    .error {
      color: #f87171;
      font-size: 13px;
      padding: 12px 0;
    }
    .reply-card {
      background: #2e1065;
      border: 1px solid #6d28d9;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 8px;
    }
    .reply-text {
      font-size: 13px;
      color: #e2e8f0;
      margin-bottom: 8px;
      line-height: 1.5;
    }
    .reply-actions {
      display: flex;
      gap: 8px;
    }
    .btn {
      flex: 1;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: opacity 0.15s;
    }
    .btn:hover { opacity: 0.85; }
    .btn-copy {
      background: #3730a3;
      color: #c4b5fd;
    }
    .btn-insert {
      background: #7c3aed;
      color: white;
    }
    .btn-copied {
      background: #065f46;
      color: #6ee7b7;
    }
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid #4c1d95;
      border-top-color: #8b5cf6;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      margin-right: 8px;
      vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .no-key-msg {
      font-size: 12px;
      color: #94a3b8;
      text-align: center;
      padding: 8px 0;
    }
    .no-key-msg a {
      color: #a78bfa;
      cursor: pointer;
    }
  `;
}
