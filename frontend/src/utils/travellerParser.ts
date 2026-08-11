/**
 * Interprets a natural-language answer for number of travellers into an integer.
 * Returns null if the text cannot be interpreted.
 */
export function interpretTravellers(input: string): number | null {
  if (!input || !input.trim()) return null;
  const text = input.trim().toLowerCase();

  // 1. Direct integer string check (e.g. "3", " 4 ")
  if (/^\d+$/.test(text)) {
    const val = parseInt(text, 10);
    return val > 0 && val <= 100 ? val : null;
  }

  // 2. Key phrases
  if (text.includes("solo") || text.includes("just me") || text.includes("myself") || text === "me") {
    return 1;
  }
  if (
    text.includes("couple") ||
    text.includes("me and a friend") ||
    text.includes("me and my partner") ||
    text.includes("me and my wife") ||
    text.includes("me and my husband") ||
    text.includes("two of us") ||
    text.includes("2 of us")
  ) {
    return 2;
  }
  if (
    text.includes("me and two friends") ||
    text.includes("me and 2 friends") ||
    text.includes("three of us") ||
    text.includes("3 of us") ||
    text.includes("family of 3") ||
    text.includes("family of three")
  ) {
    return 3;
  }
  if (
    text.includes("me and three friends") ||
    text.includes("me and 3 friends") ||
    text.includes("four of us") ||
    text.includes("4 of us") ||
    text.includes("family of 4") ||
    text.includes("family of four")
  ) {
    return 4;
  }

  // 3. Word numbers mapping
  const wordNumbers: Record<string, number> = {
    one: 1,
    two: 2,
    three: 3,
    four: 4,
    five: 5,
    six: 6,
    seven: 7,
    eight: 8,
    nine: 9,
    ten: 10,
  };

  for (const [word, num] of Object.entries(wordNumbers)) {
    if (new RegExp(`\\b${word}\\b`).test(text)) {
      return num;
    }
  }

  // 4. Extract digits inside text (e.g., "about 5 people")
  const digitMatch = text.match(/\b(\d+)\b/);
  if (digitMatch) {
    const val = parseInt(digitMatch[1], 10);
    if (val > 0 && val <= 100) return val;
  }

  return null;
}
