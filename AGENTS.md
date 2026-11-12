# Agent Working Agreement

## Canonical project configuration

`config/project_config.yaml` is the single canonical configuration file for
project runtime and experiment settings. Update or extend its existing sections
when configuration changes are needed; do not introduce another project
configuration file. Keep dependency and tool manifests (such as
`requirements.txt`) separate. If a distinct project configuration file appears
necessary, explain the constraint and get user approval before adding it.

## Mandatory Change Logging

For every requested change that modifies code, notebooks, scripts, configuration, or documentation, update `CHANGELOG.md` in the same task using this format:

```md
## YYYY-MM-DD

### Descriptive change title
- **Context / trigger:** What problem, finding, constraint, or new requirement prompted the work?
- **Decision / change:** What was decided or implemented? For a pivot, what direction changed?
- **Rationale:** Why was this approach chosen? Include alternatives or trade-offs only when they were actually considered.
- **Outcome / impact:** What changed for behavior, outputs, workflow, or project direction? Note what stayed the same.
- **Evidence / validation:** What tests, comparisons, or other evidence support the result? If validation was not run or was not recorded, state that explicitly; do not imply it passed.
- **Affected files / artifacts:** List the relevant source, documentation, and generated artifact paths.
- **Related work:** Link relevant user stories, plans, prior decisions, or follow-up work when useful.
```

Use one ISO-date heading (`YYYY-MM-DD`) per day, with that day's entries immediately beneath it; place the newest date first. Use descriptive, unnumbered entry titles. Keep the fields in the order shown; include every field except Related work, which is optional. Be concise for routine changes and explain context, rationale, and before/after direction more fully for significant changes or pivots.

Record only facts supported by the request, implementation, or validation evidence. Do not invent historical context, alternatives, outcomes, or validation. For historical entries, state when information was not recorded in the source rather than inferring it. Preserve meaningful details about behavior, outputs, decisions, and affected files when editing existing entries.

Treat the changelog update as part of the definition of done. In the final response, include a short confirmation that it was updated.

## No-Skip Rule

If a changelog update is not possible, the agent must:

1. stop before claiming completion,
2. explain why,
3. provide the exact changelog entry text to be applied manually.
