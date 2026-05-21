import { useState } from 'react';
import { useGemini } from '../hooks/useGemini.js';
import DraftEditor from '../components/DraftEditor.jsx';

const TONES = ['professional', 'casual', 'witty', 'thoughtful'];

export default function SidePanel() {
  const [platform, setPlatform] = useState('linkedin');
  const [tone, setTone] = useState('professional');
  const [topic, setTopic] = useState('');
  const { generate, loading, error, result } = useGemini('DRAFT_POST');

  async function handleGenerate() {
    if (!topic.trim()) return;
    await generate({ topic, platform, tone });
  }

  return (
    <div className="min-h-screen p-4 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 mb-5">
        <div className="w-7 h-7 bg-violet-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">D</div>
        <span className="font-bold text-slate-100">Draft a Post</span>
      </div>

      {/* Platform */}
      <div className="mb-4">
        <div className="section-title">Platform</div>
        <div className="flex gap-2">
          {['linkedin', 'x'].map(p => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${
                platform === p
                  ? 'bg-violet-600 text-white'
                  : 'bg-indigo-950 text-slate-400 border border-indigo-800 hover:border-violet-600'
              }`}
            >
              {p === 'linkedin' ? 'LinkedIn' : 'X / Twitter'}
            </button>
          ))}
        </div>
      </div>

      {/* Tone */}
      <div className="mb-4">
        <div className="section-title">Tone</div>
        <div className="grid grid-cols-2 gap-2">
          {TONES.map(t => (
            <button
              key={t}
              onClick={() => setTone(t)}
              className={`py-2 rounded-lg text-sm font-semibold capitalize transition-colors ${
                tone === t
                  ? 'bg-violet-600 text-white'
                  : 'bg-indigo-950 text-slate-400 border border-indigo-800 hover:border-violet-600'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Topic */}
      <div className="mb-4">
        <label className="label">What do you want to post about?</label>
        <textarea
          className="input-field"
          rows={3}
          placeholder={
            platform === 'linkedin'
              ? 'e.g. A lesson I learned from failing my first startup...'
              : 'e.g. Why most dev interviews are broken'
          }
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
        />
        <p className="text-xs text-slate-500 mt-1">Cmd/Ctrl+Enter to generate</p>
      </div>

      <button
        className="btn-primary w-full py-3 mb-5"
        onClick={handleGenerate}
        disabled={loading || !topic.trim()}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block w-4 h-4 border-2 border-violet-300 border-t-white rounded-full animate-spin" />
            Drafting in your voice…
          </span>
        ) : '✦ Generate Post'}
      </button>

      {error === 'NO_API_KEY' && (
        <div className="card text-center">
          <p className="text-sm text-slate-400 mb-2">No API key set.</p>
          <button
            className="text-violet-400 text-sm hover:underline"
            onClick={() => chrome.runtime.openOptionsPage()}
          >
            Open Settings →
          </button>
        </div>
      )}

      {error && error !== 'NO_API_KEY' && (
        <div className="card border-red-900">
          <p className="text-sm text-red-400">
            {error === 'RATE_LIMIT'
              ? 'Rate limit hit — wait a moment and retry.'
              : 'Generation failed. Check your API key in settings.'}
          </p>
        </div>
      )}

      {result?.draft && !loading && (
        <DraftEditor
          draft={result.draft}
          platform={platform}
          onRegenerate={handleGenerate}
        />
      )}
    </div>
  );
}
