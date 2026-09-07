/** Shape of one entry in storyboard.json, produced by the Python pipeline
 * (narration_original.py). `visual_type` / `visual_description` /
 * `on_screen_text` / `transition` are the storyboard fields defined by the
 * cahier des charges (section 8.3); the renderer drives its animation from
 * the richer VisualPlan below instead, but they are kept here so the type
 * matches the file on disk. */
export interface StoryboardScene {
  scene_id: string;
  chapter_id: string;
  duration: number;
  narration: string;
  visual_type: string;
  visual_description: string;
  on_screen_text: string;
  transition: string;
  audio_path: string | null;
}

/** LLM-generated animated-scene plan, keyed by scene_id in scene_visuals.json.
 * `archetype` selects the Remotion component; the remaining fields are its
 * text slots (meaning varies per archetype - see SceneRenderer). */
export interface VisualPlan {
  archetype: string;
  label: string;
  items: string[];
  primary: string;
  secondary: string;
  /** One sentence stating what the scene teaches, shown as a lower third on
   * every archetype. Optional: plans generated before this field existed
   * simply render without it. */
  takeaway?: string;
  /** Lucide icon name, validated during planning against the installed set. */
  icon: string;
  /** English description used to generate this scene's backdrop image. */
  image_prompt: string;
}
