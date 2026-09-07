import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { KeyPoints } from "../components/KeyPoints";
import { LockShape, SceneLabel } from "../illustrations/primitives";

/** Data getting secured: scattered document tiles converge and a padlock
 * snaps shut over them (encryption / access lock-down). */
export const StateChange: React.FC<{
  label?: string;
  primary: string;
  secondary: string;
  items?: string[];
  accent?: string;
  durationInFrames: number;
}> = ({ label, primary, secondary, items = [], accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Docs slide inward, then the lock closes over them.
  const gather = interpolate(p, [0.1, 0.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const lockIn = spring({ frame: frame - durationInFrames * 0.45, fps, config: { damping: 12 } });
  const closed = interpolate(p, [0.6, 0.72], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const glow = 0.35 + Math.sin(frame / 10) * 0.15 * closed;
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  const docs = [
    { x: -430, y: -110 },
    { x: 430, y: -140 },
    { x: -360, y: 150 },
    { x: 400, y: 130 },
  ];

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform={hasPoints ? "translate(-440 20) scale(0.78)" : "translate(0 80)"}>
          {closed > 0 && <circle r={250} fill={COLORS.accent} opacity={glow * 0.16} />}

          {docs.map((d, i) => {
            const x = interpolate(gather, [0, 1], [d.x, d.x * 0.26]);
            const y = interpolate(gather, [0, 1], [d.y, d.y * 0.26]);
            const rot = interpolate(gather, [0, 1], [i % 2 ? 16 : -16, 0]);
            return (
              <g key={i} transform={`translate(${x} ${y}) rotate(${rot})`} opacity={0.35 + 0.65 * gather}>
                <rect x={-52} y={-66} width={104} height={132} rx={10} fill="rgba(255,255,255,0.10)" stroke={COLORS.accent2} strokeWidth={3} />
                {[0, 1, 2, 3].map((l) => (
                  <rect key={l} x={-34} y={-42 + l * 26} width={68} height={7} rx={3.5} fill={COLORS.accent2} opacity={0.6} />
                ))}
              </g>
            );
          })}

          <g transform={`scale(${1.9 * lockIn})`} opacity={lockIn}>
            <LockShape x={0} y={0} open={closed < 0.5} color={COLORS.accent} />
          </g>

          {primary && (
            <text y={280} textAnchor="middle" fill={COLORS.text} fontFamily={FONT} fontSize={38} fontWeight={800} opacity={closed}>
              {primary}
            </text>
          )}
          {secondary && (
            <text y={330} textAnchor="middle" fill={COLORS.textDim} fontFamily={FONT} fontSize={28} fontWeight={600} opacity={closed}>
              {secondary}
            </text>
          )}
        </g>
      </svg>
      <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} variant="panel" />
    </AbsoluteFill>
  );
};
