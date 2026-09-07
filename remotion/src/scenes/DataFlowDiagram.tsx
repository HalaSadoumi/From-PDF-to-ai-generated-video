import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { AnimatedArrow, DeviceBox, SceneLabel, ServerStack, WrappedText } from "../illustrations/primitives";

/** Diagram: several sources on the left, arrows drawing themselves toward a
 * central platform, then a result appearing on the right. The generic
 * "collect -> process -> output" explainer beat. */
export const DataFlowDiagram: React.FC<{
  label?: string;
  sources: string[];
  hub?: string;
  result?: string;
  durationInFrames: number;
}> = ({ label, sources, hub = "Traitement", result, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;

  const items = sources.slice(0, 3);
  const spacingY = 200;
  const startY = -((items.length - 1) * spacingY) / 2;

  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const hubIn = spring({ frame: frame - 26, fps, config: { damping: 13 } });
  const resultProgress = interpolate(p, [0.72, 0.88], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const hubPulse = 1 + Math.sin(frame / 9) * 0.035 * hubIn;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(-60 70)">
          {items.map((src, i) => {
            const delayFrames = i * 12;
            const s = spring({ frame: frame - delayFrames, fps, config: { damping: 13 } });
            const y = startY + i * spacingY;
            const arrowProgress = interpolate(p, [0.28 + i * 0.07, 0.52 + i * 0.07], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <g key={i}>
                <DeviceBox x={-620} y={y} w={200} h={112} label={src} color={COLORS.accent} opacity={s} scale={s} />
                <AnimatedArrow
                  from={[-505, y]}
                  to={[-130, 0]}
                  progress={arrowProgress}
                  color={COLORS.accent}
                  curve={y === 0 ? 0 : -y * 0.22}
                />
              </g>
            );
          })}

          <g transform={`scale(${hubIn * hubPulse})`}>
            <ServerStack x={0} y={-20} label={hub} color={COLORS.accent2} opacity={hubIn} />
          </g>

          {result && (
            <>
              <AnimatedArrow from={[130, 0]} to={[480, 0]} progress={resultProgress} color={COLORS.accent3} />
              <g opacity={resultProgress} transform={`translate(660 0) scale(${resultProgress})`}>
                <rect x={-150} y={-72} width={300} height={144} rx={16} fill={`${COLORS.accent3}2E`} stroke={COLORS.accent3} strokeWidth={4} />
                <WrappedText text={result} y={12} maxWidth={272} fontSize={30} fontWeight={800} maxLines={3} />
              </g>
            </>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
