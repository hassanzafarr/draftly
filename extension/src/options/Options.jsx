import { useState, useEffect } from 'react';
import { getApiKey, saveApiKey, getVoiceProfile, saveVoiceProfile, getSettings, saveSettings } from '../lib/storage.js';

export default function Options() {
  const [apiKey, setApiKey] = useState('');
  const [voiceSamples, setVoiceSamples] = useState('');
  const [feedEnabled, setFeedEnabled] = useState(true);
  const [replyEnabled, setReplyEnabled] = useState(true);
  const [threshold, setThreshold] = useState(60);
  const [defaultTone, setDefaultTone] = useState('professional');

  const [testStatus, setTestStatus] = useState('idle'); // idle | testing | ok | error
  const [saveStatus, setSaveStatus] = useState('idle'); // idle | saving | saved

  useEffect(() => {
    Promise.all([getApiKey(), getVoiceProfile(), getSettings()]).then(([key, voice, settings]) => {
      setApiKey(key || '');
      setVoiceSamples(voice?.rawSamples || '');
      setFeedEnabled(settings.feedScannerEnabled);
      setReplyEnabled(settings.replyEnabled);
      setThreshold(settings.feedScannerThreshold);
      setDefaultTone(settings.defaultTone);
    });
  }, []);

  async function testConnection() {
    setTestStatus('testing');
    const result = await chrome.runtime.sendMessage({ type: 'TEST_API_KEY', apiKey });
    setTestStatus(result.ok ? 'ok' : 'error');
    setTimeout(() => setTestStatus('idle'), 3000);
  }

  async function handleSave() {
    setSaveStatus('saving');
    await Promise.all([
      saveApiKey(apiKey),
      saveVoiceProfile({ rawSamples: voiceSamples, updatedAt: Date.now() }),
      saveSettings({ feedScannerEnabled: feedEnabled, replyEnabled, feedScannerThreshold: threshold, defaultTone }),
    ]);
    setSaveStatus('saved');
    setTimeout(() => setSaveStatus('idle'), 2000);
  }

  const sampleBytes = new TextEncoder().encode(voiceSamples).length;
  const sampleKB = (sampleBytes / 1024).toFixed(1);

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-9 h-9 bg-violet-600 rounded-xl flex items-center justify-center text-white font-bold text-lg">D</div>
        <div>
          <h1 className="text-xl font-bold text-slate-100">Draftly Settings</h1>
          <p className="text-xs text-slate-400">AI for LinkedIn &amp; X</p>
        </div>
      </div>

      {/* API Key */}
      <div className="card mb-5">
        <div className="section-title">Gemini API Key</div>
        <div className="flex gap-2">
          <input
            type="password"
            className="input-field"
            placeholder="AIza..."
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
          />
          <button
            className="btn-secondary whitespace-nowrap px-4 py-2 rounded-lg text-sm font-semibold"
            onClick={testConnection}
            disabled={!apiKey || testStatus === 'testing'}
          >
            {testStatus === 'testing' ? '…' : testStatus === 'ok' ? '✓ OK' : testStatus === 'error' ? '✕ Failed' : 'Test'}
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Get a free key at{' '}
          <a className="text-violet-400 hover:underline" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
            aistudio.google.com
          </a>
        </p>
      </div>

      {/* Voice Profile */}
      <div className="card mb-5">
        <div className="section-title">Voice Profile</div>
        <label className="label">Paste 3–10 of your recent LinkedIn or X posts</label>
        <textarea
          className="input-field"
          rows={8}
          placeholder="Paste your past posts and comments here. The AI will learn your tone, vocabulary, and style from these examples..."
          value={voiceSamples}
          onChange={e => setVoiceSamples(e.target.value)}
        />
        <p className={`text-xs mt-1 ${sampleBytes > 40000 ? 'text-amber-400' : 'text-slate-500'}`}>
          {sampleKB} KB used {sampleBytes > 40000 && '— consider trimming to keep quality high'}
        </p>
      </div>

      {/* Feature Toggles */}
      <div className="card mb-5">
        <div className="section-title">Features</div>
        <div className="space-y-4">
          <label className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-200 font-medium">Feed Scanner</div>
              <div className="text-xs text-slate-500">Highlight high-value posts in your feed</div>
            </div>
            <input
              type="checkbox"
              className="w-4 h-4 accent-violet-500"
              checked={feedEnabled}
              onChange={e => setFeedEnabled(e.target.checked)}
            />
          </label>

          {feedEnabled && (
            <div>
              <label className="label">Score threshold: {threshold}</label>
              <input
                type="range" min="30" max="90" step="5"
                className="w-full accent-violet-500"
                value={threshold}
                onChange={e => setThreshold(Number(e.target.value))}
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>Show more</span><span>Show less</span>
              </div>
            </div>
          )}

          <label className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-200 font-medium">Reply Suggestions</div>
              <div className="text-xs text-slate-500">Show "Draft Reply" button on posts</div>
            </div>
            <input
              type="checkbox"
              className="w-4 h-4 accent-violet-500"
              checked={replyEnabled}
              onChange={e => setReplyEnabled(e.target.checked)}
            />
          </label>

          <div>
            <label className="label">Default tone</label>
            <select
              className="input-field"
              value={defaultTone}
              onChange={e => setDefaultTone(e.target.value)}
            >
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="witty">Witty</option>
              <option value="thoughtful">Thoughtful</option>
            </select>
          </div>
        </div>
      </div>

      <button
        className="btn-primary w-full py-3 text-base"
        onClick={handleSave}
        disabled={saveStatus === 'saving'}
      >
        {saveStatus === 'saving' ? 'Saving…' : saveStatus === 'saved' ? '✓ Saved!' : 'Save Settings'}
      </button>
    </div>
  );
}
