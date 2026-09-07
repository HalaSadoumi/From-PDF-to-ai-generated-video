import { COLORS } from "./theme";

/** Per-scene accent colour.
 *
 * Every scene previously drew in the same cyan, which is a large part of why
 * a chapter felt repetitive even when the diagrams differed. Rotating the
 * accent deterministically by scene id gives consecutive scenes a visibly
 * different palette while keeping the whole course coherent — and, being
 * derived from the id, it stays stable across re-renders.
 */
const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, "#34D399", "#FBBF24"];

export function accentFor(sceneId: string): string {
  let hash = 0;
  for (let i = 0; i < sceneId.length; i++) {
    hash = (hash * 31 + sceneId.charCodeAt(i)) % 9973;
  }
  return PALETTE[hash % PALETTE.length];
}

/** A second, contrasting colour for scenes that need two (comparisons,
 * before/after), guaranteed different from the primary. */
export function secondaryAccentFor(sceneId: string): string {
  const primary = accentFor(sceneId);
  const others = PALETTE.filter((c) => c !== primary);
  let hash = 0;
  for (let i = 0; i < sceneId.length; i++) {
    hash = (hash * 17 + sceneId.charCodeAt(i)) % 7919;
  }
  return others[hash % others.length];
}
