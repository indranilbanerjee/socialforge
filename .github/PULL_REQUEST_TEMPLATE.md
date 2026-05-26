# Pull Request

## Summary

<!-- One or two sentences describing the change and why it's needed. -->

## Type of change

- [ ] Bug fix (skill output wrong, script crash, broken link, broken install)
- [ ] New skill / command / agent
- [ ] Industry/platform/compliance update (benchmark, regulation, channel mechanic)
- [ ] Documentation only
- [ ] Repository hygiene (CI, templates, dependency bump, refactor)
- [ ] Other (explain):

## Which surface(s) affected

- [ ] Claude Code (CLI + IDE extensions) via `.claude-plugin/plugin.json`
- [ ] Anthropic Cowork (same `.claude-plugin/` files)
- [ ] Both / either (text-only docs change)

## Checklist

- [ ] I read [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- [ ] I read [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md)
- [ ] My change does not break any existing skill, script, or command
- [ ] I ran the relevant smoke test (e.g., `python3 scripts/<script>.py --help` exits 0 for any modified script)
- [ ] I updated the matching docs / SKILL.md / CHANGELOG.md entry if behavior changed
- [ ] I bumped the version in `.claude-plugin/plugin.json` if this is a release
- [ ] I updated the README badge + "Current version" + "Release notes" if this is a release
- [ ] My PR title follows the convention `vX.Y.Z: short description` for releases, or `fix:` / `feat:` / `docs:` / `chore:` prefix otherwise

## Compliance / regulation source (only if this changes a compliance rule)

<!-- Link the primary source (official regulation text, regulator announcement, peer-reviewed analysis) so the rule can be re-verified. Wikipedia / blog posts are NOT acceptable as primary sources for compliance changes. -->

## Testing notes

<!-- How you verified the change. For new skills: the prompt you tested. For script changes: the input/output you verified. For compliance: the source you cross-referenced. -->

## Screenshots / output samples (optional)

<!-- Helpful for skill output changes, README rewrites, visual creative-brief changes. -->

---

By submitting this PR you confirm you have the right to contribute the content under the project's MIT license, and that any AI-generated portions were substantively reviewed by you before submission.
