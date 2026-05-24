/**
 * Shared text utilities.
 */

/** Returns true if the content appears to be JSON (starts with '{' or '['). */
export function isJsonContent(content: string): boolean {
  const trimmed = content.trim();
  return trimmed.startsWith("{") || trimmed.startsWith("[");
}
