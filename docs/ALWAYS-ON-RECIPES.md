# Always-on recipes — monthly preview build, weekly performance ingest

**Checked 2026-10-04.** Each platform's own documentation was read for this file; **none of these recipes has been run end to end by us on any of the five platforms.** Where a platform's docs say nothing about running a plugin's scripts, this file says so instead of guessing. Grades: **[P]** primary (the platform's own page), **[unverified]** not stated in anything read.

SocialForge's approval chain needs a human. An always-on job is therefore limited to the two steps that are read-only or local and cost nothing, and stops at the first missing input.

## What may run unattended

| Step | Unattended? | Why |
|---|---|---|
| Monthly preview build — `build-review-gallery` | Yes | Local file, no server, no API cost; the gallery is read-only, so approvals still happen in conversation |
| Weekly performance ingest — `ingest-performance` (ingest, then wins) | Yes, only when a new export file is present | Writes `performance.json` and reports; never invents numbers |
| Creative generation (`compose-creative`, `generate-video`, `full-pipeline`), approvals (`manage-reviews`), `finalize-month`, scheduler or messaging hand-off | **Never** | Spends credits, passes approval gates, or reaches the public. A saved, scheduled prompt is not live user input and cannot stand in for approval |

`create-previews` declares `disable-model-invocation`, so a scheduled prompt may not be able to start it. The review gallery covers the monthly view and is model-invocable.

## The two jobs

Every job states the six facts Grok Bot's docs ask a routine to confirm ([docs.x.ai/grok-bot/skills-routines-and-automations](https://docs.x.ai/grok-bot/skills-routines-and-automations)): owner, schedule and time zone, input source, expected result, approval boundary, and what happens when a source is missing. The prompts below carry them, so they port to any platform that takes a plain-language prompt.

### Job A — monthly preview build

```
Job: monthly preview build for brand {brand}, month {YYYY-MM}.
Schedule: day {DD} of each month, {HH:MM} {time zone}.
Input: the brand profile and the month's calendar-data.json in the SocialForge workspace.
Steps: run the build-review-gallery skill for this brand and month.
Report: where gallery.html was written, the posts_without_media list, and any error.
Approval boundary: do NOT generate images or video, approve or reject posts, finalize,
sign, schedule, publish, or message anyone.
If the brand profile or the month's calendar is missing: say which one, and stop.
Never create placeholder data.
```

### Job B — weekly performance ingest

```
Job: weekly performance ingest for brand {brand}, month {YYYY-MM} (the month the numbers are FROM).
Schedule: every {weekday} at {HH:MM} {time zone}.
Input: CSV exports in {drop folder}.
Steps: for each platform run the ingest-performance skill with --source set to one constant label per platform
(for example "linkedin"). If that platform's files do not overlap, ingest every file in the folder. If it
exports cumulative month-to-date totals (each new file repeats the earlier posts), add --replace and ingest
ONLY its newest file: an older file would replace the newer snapshot with stale numbers. Then rank the wins.
A file the script answers with "status": "already_ingested" is not new: count it as "no new export",
do not retry it.
Report: rows matched and unmatched (name the unmatched ids), the verdict
(clear_wins / no_clear_wins / nothing_rankable), winners with vs_month_median.
Approval boundary: do not plan the month, edit the calendar, or send the report anywhere
except {delivery target}.
If the drop folder has no file, or every file comes back already_ingested: report "no new export" and stop.
Never estimate numbers.
```

