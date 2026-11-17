import type { FormExerciseId } from "@/lib/mechanics";

/**
 * Form-check exercises. A member films a short side-on clip; the phone measures joint
 * angles, reps and tempo on the device; a coach rates each criterion and writes cues.
 * The member's own clips, ratings and measurements over time show how their form changes.
 *
 * COACHING CONTENT PLACEHOLDER — criteria and filming guidance to be finalised by the head coach.
 */
export interface FormExercise {
  id: FormExerciseId;
  name: string;
  filming: string[];
  criteria: { id: string; label: string }[];
}

export const FORM_EXERCISES: FormExercise[] = [
  {
    id: "goblet-squat",
    name: "Goblet squat",
    filming: ["Phone on its side at hip height, 2–3 metres away", "Stand side-on with your whole body in frame", "Three slow reps"],
    criteria: [
      { id: "depth", label: "Depth you control without pain" },
      { id: "knees", label: "Knees track over toes" },
      { id: "torso", label: "Chest tall, back neutral" },
    ],
  },
  {
    id: "hip-hinge",
    name: "Hip hinge",
    filming: ["Phone on its side at hip height, 2–3 metres away", "Side-on, broomstick along your back", "Three slow reps"],
    criteria: [
      { id: "hips-back", label: "Hips travel back" },
      { id: "spine", label: "Back stays neutral" },
      { id: "knees", label: "Soft, steady knees" },
    ],
  },
  {
    id: "push-up",
    name: "Push-up (any incline)",
    filming: ["Phone on its side at floor or bench height", "Side-on, whole body in frame", "Three reps at your current level"],
    criteria: [
      { id: "line", label: "Straight line head to heels" },
      { id: "depth", label: "Controlled depth" },
      { id: "elbows", label: "Elbows tucked about 45°" },
    ],
  },
];

export const RATING_LABEL: Record<number, string> = { 1: "Needs work", 2: "Improving", 3: "Solid" };

export const formExerciseById = (id: string) => FORM_EXERCISES.find((e) => e.id === id);

/** Upload limits (prototype). Production: direct-to-host uploads with transcoding. */
export const FORM_CHECK_LIMITS = { maxBytes: 50 * 1024 * 1024, maxSeconds: 60 };

/** Coach minutes per form-check review — ASSUMPTION for capacity planning, to validate with time studies. */
export const FORM_CHECK_REVIEW_MINUTES = 6;
