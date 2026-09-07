import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

/** Adds edit-like energy at every scene start: a quick push-in that settles,
 * a light sweep across the frame, and a brief accent flash.
 *
 * The direction and intensity are derived from the scene id, so consecutive
 * scenes don't all move identically — variety without any per-scene authoring
 * and without depending on what the video is about. */
export const SceneTransition: React.FC<{ sceneId: string; children: React.ReactNode }> = ({
  sceneId,
  children,
}) => {
  const frame = useCurrentFrame();

  // Deterministic per-scene variation.
  let hash = 0;
  for (let i = 0; i < sceneId.length; i++) hash = (hash * 31 + sceneId.charCodeAt(i)) % 997;
  const dirX = hash % 2 === 0 ? 1 : -1;
  const dirY = hash % 3 === 0 ? 1 : -1;

  const settle = interpolate(frame, [0, 18], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = interpolate(settle, [0, 1], [1.07, 1]);
  const shiftX = interpolate(settle, [0, 1], [26 * dirX, 0]);
  const shiftY = interpolate(settle, [0, 1], [14 * dirY, 0]);

  const flash = interpolate(frame, [0, 2, 10], [0.28, 0.22, 0], { extrapolateRight: "clamp" });
  const sweep = interpolate(frame, [0, 22], [-120, 220], { extrapolateRight: "clamp" });
  const sweepOpacity = interpolate(frame, [0, 6, 22], [0, 0.16, 0], { extrapolateRight: "clamp" });

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `scale(${scale}) translate(${shiftX}px, ${shiftY}px)`,
        }}
      >
        {children}
      </div>

      {/* Light sweep travelling across the frame on entry. */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: `${sweep}%`,
          width: "40%",
          background: `linear-gradient(100deg, transparent, ${COLORS.accent}, transparent)`,
          opacity: sweepOpacity,
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "absolute",
          inset: 0,
          background: COLORS.accent,
          opacity: flash,
          mixBlendMode: "screen",
          pointerEvents: "none",
        }}
      />
    </div>
  );
};
