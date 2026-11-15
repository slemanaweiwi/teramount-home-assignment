# AI usage

The assignment allows AI tools if they are named and the prompts are
included. This file lists the tools, what each was used for, and every
prompt.

## Tools

| Tool | Model | Used for |
|---|---|---|
| **Claude Code** (Anthropic CLI agent) | Claude Opus 5.5 | Explaining the assignment; installing the Python packages; exploring the data with throwaway scripts; the design document (`docs/design.md`) and implementation plan (`docs/implementation-plan.md`); writing the code and tests (test-first, one task at a time); running the analysis; drafting `README.md`, `ANSWERS.md`, `results/fault_analysis.md` and this file. |
| **ChatGPT** (OpenAI) | — | Brainstorming how to approach the problem, and an independent review of the design document. For the review it was given only the design, not the assignment. |

## How the work was done

1. **Understanding.** Claude read the assignment (`.docx`, text and figures)
   and summarised it.
2. **Brainstorming and data exploration.** Solution approaches were
   brainstormed with ChatGPT. With Claude Code, throwaway scripts that were
   not kept were used to:
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
   - A fresh clone of the repository was run from the README instructions.
   - A final independent code review was done.

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

All prompts typed by the candidate in the Claude Code session, in order.
Times are UTC on 15 Nov 2026.

- The **prompt** column is the exact text, typos included, because the
  assignment asks for the prompts that were actually used.
- The **request** column states each one in plain terms.

| # | Time | Prompt (exact text) | Request |
|---|---|---|---|
| 1 | 13:33 | `hi , do you know teramount ?` | Background on Teramount and its technology. |
| 2 | 13:37 | `yes read the assismint and tell me what is this assigmint please` | Read the assignment document and summarise the task. |
| 3 | 13:44 | `for now install the required stuff` | Set up the Python environment and dependencies. |
| 4 | 13:49 | `yes do the design , this i want this to be profiistional and you do you maximum to give the best resutls please` | Produce a professional design aimed at the best possible results. |
| 5 | 13:51 | `idk , iam applying for a software enginner position` | Context: the role applied for is software engineer. |
| 6 | 13:51 | `yes but read the doc first to understand what they are asking for , the code will be tested on this data set and real data set` | Base everything on the assignment's requirements. The code must also work on an unseen dataset. |
| 7 | 14:13 | `a few days, maybe i need to explain it idk why ? but i can use ai to solve it and use what ever i want` | Constraints: a few days available, the solution may have to be explained, and any tools are allowed. |
| 8 | 14:27 | `i used chat gpt to review the design , he wrote me this iwhile brainstorming , [pasted: ChatGPT's full review of docs/design.md — summarised in the table above] , what do you think about what he sees ? notice that chatgpt dies not have the assigmn he has only the design` | Evaluate ChatGPT's independent review of the design, which it made without seeing the assignment. |
| 9 | 14:32 | `yes do it` | Approve the revised design and proceed to the implementation plan. |
| 10 | 15:40 | `yes go with native, start building ,how much will it take ??` | Approve the plan, build it in this session, and estimate the time. |
| 11 | 16:23 | `how much you will take ??` | Ask for a time estimate. |
| 12 | 17:06 | `how much time left until the review finishes?` | Ask for the status of the final code review. |
| 13 | 17:08 | `use the promts and inhence them to look profisinal , i used chat gpt to brain storm how to solve the problem` | Improve the presentation of this file, and record that ChatGPT was also used for brainstorming. |

## Prompts — ChatGPT

> **To add (candidate):** the messages sent to ChatGPT, exactly as typed, for
> both the brainstorming and the design review. The simplest way: in ChatGPT
> open the conversation, click **Share**, and paste the link here. Or copy
> the messages below.
