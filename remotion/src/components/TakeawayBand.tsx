import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";

/** Lower third stating what the scene is teaching.
 *
 * The diagrams name the elements of a point; this states the point itself, in
 * one sentence, so the screen explains the content rather than only labelling
 * it. Rendered by SceneRenderer for every archetype, on a scrim so it reads
 * over any diagram or backdrop, and brought in late in the scene once the
 * supporting points have landed. */
/** Vertical room the band occupies, so the scene above can be inset by it
 * instead of being drawn underneath. Estimated from the text length rather
 * than measured, to keep the render deterministic. */
export function takeawayHeight(text: string): number {
  if (!text || !text.trim()) return 0;
  const lines = Math.max(1, Math.ceil(text.length / 70));
  return 112 + lines * 48;
}

export const TakeawayBand: React.FC<{
  text: string;
  accent: string;
  durationInFrames: number;
}> = ({ text, accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!text || !text.trim()) return null;

  // Short scenes have no room to wait: come in at 45% there, later on long
  // ones so the diagram plays out first.
  const startAt = durationInFrames * (durationInFrames < 150 ? 0.45 : 0.6);
  const s = spring({ frame: frame - startAt, fps, config: { damping: 14, mass: 0.8 } });
  const opacity = interpolate(frame, [startAt, startAt + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        paddingBottom: 40,
        paddingTop: 56,
        background:
          "linear-gradient(to top, rgba(10,14,26,0.94) 0%, rgba(10,14,26,0.80) 45%, rgba(10,14,26,0) 100%)",
        opacity,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 26,
          margin: "0 auto",
          maxWidth: 1520,
          transform: `translateY(${(1 - s) * 26}px)`,
        }}
      >
        <div
          style={{
            width: 7,
            alignSelf: "stretch",
            minHeight: 54,
            borderRadius: 4,
            background: accent,
            boxShadow: `0 0 22px ${accent}99`,
            flexShrink: 0,
          }}
        />
        <div
          style={{
            fontFamily: FONT,
            fontSize: 34,
            fontWeight: 600,
            lineHeight: 1.34,
            color: COLORS.text,
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};
