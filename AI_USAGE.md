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

All prompts the candidate sent in the Claude Code session, in order. Times are
UTC on 15 Nov 2026.

The prompts below are **edited for spelling, grammar and clarity**; their
meaning is unchanged. The exact original wording is at the end of this file.

| # | Time | Prompt |
|---|---|---|
| 1 | 13:33 | Hi, are you familiar with Teramount? |
| 2 | 13:37 | Yes. Please read the assignment and explain what it asks for. |
| 3 | 13:44 | For now, please install the required dependencies. |
| 4 | 13:49 | Yes, please create the design. I want it to be professional, so please do your best to achieve the best possible results. |
| 5 | 13:51 | I'm not sure. I'm applying for a software engineer position. |
| 6 | 13:51 | Yes, but first read the assignment document to understand what is being asked. The code will be tested on this dataset and on an additional real dataset. |
| 7 | 14:13 | A few days. I may need to explain the solution, though I'm not sure why. I'm allowed to use AI and any tools I want. |
| 8 | 14:27 | I used ChatGPT to review the design while brainstorming; its review is below. What do you think of its feedback? Note that ChatGPT did not have the assignment, only the design. *[ChatGPT's full review of `docs/design.md` was pasted here; it is summarised in the table above.]* |
| 9 | 14:32 | Yes, go ahead. |
| 10 | 15:40 | Yes, use native execution and start building. How long will it take? |
| 11 | 16:23 | How long will it take? |
| 12 | 17:06 | How much time is left until the review finishes? |
| 13 | 17:08 | Please present the prompts more professionally. Also, I used ChatGPT to brainstorm how to solve the problem. |
| 14 | 17:12 | Here is the link to the ChatGPT conversation. As I said, please write the prompts in a more professional way. |

## Prompts — ChatGPT

The full ChatGPT conversation (brainstorming and design review), with every
prompt and reply:

**https://chatgpt.com/share/6af9e79d-72d0-83eb-8888-6beb5caa7c44**

<details>
<summary>Original wording of the Claude Code prompts (exact text, typos included)</summary>

| # | Prompt (exact text) |
|---|---|
| 1 | `hi , do you know teramount ?` |
| 2 | `yes read the assismint and tell me what is this assigmint please` |
| 3 | `for now install the required stuff` |
| 4 | `yes do the design , this i want this to be profiistional and you do you maximum to give the best resutls please` |
| 5 | `idk , iam applying for a software enginner position` |
| 6 | `yes but read the doc first to understand what they are asking for , the code will be tested on this data set and real data set` |
| 7 | `a few days, maybe i need to explain it idk why ? but i can use ai to solve it and use what ever i want` |
| 8 | `i used chat gpt to review the design , he wrote me this iwhile brainstorming , [pasted ChatGPT review] , what do you think about what he sees ? notice that chatgpt dies not have the assigmn he has only the design` |
| 9 | `yes do it` |
| 10 | `yes go with native, start building ,how much will it take ??` |
| 11 | `how much you will take ??` |
| 12 | `how much time left until the review finishes?` |
| 13 | `use the promts and inhence them to look profisinal , i used chat gpt to brain storm how to solve the problem` |
| 14 | `https://chatgpt.com/share/6af9e79d-72d0-83eb-8888-6beb5caa7c44, but i as i told you write the promts in more profinsinla way` |

</details>
