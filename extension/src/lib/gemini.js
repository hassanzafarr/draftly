const GEMINI_URL =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

export async function callGemini(prompt, apiKey) {
  if (!apiKey) throw new Error('NO_API_KEY');

  const response = await fetch(`${GEMINI_URL}?key=${apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.8,
        maxOutputTokens: 1024,
        responseMimeType: 'application/json',
      },
    }),
  });

  if (response.status === 400) throw new Error('INVALID_API_KEY');
  if (response.status === 429) throw new Error('RATE_LIMIT');
  if (!response.ok) throw new Error(`GEMINI_ERROR_${response.status}`);

  const data = await response.json();
  return data.candidates[0].content.parts[0].text;
}
