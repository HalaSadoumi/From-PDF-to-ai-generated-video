import React from "react";
import { AbsoluteFill, Audio, Series, staticFile, useVideoConfig } from "remotion";
import { StoryboardScene, VisualPlan } from "../types";
import { SceneRenderer } from "./SceneRenderer";
import { AnimatedBackground } from "./AnimatedBackground";
import { SceneBackdrop } from "./SceneBackdrop";
import { SceneTransition } from "./SceneTransition";
import { BrandMark } from "./BrandMark";
import visualPlansData from "../../public/scene_visuals.json";
import backdropList from "../../public/backdrops.json";

const VISUAL_PLANS = visualPlansData as Record<string, VisualPlan>;
// Which scenes actually have a generated backdrop on disk. Generation is a
// best-effort batch, so the renderer must cope with any subset being present.
const BACKDROPS = new Set(backdropList as string[]);

export const ChapterComposition: React.FC<{ scenes: StoryboardScene[] }> = ({ scenes }) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill>
      {/* Drawn once, outside the Series, so the drifting gradient keeps moving
       * across scene cuts instead of restarting. Scenes that have a generated
       * backdrop cover it; the rest show it directly. */}
      <AnimatedBackground />
      <Series>
        {scenes.map((scene) => {
          const durationInFrames = Math.max(1, Math.round(scene.duration * fps));
          const plan = VISUAL_PLANS[scene.scene_id];
          return (
            <Series.Sequence key={scene.scene_id} durationInFrames={durationInFrames}>
              <SceneTransition sceneId={scene.scene_id}>
                {BACKDROPS.has(scene.scene_id) && (
                  <SceneBackdrop sceneId={scene.scene_id} durationInFrames={durationInFrames} />
                )}
                <SceneRenderer scene={scene} plan={plan} durationInFrames={durationInFrames} />
              </SceneTransition>
              <Audio src={staticFile(`audio/${scene.scene_id}.wav`)} />
            </Series.Sequence>
          );
        })}
      </Series>
      {/* Held above the scenes so it survives every cut, and above the
       * backdrop so it never disappears behind a dark image. */}
      <BrandMark />
      {/* Subtitles are not burnt in: they ship as a WebVTT track next to the
       * video, timed from the real speech, and toggleable by the viewer.
       * The "AI generated" notice lives in the player UI, not the picture. */}
    </AbsoluteFill>
  );
};
