// HSL palette: muted, legible on dark canvas, ~50% saturation, ~55% lightness
const TAG_PALETTE: string[] = [
  "#d4956b", // amber/copper
  "#7eb8da", // steel blue
  "#8fbc8f", // sage
  "#ca8a8a", // dusty rose
  "#a089c4", // muted lavender
  "#6bada8", // teal
  "#d4a574", // tan
  "#7a9ec4", // cornflower
  "#b5a675", // olive
  "#c08095", // mauve
  "#6daa8a", // sea green
  "#ad93c4", // periwinkle
];

/** Deterministic hash → palette index */
function hashTag(tag: string): number {
  let h = 0;
  for (let i = 0; i < tag.length; i++) {
    h = (h * 31 + tag.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

export function tagColor(tag: string): string {
  return TAG_PALETTE[hashTag(tag) % TAG_PALETTE.length];
}

export const GraphStyle = {
  BG: "#111111",

  TAG_PALETTE,
  tagColor,

  // Default colour when a node has no tags
  UNTAGGED_COLOR: "#d4d4d4",

  // Superseded / deprecated dim factors
  SUPERSEDED_ALPHA: 0.25,
  DEPRECATED_ALPHA: 0.25,

  /** Derive a base hex colour from the node's primary tag */
  nodeBaseColor(node: { tags: string[] }): string {
    if (node.tags.length === 0) return this.UNTAGGED_COLOR;
    const sortedTags = [...node.tags].sort();
    return this.tagColor(sortedTags[0]);
  },

  // Node sizing
  nodeRadius(connections: number): number {
    return Math.sqrt((connections ?? 0) + 1) * 4;
  },

  // Orb highlight — ratio of radius for the specular dot offset
  SPECULAR_OFFSET_RATIO: 0.3,
  SPECULAR_DOT_RATIO: 0.22,

  // Highlight ring (selected / hovered)
  HIGHLIGHT: {
    COLOR: "rgba(255, 255, 255, 0.5)",
    WIDTH: 2,
  },

  // Recent-update ring
  RECENT: {
    ALPHA_MAX: 0.35,
    PERIOD_MS: 2000,
    WINDOW_MS: 7 * 86400000,
  },

  // Search match breathing ring
  SEARCH: {
    ALPHA_MIN: 0.3,
    ALPHA_MAX: 0.65,
    PERIOD_MS: 1500,
  },

  // In-progress node breathing
  IN_PROGRESS: {
    ALPHA_MIN: 0.5,
    ALPHA_MAX: 1.0,
    PERIOD_MS: 1800,
  },

  // Labels
  LABEL: {
    SCALE_THRESHOLD: 0.7,
    MAX_CHARS: 30,
    COLOR: "rgba(212, 212, 212, 0.85)",
  },

  // Links
  LINK: {
    COLOR_RELATED: "rgba(100, 116, 139, 0.3)",
    COLOR_SUPERSEDES: "rgba(156, 163, 175, 0.5)",
    WIDTH_RELATED: 1.5,
    WIDTH_SUPERSEDES: 2,
    SUPERSEDES_PARTICLE_COUNT: 4,
    SUPERSEDES_PARTICLE_SPEED: 0.004,
    SUPERSEDES_PARTICLE_WIDTH: 2,
  },
} as const;
