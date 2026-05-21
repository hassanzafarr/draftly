import { useState } from 'react';

const X_CHAR_LIMIT = 280;

export default function DraftEditor({ draft, platform, onRegenerate }) {
  const [text, setText] = useState(draft);
  const [copied, setCopied] = useState(false);

  const isThread = text.includes('---');
  const charCount = text.length;
  const overLimit = platform === 'x' && !isThread && charCount > X_CHAR_LIMIT;

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="draft-editor">
      <textarea
        className="draft-textarea"
        value={text}
        onChange={e => setText(e.target.value)}
        rows={10}
        spellCheck
      />

      <div className="draft-footer">
        <span className={`char-count ${overLimit ? 'over-limit' : ''}`}>
          {platform === 'x' && !isThread && `${charCount} / ${X_CHAR_LIMIT}`}
          {platform === 'linkedin' && `${charCount} chars`}
          {isThread && 'Thread format'}
        </span>
        <div className="draft-actions">
          <button className="btn btn-secondary" onClick={onRegenerate}>
            ↻ Regenerate
          </button>
          <button className={`btn ${copied ? 'btn-copied' : 'btn-primary'}`} onClick={handleCopy}>
            {copied ? '✓ Copied!' : 'Copy Post'}
          </button>
        </div>
      </div>
    </div>
  );
}
