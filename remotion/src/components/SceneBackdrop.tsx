import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

/** Generated ambience image behind a scene, animated with a slow Ken Burns
 * push so a still never looks frozen, and heavily darkened so the diagram and
 * text drawn on top stay legible.
 *
 * It is scenery, never information: the explanatory content of a scene lives
 * entirely in the diagram and its text, so the veil is set dark enough that a
 * poor or irrelevant generated image costs nothing.
 *
 * The image is optional by design: if none was generated for this scene, the
 * caller renders the plain animated background instead, and nothing breaks. */
export const SceneBackdrop: React.FC<{ sceneId: string; durationInFrames: number }> = ({
  sceneId,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const p = frame / Math.max(1, durationInFrames);

  // Alternate the drift direction per scene so consecutive backdrops don't
  // all push the same way.
  const forward = sceneId.charCodeAt(sceneId.length - 1) % 2 === 0;
  const scale = forward
    ? interpolate(p, [0, 1], [1.06, 1.16])
    : interpolate(p, [0, 1], [1.16, 1.06]);
  const shiftX = interpolate(p, [0, 1], forward ? [-14, 14] : [14, -14]);

  const fadeIn = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: COLORS.bg }}>
      <Img
        src={staticFile(`backdrops/${sceneId}.jpg`)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${shiftX}px)`,
          opacity: fadeIn * 0.34,
        }}
      />
      {/* Darkening veil + vignette: keeps foreground text readable whatever
       * the generated image turned out to be. */}
      <AbsoluteFill style={{ background: "rgba(10,14,26,0.70)" }} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 35%, rgba(10,14,26,0.85) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
