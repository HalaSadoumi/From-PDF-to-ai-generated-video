import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";

/** The supporting points of a scene, revealed one at a time.
 *
 * Half the scenes used to show a title and nothing else, so a viewer watching
 * without sound learned almost nothing. Every archetype now renders the plan's
 * `items` through this component: the points are staggered across the scene so
 * each one lands roughly while it is being said, rather than all appearing at
 * the first frame.
 *
 * `panel` places them as a right-hand column beside a centred diagram;
 * `inline` stacks them under a typographic statement. */
export const KeyPoints: React.FC<{
  items: string[];
  accent: string;
  durationInFrames: number;
  variant?: "panel" | "inline";
}> = ({ items, accent, durationInFrames, variant = "inline" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shown = items.filter((t) => t && t.trim()).slice(0, 4);
  if (shown.length === 0) return null;

  // Spread the entrances over the first 70% of the scene, leaving the last
  // stretch for the takeaway line to come in underneath.
  const span = (durationInFrames * 0.7) / shown.length;
  const isPanel = variant === "panel";

  const rows = shown.map((text, i) => {
    const start = 8 + i * span;
    const s = spring({ frame: frame - start, fps, config: { damping: 13, mass: 0.6 } });
    const opacity = interpolate(frame, [start, start + 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <div
        key={i}
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: isPanel ? 16 : 20,
          opacity,
          transform: `translateX(${(1 - s) * (isPanel ? 46 : 0)}px) translateY(${(1 - s) * (isPanel ? 0 : 18)}px)`,
        }}
      >
        <div
          style={{
            width: isPanel ? 10 : 12,
            height: isPanel ? 10 : 12,
            borderRadius: 6,
            background: accent,
            boxShadow: `0 0 16px ${accent}AA`,
            flexShrink: 0,
            marginTop: isPanel ? 14 : 16,
            transform: `scale(${s})`,
          }}
        />
        <div
          style={{
            fontFamily: FONT,
            fontSize: isPanel ? 30 : 34,
            fontWeight: 600,
            lineHeight: 1.32,
            color: COLORS.text,
            textAlign: "left",
          }}
        >
          {text}
        </div>
      </div>
    );
  });

  if (isPanel) {
    return (
      <div
        style={{
          position: "absolute",
          right: 84,
          top: "50%",
          transform: "translateY(-50%)",
          width: 560,
          display: "flex",
          flexDirection: "column",
          gap: 26,
          borderLeft: `3px solid ${accent}55`,
          paddingLeft: 30,
        }}
      >
        {rows}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        marginTop: 44,
        maxWidth: 1180,
        alignSelf: "center",
      }}
    >
      {rows}
    </div>
  );
};