**A repeat of the same file is a no-op; a cumulative export needs `--replace`.** Each source records the sha256 of its CSV bytes, so ingesting the same file again, under any label, adds nothing and answers `already_ingested` with the earlier source (checked 2026-10-04 against `scripts/ingest_performance.py`). That is why Job B needs no skip rule. It does not make two *different* files safe to combine: a platform that exports cumulative totals sends a new file each week that contains last week's posts again, and ingesting it next to last week's would count those posts twice. For those platforms use one constant `--source` label with `--replace`: every row previously ingested under that label is removed before the new file is ingested, so only the latest snapshot stays, and rows from other labels are untouched. Two limits: `--replace` refuses a label that was ingested before rows carried their source label, because those old rows cannot be told apart (use a new label, or delete the month's performance.json and re-ingest); and a `--replace` whose file matches no calendar post fails and leaves the earlier snapshot in place. One hazard is yours to avoid, because the script cannot see it: `--replace` trusts the file it is given, so ingesting an older cumulative file after a newer one replaces the newer snapshot with stale numbers (the older file's hash is no longer on record once it was replaced). Under `--replace`, ingest only the newest file.

## Where each one runs

| Platform | Runs on | Schedule it with | SocialForge compatibility |
|---|---|---|---|
| Claude Code routines | Anthropic cloud, fresh clone, no permission prompts | `/schedule` | Skills must be in the cloned repository; plugin data is not. See below |
| Claude Code Desktop scheduled task | Your machine, only while the app is open and the computer is awake | Routines page, **Local** | Direct access to local files and the plugin workspace |
| Claude Tag | Slack, in channels an Owner configured | Ask `@Claude` in the channel | [unverified] whether plugin skills and scripts are available |
| Grok Bot | A Bot's own cloud computer | Plain-language routine request | [unverified]; SocialForge's Grok manifest targets the Build CLI, not Grok Bot |
| Gemini Spark | Google's cloud | Plain-language recurring task | [unverified]; documented examples are Workspace chores |
| Hermes cron | Your machine, via the gateway daemon | `hermes cron create` | SocialForge ships a Hermes adapter; fresh session per job |

### Claude Code routines and Desktop tasks

