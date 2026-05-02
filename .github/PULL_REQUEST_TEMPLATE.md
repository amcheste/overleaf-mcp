<!--
Thanks for the contribution! A few things that make review faster:

- Keep PRs focused. One concern per PR is easier to review and easier
  to revert if needed.
- Tests are required for new behaviour. The suite runs ~5 seconds
  locally with `uv run pytest`.
- Coverage stays at 100% on `src/overleaf_mcp/` (excluding the
  transports). If your PR drops it, add a test.
- Conventional commit messages help — `feat(tools):`, `fix(core):`,
  `docs:`, `test:`, `chore:` prefixes are the norm here.
-->

## Summary

<!-- One or two sentences. What does this PR change and why? -->

## Why

<!-- The problem this solves or the gap it fills. Link to an issue if there is one. -->

## What changed

<!-- Concrete changes. Bullet list works well. -->

## Test plan

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src/ tests/` is clean
- [ ] Coverage didn't drop (visible in the test run output)
- [ ] Manual verification (if applicable):

## Anything reviewers should look at first

<!-- Optional. "The decision in src/x.py:42 about Y" or "I'm not sure about the error message in Z, please weigh in." -->
