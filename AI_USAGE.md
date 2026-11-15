# AI usage

The assignment allows AI tools if they are named and the prompts are
included. This file lists both tools used, what each did, and the prompts
verbatim (typos included).

## Tools

| Tool | Model | Used for |
|---|---|---|
| **Claude Code** (Anthropic CLI agent) | Claude Opus 5.5 | Explaining the assignment; installing the Python packages; exploring the data with throwaway scripts; the design document (`docs/design.md`) and implementation plan (`docs/implementation-plan.md`); writing the code and tests (test-first, one task at a time); running the analysis; drafting `README.md`, `ANSWERS.md`, `results/fault_analysis.md` and this file. |
| **ChatGPT** (OpenAI) | — | An independent review of the design document. ChatGPT saw only the design, not the assignment. |

## How the work was done

1. **Understanding.** Claude read the assignment (`.docx`, text and figures)
   and summarised it.
2. **Data exploration.** Throwaway scripts that were not kept were used to:
   - plot all 30 scans and locate the elements;
   - prototype each risky algorithm step on the real data;
   - discover that dataset 2 is dataset 1 rotated and tilted;
   - find the planted noisy elements.

   Several first ideas were rejected on evidence: a projection-based rotation
   estimate, gradient-peak edge location, and edge-based dome segmentation.
   The reasons are in `docs/design.md` and `ANSWERS.md` §2.2.
3. **Design.** The design document was checked by a separate reviewer agent
   and by ChatGPT (below), then approved by the candidate.
4. **Plan.** A 17-task implementation plan was written and approved by the
   candidate.
5. **Implementation.** Each task was built test-first: write a failing test,
   implement, pass, commit. Deviations from the plan were logged with their
   reasons. The 30 real scans were used for validation at each step.
6. **Validation and answers.**
   - The full analysis was run on both datasets.
   - All 30 diagnostic figures were inspected.
   - Every number in `ANSWERS.md` was cross-checked against the CSVs.

### ChatGPT's design review and what was done with it

ChatGPT made five main recommendations. The candidate passed them to Claude
Code (prompt 8 below), and Claude assessed each one; the outcome is recorded
in `docs/design.md` §12:

| Recommendation | Outcome |
|---|---|
| Strengthen segmentation with geometric relationships, not height alone | **Accepted:** a consistency check of the labeling was added. |
| Validate the rotation estimate | **Accepted:** an independent check via the element positions on the channel axis. |
| Separate structural, nominal and statistical faults | **Accepted:** three separate flag columns. |
| Avoid over-engineering | **Accepted:** dropped the Hough-only route and the bootstrap. |
| Make the principal curvatures the main Xpander result | **Not accepted:** the assignment explicitly asks for the radius along X and Y. Principal radii are reported as an extra. |

## Prompts — Claude Code

All prompts typed by the candidate in the Claude Code session, in order. Times
are UTC, 15 Nov 2026.

1. *13:33* — `hi , do you know teramount ?`
2. *13:37* — `yes read the assismint and tell me what is this assigmint please`
3. *13:44* — `for now install the required stuff`
4. *13:49* — `yes do the design , this i want this to be profiistional and you do you maximum to give the best resutls please`
5. *13:51* — `idk , iam applying for a software enginner position`
6. *13:51* — `yes but read the doc first to understand what they are asking for , the code will be tested on this data set and real data set`
7. *14:13* — `a few days, maybe i need to explain it idk why ? but i can use ai to solve it and use what ever i want`
8. *14:27* — `i used chat gpt to review the design , he wrote me this iwhile brainstorming , [pasted: ChatGPT's full review of docs/design.md — summarised in the table above] , what do you think about what he sees ? notice that chatgpt dies not have the assigmn he has only the design`
9. *14:32* — `yes do it` (approving the updated design)
10. *15:40* — `yes go with native, start building ,how much will it take ??`
11. *16:23* — `how much you will take ??`

## Prompts — ChatGPT

> **TODO (candidate):** paste here the messages you sent to ChatGPT for the
> design review. For example: the request to review the design and the
> design text you gave it.
