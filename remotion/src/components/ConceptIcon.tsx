import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import * as Icons from "lucide-react";
import { COLORS } from "../theme";

const FALLBACK = Icons.Info;

/** Renders the concept icon chosen for this scene by the planning step.
 * The name comes from the generated visual plan (validated there against the
 * installed icon set), so this component stays domain-neutral - it never
 * inspects the narration or carries a keyword list of its own. */
export const ConceptIcon: React.FC<{ icon: string; size?: number; delay?: number }> = ({
  icon,
  size = 176,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const IconComp = (Icons as unknown as Record<string, typeof FALLBACK>)[icon] ?? FALLBACK;

  const s = spring({ frame: frame - delay, fps, config: { damping: 10, mass: 0.6, stiffness: 160 } });
  const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const bob = Math.sin((frame - delay) / 16) * 6;
  const rotate = interpolate(s, [0, 1], [-12, 0]);

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        background: `linear-gradient(135deg, ${COLORS.accent}2E, ${COLORS.card})`,
        border: `3px solid ${COLORS.accent}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: `0 0 46px ${COLORS.accent}66`,
        opacity,
        transform: `scale(${s}) translateY(${bob}px) rotate(${rotate}deg)`,
      }}
    >
      <IconComp size={size * 0.49} color={COLORS.accent} strokeWidth={1.6} />
    </div>
  );
};
