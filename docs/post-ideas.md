# Post ideas

`Next with AI` on Studio's Focus step plans a post with the default AI model. It is a port of the
`marketing-strategist` skill, with the parts the app does itself taken out.

## What is sent

One request (history purpose `studio`) with the saved README analysis for the choice:

- **Tool / Utility post**: the product's tagline and summary and up to eight features that are not
  planned, headline ones first.
- **Feature post**: the chosen feature (a planned one is refused), or the chosen use case with the
  features that serve it, or the chosen capability.

Each item carries its evidence quote and the claims that need care. The list of claims to avoid is
built from those claims in code, not by the model.

## What comes back

A strategy, exactly three angles with three hooks each and as many post ideas as Settings > AI asks for (5 by default, 1 to 20). Ideas are plans,
not finished copy. A claim is kept only when its quote is one of the quotes that were sent; others
are left out and listed as warnings. The ideas are saved for the same choice. `Refresh with AI`
asks again and adds the new ideas to the saved ones: the ones saved stay as they are, the AI is told
their titles so it does not repeat them, and an idea with the same title is skipped. An idea can be
flagged as posted (automatically after posting to Instagram, or when you say so after an export);
the Ideas step shows a Posted badge on it.

## Prompt

`src/kodalo/core/ai/prompts/marketing/marketing-strategist.SKILL.md`. Compared with the skill it
came from, it has no argument parsing, selector matching, `--allow-unverified`, `source`, `brief`,
`selection` or `claims_to_avoid` blocks; the code does those.