Source: [code.claude.com/docs/en/routines](https://code.claude.com/docs/en/routines) and [desktop-scheduled-tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks) [P].

- A cloud routine runs "autonomously as full Claude Code cloud sessions": no permission-mode picker, shell commands and skills "committed to the cloned repository", and connectors, "all without stopping for approval". Minimum interval one hour. A custom cadence such as "the first of each month" is set with `/schedule update`. Create with `/schedule`, e.g. `/schedule daily PR review at 9am` is the documented shape.
- **Remove write connectors.** The docs: "Claude can use every tool from an included connector, including writes, without asking for permission during a run." Leave the `postiz` and `whatsapp-business-tools` catalog connectors out of any routine.
- **Fire prompts are not approval.** "The fired prompt is not live user input and can't act as approval or consent for actions during the run." This matches SocialForge's gates.
- **State.** The comparison table lists local files for cloud routines as "No (fresh clone)". SocialForge keeps brand profiles and outputs in its plugin data directory (`${CLAUDE_PLUGIN_DATA}/socialforge/`, else `~/socialforge-workspace`), so a cloud routine would start without them unless you put that state somewhere the clone includes. That is an inference from the two docs, not something they state. For SocialForge prefer a **Desktop local task**: direct access to your files and tools, a per-task permission mode, one catch-up run after a sleep (not a backlog), and a minimum interval of one minute. A task in Manual mode that needs an un-approved tool stalls until you answer, so run it once with **Run now** and approve each tool "always" first.
- A green run status "does not mean the task in your prompt succeeded" — open the run and read it.
- Time on the hour can start several minutes late; the docs suggest a few minutes past, e.g. 9:07.

### Claude Tag

Sources: [anthropic.com/news/introducing-claude-tag](https://www.anthropic.com/news/introducing-claude-tag) (2026-06-23) and [support.claude.com/en/articles/15594475-what-is-claude-tag](https://support.claude.com/en/articles/15594475-what-is-claude-tag) [P].

- A shared agent in Slack, beta for Team and Enterprise. "It can also schedule tasks for itself, pursuing a project autonomously over hours or days." An Owner provisions the identity, connects tools and picks channels.
- Ask in a configured channel with Job A or B's text; `@Claude what triggers do you have set up here?` lists standing work, and the Owner-only Activity page lists "every scheduled and one-time task".
- The support article read does not describe an approval flow for scheduled work, so treat the job as unattended and keep to the table above. Whether SocialForge's skills and Python scripts are available there is not stated.

### Grok Bot

Source: [docs.x.ai/grok-bot/skills-routines-and-automations](https://docs.x.ai/grok-bot/skills-routines-and-automations) [P].

- A routine "tells one Bot when to run a workflow—on a schedule or, where supported, after an event." You ask the owning Bot in plain language, e.g. "Every weekday at 8:00 AM, run the [Skill Name] against [input source]." A Bot can own up to 50 routines.
- Routines are meant to "Require approval for sending, purchasing, deleting, publishing, or changing production systems", the same boundary as the table above.
- Not stated in the page read: where files persist between runs, and whether Agent Skills (`SKILL.md`) load. SocialForge's `.grok-plugin/` manifest is for the xAI Build CLI; do not assume Grok Bot reads it.

### Gemini Spark

Source: [blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app](https://blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app/) (2026-05-19) [P].

- "A 24/7 personal AI agent" in Google's cloud that "keeps working in the background even when you close your laptop or lock your phone"; it is "designed to ask you first before performing high-stakes actions like spending money or sending emails." At that date it was a beta for U.S. Google AI Ultra subscribers; check Google's current availability for your region and plan.
- The documented recurring tasks are Gmail, Docs and similar chores. Nothing read says it can run a plugin's Python scripts, so start with Job B's read-only half on a pasted export, and only extend it after a test.

### Hermes cron

Source: [hermes-agent.nousresearch.com/docs/user-guide/features/cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) [P].

- `hermes cron create "<schedule>" "<prompt>" --skill <name>`, or `/cron add` in chat. Schedules accept intervals (`every 2h`), natural day/time (`every monday 9am`), cron expressions (`0 9 * * 1-5`) and ISO timestamps.
- "Cron execution is handled by the gateway daemon", installed with `hermes gateway install`. Each job runs in a fresh agent session; output is saved under `~/.hermes/cron/output/{job_id}/`. "A scheduled job with no operator present cannot prompt for input", so the prompt must be self-contained, as above.
- Jobs get only the toolsets configured for the `cron` platform. Check that your cron toolset can run shell commands before the first run.
- `--workdir` sets the directory the job runs in; the path must be an absolute directory that exists.
- Deterministic steps need no model: `hermes cron create "every 5m" --no-agent --script <file>` runs a script on schedule and delivers its stdout. Job B's ingest is a plain script (`scripts/ingest_performance.py`), so this is the cheapest way to run it on Hermes. Where the script file must live is in Hermes' docs, not here.

## Before turning any job on

1. Run it once by hand and read the transcript.
2. Confirm the job's connector or toolset list has no write-capable connector in it.
3. Confirm the brand profile and the month's folder are where the job runs.
4. Put the platform's own limits in the prompt as guardrails (a missed run can fire late; say what the job does if it is the wrong day).

## Source ledger

| Claim area | URL | Checked |
|---|---|---|
| Routines, fresh clone, no prompts, connectors | https://code.claude.com/docs/en/routines | 2026-10-04 |
| Desktop local tasks, permissions, missed runs | https://code.claude.com/docs/en/desktop-scheduled-tasks | 2026-10-04 |
| Claude Tag scheduling and admin | https://www.anthropic.com/news/introducing-claude-tag | 2026-10-04 |
| Claude Tag overview, Activity page | https://support.claude.com/en/articles/15594475-what-is-claude-tag | 2026-10-04 |
| Grok Bot routines and approval boundary | https://docs.x.ai/grok-bot/skills-routines-and-automations | 2026-10-04 |
| Gemini Spark | https://blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app/ | 2026-10-04 |
| Hermes cron | https://hermes-agent.nousresearch.com/docs/user-guide/features/cron | 2026-10-04 |
