import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** Best-practice items sliding in and getting ticked one by one, with the
 * checkmark stroke drawing itself. */
export const ChecklistScene: React.FC<{ label?: string; items: string[]; durationInFrames: number }> = ({
  label,
  items,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const rows = items.slice(0, 4);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const rowH = 128;
  const startY = -((rows.length - 1) * rowH) / 2;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 90)">
          {rows.map((item, i) => {
            const appear = spring({ frame: frame - (10 + i * 16), fps, config: { damping: 13 } });
            const tick = spring({ frame: frame - (24 + i * 16), fps, config: { damping: 14 } });
            const y = startY + i * rowH;
            return (
              <g key={i} opacity={appear} transform={`translate(${(1 - appear) * -90} ${y})`}>
                <rect x={-520} y={-46} width={1040} height={92} rx={18} fill="rgba(255,255,255,0.06)" stroke={COLORS.cardBorder} strokeWidth={2} />
                <g transform="translate(-452 0)">
                  <rect x={-30} y={-30} width={60} height={60} rx={12} fill={tick > 0.3 ? `${COLORS.accent}33` : "transparent"} stroke={COLORS.accent} strokeWidth={4} />
                  <path
                    d="M -14 2 L -3 14 L 16 -12"
                    stroke={COLORS.accent}
                    strokeWidth={7}
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray={54}
                    strokeDashoffset={54 * (1 - tick)}
                  />
                </g>
                <WrappedText
                  text={item}
                  x={-386}
                  y={12}
                  maxWidth={880}
                  fontSize={34}
                  fontWeight={700}
                  anchor="start"
                  maxLines={2}
                />
              </g>
            );
          })}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
