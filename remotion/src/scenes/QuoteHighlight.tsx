import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { KeyPoints } from "../components/KeyPoints";

/** An editorial pull-quote: a large statement between quote marks with a
 * colour rule beside it. Deliberately typographic and full-bleed, so a run of
 * diagram scenes gets a change of rhythm rather than another boxed schema. */
export const QuoteHighlight: React.FC<{
  primary: string;
  secondary: string;
  items?: string[];
  accent: string;
  durationInFrames: number;
}> = ({ primary, secondary, items = [], accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - 3, fps, config: { damping: 13 } });
  const opacity = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  const ruleHeight = interpolate(frame, [6, 30], [0, 1], { extrapolateRight: "clamp" });
  const drift = Math.sin(frame / 30) * 4;
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 12%" }}>
      <div style={{ display: "flex", gap: 44, alignItems: "center", maxWidth: 1400 }}>
        <div
          style={{
            width: 9,
            alignSelf: "stretch",
            borderRadius: 5,
            background: accent,
            transform: `scaleY(${ruleHeight})`,
            transformOrigin: "top",
            boxShadow: `0 0 26px ${accent}88`,
            flexShrink: 0,
          }}
        />
        <div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 96,
              lineHeight: 0.55,
              color: accent,
              opacity: opacity * 0.85,
              marginBottom: 22,
            }}
          >
            “
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: hasPoints ? 44 : 52,
              fontWeight: 700,
              lineHeight: 1.35,
              color: COLORS.text,
              opacity,
              transform: `translateY(${drift}px) scale(${0.96 + 0.04 * s})`,
            }}
          >
            {primary}
          </div>
          {secondary && (
            <div
              style={{
                fontFamily: FONT,
                fontSize: 26,
                fontWeight: 600,
                letterSpacing: 1.6,
                textTransform: "uppercase",
                color: accent,
                opacity,
                marginTop: 26,
              }}
            >
              {secondary}
            </div>
          )}
          <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
