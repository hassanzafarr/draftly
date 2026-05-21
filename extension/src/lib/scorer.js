const HIGH_VALUE_KEYWORDS = [
  'ai', 'artificial intelligence', 'machine learning', 'startup', 'funding',
  'raise', 'launch', 'breaking', 'announcing', 'lessons learned', 'mistake',
  'unpopular opinion', 'hot take', 'thread', 'hiring', 'layoff', 'acquisition',
  'ipo', 'product', 'growth', 'revenue', 'profitable', 'failed', 'fired',
];

const SPAM_KEYWORDS = [
  'click here', 'free gift', 'dm me', 'buy now', 'limited time', 'guaranteed',
  'make money', 'passive income',
];

export function scorePost(postText, engagementMeta = {}) {
  if (!postText || postText.length < 20) return 0;

  const lower = postText.toLowerCase();
  let score = 30; // baseline

  // keyword signals
  const highValueHits = HIGH_VALUE_KEYWORDS.filter(k => lower.includes(k)).length;
  const spamHits = SPAM_KEYWORDS.filter(k => lower.includes(k)).length;
  score += Math.min(highValueHits * 8, 32);
  score -= spamHits * 15;

  // length signal — very short or very long posts tend to underperform
  if (postText.length > 100 && postText.length < 1500) score += 10;

  // engagement counts (if extractable from DOM)
  const { likes = 0, comments = 0, reposts = 0 } = engagementMeta;
  if (likes > 50) score += 10;
  if (likes > 200) score += 10;
  if (comments > 10) score += 8;
  if (reposts > 20) score += 8;

  // question mark = discussion potential
  if (postText.includes('?')) score += 5;

  return Math.max(0, Math.min(100, score));
}
