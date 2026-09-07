import React from "react";
import { Composition } from "remotion";
import { ChapterComposition } from "./components/ChapterComposition";
import { StoryboardScene } from "./types";
import scenesData from "../public/storyboard.json";

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

const allScenes = scenesData as StoryboardScene[];
const chapterIds = Array.from(new Set(allScenes.map((s) => s.chapter_id)));

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {chapterIds.map((chapterId) => {
        const scenes = allScenes.filter((s) => s.chapter_id === chapterId);
        const totalSeconds = scenes.reduce((acc, s) => acc + s.duration, 0);
        const durationInFrames = Math.max(1, Math.round(totalSeconds * FPS));
        // Composition ids may only contain a-z, A-Z, 0-9, CJK and "-" (no
        // underscores), while chapter_id ("chapter_00", ...) is used as-is
        // everywhere else (JSON data, audio filenames).
        const compositionId = chapterId.replace(/_/g, "-");
        return (
          <Composition
            key={chapterId}
            id={compositionId}
            component={ChapterComposition}
            durationInFrames={durationInFrames}
            fps={FPS}
            width={WIDTH}
            height={HEIGHT}
            defaultProps={{ scenes }}
          />
        );
      })}
    </>
  );
};
