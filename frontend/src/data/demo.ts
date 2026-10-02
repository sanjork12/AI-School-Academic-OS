import snapshot from "./demo.json";
import type { CurriculumDemoView } from "./types";
// Disposable presentation snapshot. UI actions never mutate this source-derived data.
export const demo = snapshot as CurriculumDemoView;
