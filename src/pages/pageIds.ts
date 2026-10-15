export const PAGE_IDS = [
  "playback",
  "playlist",
  "visualizer",
  "translator",
  "settings",
  "debug",
  "license",
] as const;

export type PageId = (typeof PAGE_IDS)[number];
