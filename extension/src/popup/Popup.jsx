import { useState, useEffect } from 'react';
import { getApiKey } from '../lib/storage.js';

export default function Popup() {
  const [hasKey, setHasKey] = useState(null);

  useEffect(() => {
    getApiKey().then(key => setHasKey(!!key));
  }, []);

  async function openSidePanel() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.sidePanel.open({ windowId: tab.windowId });
    window.close();
  }

  function openOptions() {
    chrome.runtime.openOptionsPage();
    window.close();
  }

  return (
    <div style={{ width: 260, padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <div style={{
          width: 28, height: 28, background: '#7c3aed', borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, color: 'white', fontWeight: 700,
        }}>D</div>
        <span style={{ fontWeight: 700, fontSize: 16, color: '#f1f5f9' }}>Draftly</span>
      </div>

      {hasKey === false && (
        <div style={{
          background: '#4c1d95', border: '1px solid #6d28d9', borderRadius: 8,
          padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#c4b5fd',
        }}>
          ⚠ Set your Gemini API key to activate AI features.
        </div>
      )}

      {hasKey === true && (
        <div style={{
          background: '#064e3b', border: '1px solid #065f46', borderRadius: 8,
          padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#6ee7b7',
        }}>
          ✓ API key active
        </div>
      )}

      <button
        onClick={openSidePanel}
        style={{
          width: '100%', padding: '9px 0', background: '#7c3aed', color: 'white',
          border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 13,
          cursor: 'pointer', marginBottom: 8,
        }}
      >
        ✦ Open Draft Panel
      </button>

      <button
        onClick={openOptions}
        style={{
          width: '100%', padding: '9px 0', background: '#1e1b4b', color: '#a78bfa',
          border: '1px solid #4c1d95', borderRadius: 8, fontWeight: 600, fontSize: 13,
          cursor: 'pointer',
        }}
      >
        ⚙ Settings
      </button>

      <div style={{ marginTop: 12, fontSize: 11, color: '#475569', textAlign: 'center' }}>
        Hover posts on LinkedIn or X to draft replies
      </div>
    </div>
  );
}
