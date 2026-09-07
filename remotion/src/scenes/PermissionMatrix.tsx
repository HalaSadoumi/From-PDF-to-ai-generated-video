import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { AnimatedArrow, Figure, SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3];

/** Least-privilege: a user on the left, resources on the right, and only the
 * authorised link lights up green while the others are barred — each row
 * resolving in turn. */
export const PermissionMatrix: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  secondary: string;
  durationInFrames: number;
}> = ({ label, items, primary, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const rows = items.slice(0, 3);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const userIn = spring({ frame, fps, config: { damping: 13 } });

  const rowH = 190;
  const startY = -((rows.length - 1) * rowH) / 2;
  // Only the first resource is granted; the rest are denied (least privilege).
  const grantedIndex = 0;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 90)">
          <g opacity={userIn} transform={`translate(${(1 - userIn) * -70} 0)`}>
            <Figure x={-620} y={20} scale={1.4} variant="neutral" label={primary || "Profil"} />
          </g>

          {rows.map((item, i) => {
            const y = startY + i * rowH;
            const appear = spring({ frame: frame - (14 + i * 14), fps, config: { damping: 13 } });
            const decide = interpolate(p, [0.42 + i * 0.11, 0.58 + i * 0.11], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const granted = i === grantedIndex;
            const color = granted ? COLORS.accent : COLORS.accent3;
            return (
              <g key={i}>
                <AnimatedArrow
                  from={[-470, 10]}
                  to={[170, y]}
                  progress={decide}
                  color={granted ? COLORS.accent : "rgba(244,114,182,0.55)"}
                  curve={-(y * 0.16)}
                  width={granted ? 6 : 4}
                  dashed={!granted}
                />
                <g opacity={appear} transform={`translate(400 ${y}) scale(${appear})`}>
                  <rect x={-210} y={-58} width={420} height={116} rx={16} fill={`${color}1F`} stroke={color} strokeWidth={4} />
                  <WrappedText
                    text={item}
                    x={-160}
                    y={12}
                    maxWidth={268}
                    fontSize={30}
                    fontWeight={700}
                    anchor="start"
                    maxLines={2}
                  />
                  <g transform="translate(158 0)" opacity={decide}>
                    <circle r={30} fill={color} />
                    {granted ? (
                      <path d="M -13 2 L -3 13 L 14 -10" stroke="#0A0E1A" strokeWidth={6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    ) : (
                      <path d="M -11 -11 L 11 11 M 11 -11 L -11 11" stroke="#0A0E1A" strokeWidth={6} strokeLinecap="round" />
                    )}
                  </g>
                </g>
              </g>
            );
          })}

          {secondary && (
            <text y={startY + rows.length * rowH - 40} textAnchor="middle" fill={COLORS.textDim} fontFamily={FONT} fontSize={28} fontWeight={700}>
              {secondary}
            </text>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
