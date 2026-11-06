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

A strategy, exactly three angles with three hooks each and up to five post ideas. Ideas are plans,
not finished copy. A claim is kept only when its quote is one of the quotes that were sent; others
are left out and listed as warnings. Nothing is saved on the computer: the window keeps the result
for the same choice and `Refresh with AI` asks again.

## Prompt

`src/kodalo/core/ai/prompts/marketing/marketing-strategist.SKILL.md`. Compared with the skill it
came from, it has no argument parsing, selector matching, `--allow-unverified`, `source`, `brief`,
`selection` or `claims_to_avoid` blocks; the code does those.
