import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONT } from "../theme";
import { chunkWords, getChunkAt } from "../narrationChunks";

function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[.,!?;:()«»"']/g, "");
}

/** Supporting subtitle band: shows the real narration a line at a time.
 *
 * Words that also appear in this scene's own label/items are accented, so the
 * spoken words tie visually to what the diagram is showing. Highlighting is
 * therefore derived from the generated plan, not from a hardcoded keyword
 * list — nothing here is specific to any subject matter. */
export const CaptionOverlay: React.FC<{
  narration: string;
  durationInFrames: number;
  highlight?: string[];
}> = ({ narration, durationInFrames, highlight = [] }) => {
  const frame = useCurrentFrame();
  const chunks = chunkWords(narration, 52);
  const { index, localFrame, chunkDuration } = getChunkAt(frame, durationInFrames, chunks.length);
  const words = chunks[index].split(" ");

  // Words worth accenting: those appearing in the scene's own labels, kept to
  // reasonably long tokens so articles and prepositions don't light up.
  const keywords = new Set(
    highlight
      .flatMap((h) => h.split(/\s+/))
      .map(normalize)
      .filter((w) => w.length > 4)
  );

  const opacity = interpolate(
    localFrame,
    [0, 6, Math.max(6, chunkDuration - 6), chunkDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const rise = interpolate(localFrame, [0, 8], [16, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 64 }}>
      <div
        style={{
          maxWidth: "80%",
          background: "rgba(8,12,22,0.78)",
          borderRadius: 16,
          padding: "18px 36px",
          opacity,
          transform: `translateY(${rise}px)`,
          border: `1px solid ${COLORS.cardBorder}`,
        }}
      >
        <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 600, lineHeight: 1.35, textAlign: "center" }}>
          {words.map((w, i) => (
            <span
              key={i}
              style={{ color: keywords.has(normalize(w)) ? COLORS.accent : COLORS.text, marginRight: 9 }}
            >
              {w}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
