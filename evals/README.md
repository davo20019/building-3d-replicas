# Evaluations

Scenarios for checking that an agent using this skill does what it should, in the format Anthropic's skill
guidance suggests (`query`, `files`, `expected_behavior`). Each targets a failure that happened while the skill
was being built; `05-triggering.json` checks when the skill should and should not be chosen.

There is no built-in runner. To run one: start a fresh agent session with the skill installed, give it the
query and files, and score each expected behaviour as met or not. Run the same query without the skill for a
baseline. Run each with every model you intend to use (Anthropic suggests Haiku, Sonnet and Opus); smaller
models may need more explicit steps.

| Eval | Catches |
|---|---|
| 01-cowbell-from-photo | fitting before checking cut-outs; fitting published sizes; building from the answer key |
| 02-rounded-object-one-photo | trusting a parameter the photo can't measure; an angular case where the real one is rounded |
| 03-trademarked-product | logos, shop photos in a public repo, protected product shapes |
| 04-interior-from-video | interiors placed by eye; unchecked scales |
| 05-triggering | the skill firing for stylised models, scan clean-up or image-to-3D |

The scripts have their own tests in `tests/` (`uv run pytest`).
