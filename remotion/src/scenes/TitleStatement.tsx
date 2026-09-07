import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { ConceptIcon } from "../components/ConceptIcon";
import { KeyPoints } from "../components/KeyPoints";

/** Definition / key-message beat, and the fallback when no diagram fits: a
 * statement set typographically under the scene's concept icon, with the
 * points that develop it listed underneath. */
export const TitleStatement: React.FC<{
  label?: string;
  primary: string;
  icon: string;
  items?: string[];
  accent?: string;
  durationInFrames: number;
}> = ({ label, primary, icon, items = [], accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - 4, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const float = Math.sin(frame / 24) * 5;
  const text = primary || label || "";
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <div style={{ marginBottom: hasPoints ? 26 : 44, transform: `scale(${hasPoints ? 0.72 : 1})` }}>
        <ConceptIcon icon={icon} />
      </div>
      <div style={{ maxWidth: "82%", textAlign: "center", display: "flex", flexDirection: "column" }}>
        {label && primary && (
          <div
            style={{
              fontFamily: FONT,
              fontSize: 30,
              fontWeight: 800,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: COLORS.accent,
              opacity,
              marginBottom: 22,
            }}
          >
            {label}
          </div>
        )}
        <div
          style={{
            fontFamily: FONT,
            fontSize: hasPoints ? 46 : 58,
            fontWeight: 800,
            lineHeight: 1.28,
            color: COLORS.text,
            opacity,
            transform: `scale(${0.92 + 0.08 * s}) translateY(${float}px)`,
            textShadow: `0 0 44px ${COLORS.accent}44`,
          }}
        >
          {text}
        </div>
        <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} />
      </div>
    </AbsoluteFill>
  );
};
