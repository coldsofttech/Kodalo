/** Helpers for the post ideas the AI returns. */

/**
 * The idea as plain text to paste elsewhere, with the chosen hook and the sources of its claims.
 * @param {any} idea
 * @param {string} hook
 */
export function ideaText(idea, hook) {
  const lines = [
    `${idea.working_title} (${idea.format === 'carousel' ? 'Carousel' : 'Single image'})`,
  ];
  if (hook) lines.push(`Hook: ${hook}`);
  if (idea.objective) lines.push(`Objective: ${idea.objective}`);
  if (idea.outline.length > 0)
    lines.push('', ...idea.outline.map((/** @type {string} */ b) => `- ${b}`));
  if (idea.visual_concept) lines.push('', `Visual: ${idea.visual_concept}`);
  if (idea.claims_used.length > 0) {
    lines.push('', 'Claims and sources:');
    for (const claim of idea.claims_used) {
      lines.push(`- ${claim.text} (${claim.file}: "${claim.quote}")`);
    }
  }
  if (idea.risk_notes) lines.push('', `Careful: ${idea.risk_notes}`);
  return lines.join('\n');
}
