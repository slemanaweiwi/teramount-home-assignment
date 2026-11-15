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

The following prompts represent the instructions provided to Claude Code throughout the development of the Teramount Home Assignment. They have been professionally edited for clarity, structure, and technical precision while preserving the intent and sequence of the original interactions.

### 1. Understanding the Company

**Prompt:**

Are you familiar with Teramount? Please briefly explain the company's business, its core technology, and the products or solutions it develops. I would like to understand the context of the company before starting its technical assignment.

### 2. Understanding the Assignment

**Prompt:**

Please review the provided Teramount Home Assignment document carefully and explain its objectives in detail.

I want to understand:
- What the assignment expects me to implement.
- What input data is provided.
- What measurements and results must be extracted.
- What challenges the assignment is designed to evaluate.
- What the expected deliverables are.

Start by explaining the problem in accessible language before suggesting an implementation approach. Do not make assumptions about requirements that are not stated in the assignment.

### 3. Preparing the Development Environment

**Prompt:**

Before proceeding with the implementation, please inspect the project environment and install the dependencies required for the assignment.

Use an appropriate Python environment, select suitable scientific-computing and image-processing libraries, and verify that the installation works. Please avoid introducing unnecessary dependencies.

### 4. Designing the Solution

**Prompt:**

Please develop a comprehensive technical design for solving this assignment.

The solution should demonstrate professional software engineering practices and prioritize measurement accuracy, robustness, maintainability, and reproducibility.

Before proposing the architecture:
1. Inspect the assignment and all available input data.
2. Explore the structure and characteristics of the scans.
3. Identify the main technical challenges and potential failure cases.
4. Evaluate suitable algorithms for segmentation, geometric measurements, surface fitting, and fault detection.

Then propose a modular architecture, explain the reasoning behind the major algorithmic choices, define the expected outputs, and establish a testing and validation strategy.

The implementation will be evaluated on the provided dataset and an additional real-world dataset. Therefore, avoid hard-coded coordinates, file-specific assumptions, and solutions that only work on the current samples.

### 5. Clarifying the Engineering Context

**Prompt:**

I am applying for a Software Engineer position, rather than a dedicated research or data-science position.

Please take this into account when designing the solution. I want the implementation to demonstrate strong engineering practices, not simply produce accurate numerical results.

Prioritize:
- Clean and modular architecture.
- Readable, maintainable Python code.
- Appropriate abstractions and separation of responsibilities.
- Automated testing and error handling.
- Reproducible execution and clear documentation.

The mathematical methods should still be rigorous, but their implementation and justification should be understandable and defensible in a software engineering interview.

### 6. Reviewing the Assignment Before Finalizing the Design

**Prompt:**

Before finalizing the design, please return to the original assignment document and verify that the proposed solution addresses every requirement.

The implementation will be tested against both the supplied dataset and an additional real dataset. This means the design must generalize beyond the observed scans.

Please identify:
- Requirements that are not yet covered.
- Assumptions that need validation.
- Algorithms that may fail under different scan conditions.
- Potential edge cases.
- Any unnecessary complexity that could be removed without compromising the solution.

Do not finalize the design until you have checked it against the actual assignment requirements.

### 7. Defining the Scope and Constraints

**Prompt:**

I expect to have a few days to complete the assignment. I may also be asked to explain and justify the implementation during a technical interview.

I am permitted to use AI tools and other development resources.

Please optimize the implementation strategy for this situation. The final result should be technically strong, but I also need to understand the important decisions well enough to explain them independently.

Prioritize the essential requirements first and distinguish between must-have functionality and optional improvements.

### 8. Finalizing the Design

**Prompt:**

Please proceed with the agreed design revisions.

Update the design documentation to incorporate the accepted recommendations, resolve the identified inconsistencies, and ensure that the implementation plan is consistent with the final architecture.

Before implementation, verify that the design, testing strategy, and deliverables are aligned.

### 9. Starting the Implementation

**Prompt:**

The design is approved. Please proceed with the native implementation approach and build the complete solution in the current project.

Follow the agreed implementation plan and work incrementally.

For each task:
1. Implement the functionality.
2. Add or update the relevant automated tests.
3. Run the tests and investigate any failures.
4. Review the implementation before moving to the next task.

Preserve the modular architecture and avoid shortcuts that compromise correctness or maintainability.

Please also provide an estimate of the implementation time and identify the major remaining milestones.

### 10. Requesting an Implementation Progress Update

**Prompt:**

Please provide an updated estimate of the remaining implementation time.

Summarize the completed tasks, the work currently in progress, the outstanding tasks, and any issues that could affect the delivery timeline.

### 11. Requesting a Review Progress Update

**Prompt:**

Please provide an update on the independent code review.

How many issues have been identified, how many have been resolved, and what remains to be reviewed? Also, estimate how much time is needed to complete the review.

### 12. Improving the AI Usage Documentation

**Prompt:**

I need to document my use of AI tools as part of the assignment submission.

Please prepare a professional and transparent AI usage section for `AI_USAGE.md`.

The documentation should describe how Claude Code contributed to the development process, including data exploration, technical design, implementation, testing, debugging, and documentation.

Please present the prompts used during the interactions in a professional, well-structured format. Do not invent technical decisions or claim that suggestions were implemented unless they were actually accepted and used.

---



</details>
