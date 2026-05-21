export function buildReplyPrompt({ postText, voiceProfile, platform }) {
  const voiceSection = voiceProfile?.rawSamples
    ? `Here are examples of how I write on social media:\n\n${voiceProfile.rawSamples.slice(0, 3000)}`
    : 'Write in a professional yet personable tone.';

  const platformCtx = platform === 'linkedin'
    ? 'LinkedIn (professional audience, up to 1200 chars per reply)'
    : 'X/Twitter (concise, under 280 characters)';

  return `You are a social media ghostwriter helping me reply to a ${platform} post.

${voiceSection}

## Post I want to reply to:
${postText.slice(0, 1500)}

## Instructions
Generate exactly 3 reply options. Each reply must:
- Match my writing voice from the examples above
- Be appropriate for ${platformCtx}
- Add genuine value: an insight, a question, or a specific affirmation — never generic filler
- NOT start with "Great post!", "Absolutely!", "I totally agree", or similar hollow openers
- Be ready to post with no editing needed

Return ONLY a valid JSON array with exactly 3 strings. No markdown, no explanation.
Example: ["reply one", "reply two", "reply three"]`;
}

export function buildDraftPostPrompt({ topic, platform, tone, voiceProfile }) {
  const charLimit = platform === 'x'
    ? 'Keep it under 280 characters for a single tweet, or structure as a thread (max 5 tweets, each clearly separated by "---", each under 280 chars).'
    : 'LinkedIn allows up to 3000 characters. Aim for 150–400 words for best engagement. Use line breaks for readability.';

  const voiceSection = voiceProfile?.rawSamples
    ? `Here are examples of my writing style:\n\n${voiceProfile.rawSamples.slice(0, 3000)}`
    : '';

  return `You are a social media ghostwriter.
${voiceSection}

Write a ${platform === 'linkedin' ? 'LinkedIn' : 'X/Twitter'} post about the following topic.

Topic: ${topic}
Tone: ${tone}

Rules:
- ${charLimit}
- Match my writing voice from the examples above
- Open with a hook that stops the scroll
- ${platform === 'linkedin' ? 'End with a question or call-to-action to drive comments.' : 'Be punchy. Every word earns its place.'}
- No hashtag spam — maximum 2–3 relevant hashtags only if they add value
- Return ONLY the post text, nothing else. No markdown formatting, no labels.`;
}

export function buildScoringPrompt({ postText, platform }) {
  return `Rate the following ${platform} post on engagement potential for a professional in tech or business.

Post:
${postText.slice(0, 800)}

Score guidelines:
- 80–100: High-value — trending topic, thought-provoking, strong discussion potential
- 50–79: Moderate — relevant but not exceptional
- 0–49: Low — generic, spammy, or off-topic

Return ONLY valid JSON: { "score": <0-100>, "reasons": ["reason1", "reason2"] }`;
}
