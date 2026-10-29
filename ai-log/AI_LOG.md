# AI log — DASH-247

This folder holds the full Claude Code session that produced this repo (`session-export.txt`, exported with `/export`) and this guide to reading it.

## How to read it

- `session-export.txt` is the whole session in order: my prompts, Claude's responses, and the tool calls (shell commands, file edits, test runs) with their output inline.
- The session follows the implementation order in [PLAN.md §8](../PLAN.md). The phase table below maps each part to its commits, so you can jump between the log and `git log`.
- Data-heavy answers end with a **Verify** table: each number, the query or script that produced it, and its raw output. Corrections found that way are listed under "Corrections" at the end of those answers.
- The fastest way in is the **corrections and redirections index** below. Search the export for a quote to land on that moment.

## Sittings

I worked in several sittings. Gaps between timestamps in the log and in `git log` are breaks, not time spent by the tools.

## Phases and commits


| Phase                       | What happened                                                                                                                                       | Commits                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 0. Exploration and plan     | Cloned the starter, profiled the data, found the spike, duplicates and timezone issues; created the `/verify` skill; agreed the rule; wrote PLAN.md | `e695143`                                                   |
| 1. Skeleton                 | Compose, migrations, idempotent seed, test harness; then the ticket quoted in the README and PLAN.md §10 (LLM) filled in                            | `d2e3f08` `4bb77d0` `ace6c9a` `b8b9cf6`                     |
| 2. Rules                    | Threshold constants and the pure rule and ranking, test-first                                                                                       | `098a200` `452aaa0`                                         |
| 3. Data                     | Independent reference script, local-week aggregation, dedup view, seed known answers; CLAUDE.md                                                     | `cc7946e` `7068701` `a94bc60` `d615973` `6a589ae`           |
| 4. Endpoint and minimal UI  | API with contract tests, React UI with URL state, everything from one `docker compose up`; follow-up fixes                                          | `578efb4` `5f1ea2b` `bb848d5` `bd8848c` `b6f3b62` `3f4a241` |
| 5. Refinement               | Account totals, per-type counts, frontend tests                                                                                                     | `b6cfbdb` `2e83ae1` `cb5ec49` `b6f1fc6` `e53caac`           |
| UI review                   | WCAG 2.2 contrast, the "no locations need attention" line, the as-of hint, product notes                                                            | `d34b74c` `052d442` `11bc3ca`                               |
| 6. README and install check | README for reviewers; fresh-clone install run that found two bugs; screenshots                                                                      | `e8831ce` `48169fd` `9644f92` `5617ef3`                     |


Commits titled "Add failing …" hold the tests committed before the code that makes them pass.

## Redaction

Mentions of my current employer's local setup (a container that held port 8000 early in the session, and its paths) are replaced with `[redacted: employer project]`. Nothing else in the export is changed.

<!-- TODO before submitting: confirm the redaction has been applied to session-export.txt, then delete this comment. -->

## Where I corrected or redirected Claude

Quotes are verbatim, typos included.


| #   | Phase     | Quote                                                                                                                          | What changed                                                                                                                                                                                                                                                      |
| --- | --------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 0         | "where does that number come from?"                                                                                            | Claude's "\~25/day normal" for account 6 turned out to be the busiest days, not a typical day; corrected to 13 per weekday, with the queries shown. (Claude also clarified it hadn't read the ticket yet: the "normal" wording came from the product background.) |
| 2   | 0         | "I want verification to be automatic instead of me asking every time"                                                          | Led to the `/verify` skill. Its first run corrected "7 accounts observe daylight saving" to 17.                                                                                                                                                                   |
| 3   | 0         | "i was wrong about the median handling the spike alone"                                                                        | After Claude's pushback the plan changed: flag on location totals, minimum volume on the baseline, typical range = middle 6 of 8.                                                                                                                                 |
| 4   | 0         | "missed-call rate is out of v1, I would rather spend the time on tests"                                                        | Scope cut; moved to the README's next steps.                                                                                                                                                                                                                      |
| 5   | 0         | "justify 0.3 by what it means, not by the fact that it catches Site G"                                                         | The plan's justification for the 0.3 threshold was rewritten around what it means, and it became a named constant.                                                                                                                                                |
| 6   | 1         | "the schema tests are more than this needed"                                                                                   | Testing effort was refocused on the rules and the aggregation for the rest of the project.                                                                                                                                                                        |
| 7   | 1         | "keep 8000 as the default and make it configurable by env var"                                                                 | Claude had planned to move the backend off port 8000; the default stayed and `BACKEND_PORT` was added.                                                                                                                                                            |
| 8   | 1         | "Leave docs out of the repo, quote the ticket in the README"                                                                   | `docs/` is gitignored and the README quotes the ticket.                                                                                                                                                                                                           |
| 9   | 3         | "edge case, noted in the readme for now"                                                                                       | The default as-of fix was deferred to a documented limitation instead of being built in phase 4.                                                                                                                                                                  |
| 10  | 3         | "PLAN.md should not be edited unless I say it :P, deviations go to the readme tho"                                             | A working rule in CLAUDE.md. From then on, deviations and limitations went to the README.                                                                                                                                                                         |
| 11  | 3         | "Show it to me before committing"                                                                                              | CLAUDE.md was reviewed before it was committed.                                                                                                                                                                                                                   |
| 12  | 4         | "fix the broken link in my CLAUDE.md section (weekly.py got auto-linked when I pasted it) and the blank lines between bullets" | Claude had flagged the link but missed the blank lines; both fixed.                                                                                                                                                                                               |
| 13  | UI review | "Please use WCAG 2.2 for accesibility (colors of the page)"                                                                    | The audit found form-control borders and the light flag border below 3:1; fixed and re-measured.                                                                                                                                                                  |
| 14  | UI review | "when no location is flagged, say so at the top"                                                                               | Added the attention line, test-first.                                                                                                                                                                                                                             |
| 15  | UI review | "shows the last complete week before that date, which isn't obvious from the label"                                            | Added a hint linked to the date input.                                                                                                                                                                                                                            |
| 16  | UI review | "I think it depends on the business"                                                                                           | Above and below typical stay on one neutral highlight; recorded as a product question.                                                                                                                                                                            |
| 17  | 6         | "follow the README exactly as written from zero"                                                                               | The fresh-clone run found two install bugs (a wrong "ready" cue, root-owned files left by the tests), both fixed.                                                                                                                                                 |
| 18  | 6         | "keep the total about the same length by tightening other sections"                                                            | Product questions and the code layout now point to PLAN.md and CLAUDE.md.                                                                                                                                                                                         |


## Reflection

## AI Tools and models used

i used Orca as the agent IDE, it helped me with the file management and the usage of Claude in the terminal integrated in the IDE.   
  
Claude Code (Claude Opus 5.5) as the coding agent: data exploration, [PLAN.md](http://PLAN.md) and README drafts, all code and tests. I reviewed every phase, made the product calls and wrote the [CLAUDE.md](http://CLAUDE.md) stack conventions, the LLM section direction and this reflection. i used the Claude skill for code review. Generally I created a customised one but since this is a small project, I didn't.   
  
Playwright for the README screenshots.