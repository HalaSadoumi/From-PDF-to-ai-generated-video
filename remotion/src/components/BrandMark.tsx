import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";

/** S2M logo, held in the top corner for the whole chapter.
 *
 * Drawn once outside the scene series, so it stays put across cuts instead of
 * fading in again at every scene. Deliberately understated — a course carries
 * its owner's mark, it does not advertise it: modest size, slightly held back
 * opacity, and clear of both the centred scene title and the lower third.
 *
 * The file is a light variant of the logo: the brand's dark brown is
 * unreadable on the dark background these videos use, so the wordmark is
 * carried in white while the cyan device keeps the brand colour.
 */
export const BrandMark: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 0.85], { extrapolateRight: "clamp" });

  return (
    <Img
      src={staticFile("s2m-logo.png")}
      style={{
        position: "absolute",
        top: 46,
        left: 56,
        width: 132,
        height: "auto",
        opacity,
        pointerEvents: "none",
      }}
    />
  );
};
