import { useState } from 'react';
import { PLATFORM_CONFIG } from '../content/platform.js';

export default function ReplyCard({ text, platform }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleInsert() {
    const config = PLATFORM_CONFIG[platform];
    const box = document.querySelector(config.composeBoxSelector);
    if (!box) {
      handleCopy();
      return;
    }
    box.focus();
    document.execCommand('selectAll');
    document.execCommand('insertText', false, text);
    // Trigger synthetic input event for React-controlled inputs (LinkedIn/X)
    box.dispatchEvent(new InputEvent('input', { bubbles: true, data: text }));
  }

  return (
    <div className="reply-card">
      <div className="reply-text">{text}</div>
      <div className="reply-actions">
        <button
          className={`btn ${copied ? 'btn-copied' : 'btn-copy'}`}
          onClick={handleCopy}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
        <button className="btn btn-insert" onClick={handleInsert}>
          Insert
        </button>
      </div>
    </div>
  );
}
