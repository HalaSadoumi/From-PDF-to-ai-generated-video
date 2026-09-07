/** Narration chunking, at two granularities:
 *  - word groups (2-3 words): drives the big punchy captions, Opus/InVideo
 *    style - changes rapidly, in sync with speech pacing.
 *  - phrase chunks (~58 chars): drives the concept icon, which should
 *    change per idea/concept, not per word (would be too flickery).
 */

export function splitWordGroups(text: string, groupSize = 3): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const groups: string[] = [];
  for (let i = 0; i < words.length; i += groupSize) {
    groups.push(words.slice(i, i + groupSize).join(" "));
  }
  return groups.length ? groups : [""];
}

export function chunkWords(text: string, maxCharsPerChunk = 58): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const chunks: string[] = [];
  let current: string[] = [];
  let len = 0;
  for (const w of words) {
    if (len + w.length + 1 > maxCharsPerChunk && current.length) {
      chunks.push(current.join(" "));
      current = [];
      len = 0;
    }
    current.push(w);
    len += w.length + 1;
  }
  if (current.length) chunks.push(current.join(" "));
  return chunks.length ? chunks : [""];
}

export function getChunkAt(
  frame: number,
  durationInFrames: number,
  chunkCount: number
): { index: number; localFrame: number; chunkDuration: number } {
  const chunkDuration = durationInFrames / chunkCount;
  const index = Math.min(chunkCount - 1, Math.floor(frame / chunkDuration));
  const localFrame = frame - index * chunkDuration;
  return { index, localFrame, chunkDuration };
}
