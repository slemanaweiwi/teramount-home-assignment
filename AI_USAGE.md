# AI Usage Disclosure

## 1. AI Tools

The following AI tools were used during the development of the Teramount Home Assignment.

| Tool | Model | Purpose |
|---|---|---|
| Claude Code | Claude Opus 5.5 | Assignment analysis, environment setup, data exploration, technical design, implementation planning, code development, testing, debugging, and documentation. |
| ChatGPT | — | Brainstorming possible solution approaches and independently reviewing the technical design. ChatGPT was provided with the design document only, not the original assignment. |

## 2. Development Process

AI tools were used as development assistants throughout the assignment to support problem analysis, evaluate possible approaches, accelerate implementation, and improve code quality.

### 2.1 Understanding the Assignment

Claude Code was used to inspect the original assignment document, including its text and figures, and analyze the problem, input data, expected measurements, technical requirements, and deliverables.

### 2.2 Brainstorming and Data Exploration

Different approaches to solving the problem were explored before selecting the implementation strategy.

Claude Code was used to create temporary exploration scripts that were not included in the final implementation. These scripts were used to:

- Visualize all 30 scans and identify the relevant elements.
- Experiment with potential algorithms using the actual data.
- Investigate geometric transformations and differences between datasets.
- Identify noisy elements and potential sources of measurement errors.

Several initial approaches were evaluated and rejected based on their behavior on the actual data, including projection-based rotation estimation, gradient-peak edge detection, and edge-based dome segmentation.

The reasoning behind these decisions is documented in `docs/design.md` and `ANSWERS.md`, Section 2.2.

### 2.3 Technical Design

Claude Code assisted in preparing the technical design document, covering the architecture, processing pipeline, algorithms, measurement methodology, fault detection, and validation strategy.

The design was also reviewed independently using ChatGPT. ChatGPT received only the design document and did not have access to the original assignment.

The recommendations were subsequently evaluated using Claude Code. Their acceptance or rejection was based on the assignment requirements and technical considerations.

### 2.4 Implementation Planning

Claude Code prepared a 17-task implementation plan based on the approved design.

The plan was reviewed before implementation, and development proceeded incrementally, following the agreed architecture.

### 2.5 Implementation and Testing

Claude Code assisted with implementing the solution, writing automated tests, debugging, and improving the code.

Development followed a test-first approach:

1. Write a test for the functionality being implemented.
2. Verify that the test fails when appropriate.
3. Implement the required functionality.
4. Run the relevant tests.
5. Review the implementation before proceeding to the next task.

The implementation was developed incrementally, with deviations from the original plan documented along with their reasoning.

### 2.6 Validation and Final Review

The final solution was validated through several checks:

- The complete analysis was executed on both datasets.
- All 30 diagnostic figures were inspected.
- Numerical results in `ANSWERS.md` were cross-checked against the generated CSV files.
- A fresh repository clone was used to verify execution using the README instructions.
- An independent code review was performed.
- Minor review findings were addressed individually, with tests added or updated where appropriate.
- The final generated results were compared against the previous results to verify that only the intended output columns had changed.

### 2.7 Documentation

Claude Code assisted in preparing and refining the project documentation, including:

- `README.md`
- `ANSWERS.md`
- `docs/design.md`
- `docs/implementation-plan.md`
- `results/fault_analysis.md`
- `AI_USAGE.md`

The documentation was checked against the actual implementation and generated results.

## 3. Independent Design Review

ChatGPT was used as an independent reviewer of the technical design.

It was intentionally provided with the design document only, without access to the original assignment. This allowed the design to be evaluated from a separate perspective.

The main recommendations and their outcomes were:

| Recommendation | Outcome |
|---|---|
| Strengthen segmentation using geometric relationships rather than relying only on height. | **Accepted:** A consistency check of the labeling was added. |
| Independently validate the rotation estimate. | **Accepted:** An additional validation using element positions along the channel axis was introduced. |
| Separate structural, nominal, and statistical faults. | **Accepted:** Three separate flag columns were introduced. |
| Avoid unnecessary complexity in the implementation. | **Accepted:** The Hough-only approach and bootstrap procedure were dropped. |
| Make principal curvatures the primary Xpander result. | **Not accepted:** The assignment explicitly requires radii along X and Y. Principal radii are reported as additional information. |

The final decisions were incorporated into the technical design where appropriate.

## 4. Prompts — Claude Code

The following prompts document the interactions used throughout the development of the Teramount Home Assignment, in chronological order.

### 1. Understanding the Company

Before starting the technical assignment, I would like to understand Teramount and its technology.

Please provide an overview of the company, including its core business, underlying technology, main products, and the problems its solutions are designed to address.

Focus on the technical aspects that may be relevant when approaching an engineering assignment for this company.

### 2. Understanding the Assignment

Please review the provided Teramount Home Assignment document carefully and explain the problem I am expected to solve.

I would like you to break down the assignment into the following areas:

1. **Objective:** What is the main problem the assignment aims to address?
2. **Input Data:** What data is provided, and what are its characteristics?
3. **Expected Processing:** What operations, algorithms, or measurements are required?
4. **Expected Results:** What outputs and numerical results must be produced?
5. **Technical Challenges:** What are the main engineering and computational challenges?
6. **Deliverables:** What exactly must be submitted?

Start with a clear explanation of the problem and its requirements before discussing possible implementation approaches.

Use the assignment document as the source of truth. Do not introduce assumptions or requirements that are not explicitly stated.

### 3. Preparing the Development Environment

Inspect the existing project environment and prepare it for development.

Identify the Python version and available dependencies, then determine which additional packages are necessary to implement the assignment.

Install the required dependencies using an appropriate Python environment and verify that the setup works correctly.

Keep the dependency list minimal and avoid introducing packages that are not justified by the technical requirements.

### 4. Designing the Solution

Develop a comprehensive technical design for solving the assignment.

The solution should follow professional software engineering principles, with particular attention to measurement accuracy, robustness, maintainability, and reproducibility.

Before proposing the architecture, investigate the problem systematically:

1. Examine the assignment requirements and available input data.
2. Analyze the structure, dimensions, and characteristics of the provided scans.
3. Identify the main computational challenges and potential sources of measurement error.
4. Evaluate suitable approaches for image preprocessing, segmentation, geometric measurements, surface fitting, and fault detection.
5. Consider potential edge cases and variations that may appear in unseen datasets.

Based on this investigation, propose a modular architecture that clearly separates responsibilities.

For each major component, explain:

- Its purpose and responsibilities.
- The proposed algorithm or processing approach.
- Why that approach is appropriate.
- Its expected inputs and outputs.
- Potential limitations and failure scenarios.

Also define the testing strategy, validation methodology, and expected output structure.

An important requirement is that the implementation will be evaluated using both the supplied dataset and an additional real-world dataset. Therefore, the design must generalize beyond the observed samples. Avoid hard-coded coordinates, dataset-specific assumptions, and approaches that depend on the exact characteristics of the provided scans.

### 5. Clarifying the Engineering Context

One important consideration regarding this assignment is that I am applying for a Software Engineer position, rather than a specialized research or data-science role.

Please take this into account when refining the technical design.

The solution should demonstrate that I can translate a technical problem into a reliable and maintainable software system, not simply implement algorithms that produce numerical results.

In particular, prioritize:

- Clear separation of responsibilities and modular architecture.
- Readable, maintainable, and well-structured Python code.
- Appropriate abstractions without unnecessary complexity.
- Automated testing, validation, and error handling.
- Reproducible execution and clear documentation.
- Explicit handling of assumptions and failure cases.

The mathematical methods must remain technically rigorous, but the implementation should be understandable, defensible, and appropriate for discussion in a Software Engineering technical interview.

Avoid over-engineering the solution or introducing abstractions that do not provide practical value.

### 6. Reviewing the Assignment Before Finalizing the Design

Before finalizing the technical design, perform another review against the original assignment document.

I want to ensure that the proposed architecture addresses all explicit requirements and does not overlook important constraints.

Please evaluate the design with particular attention to the fact that the implementation will be tested on both the supplied dataset and an additional real-world dataset.

Review the following:

1. **Requirement coverage:** Is every requested functionality addressed?
2. **Generalization:** Will the proposed algorithms work on data with different characteristics?
3. **Assumptions:** Which assumptions have been made, and have they been validated?
4. **Robustness:** How might the algorithms behave under noisy, incomplete, or unexpected input?
5. **Edge cases:** What scenarios could cause incorrect measurements or failures?
6. **Complexity:** Are there unnecessary components or algorithms that could be simplified?

Identify any gaps, weaknesses, or inconsistencies and recommend specific improvements.

Do not finalize the design until it has been checked against the actual assignment requirements.

### 7. Defining the Scope and Constraints

I expect to have a few days to complete this assignment, and I may need to explain the implementation and its technical decisions during a subsequent interview.

I am permitted to use AI tools and other development resources.

Please take these constraints into account when defining the implementation strategy.

The objective is to deliver a technically strong solution while keeping the development process manageable and ensuring that I understand the important engineering and algorithmic decisions.

Please distinguish between:

- Essential functionality required to satisfy the assignment.
- Improvements that significantly increase accuracy or reliability.
- Optional enhancements that are not necessary for the core solution.

Prioritize implementation tasks based on their importance, technical risk, and dependency on other components.

Avoid spending development time on unnecessary complexity that does not meaningfully improve the final result.

### 8. Reviewing the Technical Design

I used ChatGPT to obtain an independent review of the technical design. It was given the design document only and did not have access to the original assignment.

I have included its recommendations below.

Please evaluate these recommendations critically in the context of our actual assignment and implementation design.

For each recommendation:

1. Determine whether it is technically valid.
2. Check whether it is consistent with the assignment requirements.
3. Evaluate whether implementing it would improve the solution.
4. Identify any potential disadvantages or unnecessary complexity.
5. Decide whether it should be accepted, modified, or rejected.

Do not accept recommendations automatically. Explain the reasoning behind each decision and update the design only where justified.

### 9. Finalizing the Design

Please proceed with the agreed design revisions.

Update the technical design document to incorporate the recommendations that were accepted during the review.

Ensure that:

- The architecture reflects the final agreed approach.
- Identified inconsistencies are resolved.
- Rejected approaches are not included as active implementation requirements.
- The testing and validation strategy covers the important failure cases.
- The expected outputs match the assignment requirements.
- The implementation plan is consistent with the final design.

Before proceeding to implementation, perform a final consistency check across the design document, implementation plan, testing strategy, and deliverables.

### 10. Starting the Implementation

The technical design has been reviewed and approved. Proceed with implementing the solution using the agreed native implementation approach.

Follow the implementation plan and work incrementally, completing one task at a time.

For each task:

1. Implement the functionality according to the agreed architecture.
2. Write or update the relevant automated tests.
3. Run the tests and investigate any failures.
4. Verify that the implementation behaves correctly on the relevant input data.
5. Review the implementation for correctness, readability, and maintainability before moving to the next task.

Follow a test-first development approach wherever practical. Avoid shortcuts, unnecessary dependencies, and changes that compromise the architecture or measurement accuracy.

Keep the implementation plan updated as work progresses, documenting any deviations and the reasons behind them.

Also provide an estimated development timeline, including the major milestones and remaining tasks.

### 11. Requesting an Implementation Progress Update

Please provide a progress update on the implementation.

Include:

- Tasks completed successfully.
- Tasks currently in progress.
- Remaining tasks from the implementation plan.
- Outstanding technical issues or blockers.
- Any deviations from the original plan and their justification.
- An updated estimate of the remaining development time.

Base the update on the actual project state rather than the original estimated timeline.

### 12. Requesting a Code Review Progress Update

Please provide an update on the independent code review.

Summarize the current review status, including:

- The total number of issues identified.
- The number of issues resolved.
- The number of issues still outstanding.
- The severity and general nature of the remaining findings.
- Any components that have not yet been reviewed.
- The estimated time required to complete the review.

Distinguish between confirmed issues, potential improvements, and observations that do not require changes.

### 13. Preparing the AI Usage Documentation

I need to prepare an AI usage disclosure as part of the assignment submission.

Please create a professional and transparent `AI_USAGE.md` document describing how AI tools were used throughout the development process.

The document should cover the actual contributions of Claude Code, including:

- Understanding and analyzing the assignment.
- Exploring the provided datasets.
- Evaluating technical approaches.
- Preparing the design document and implementation plan.
- Implementing the solution and automated tests.
- Debugging and validating the results.
- Preparing the documentation and final deliverables.

Also document the use of ChatGPT for brainstorming and independently reviewing the technical design.

Include the prompts used during the development process in a professional, well-structured format.

Do not invent technical decisions or claim that suggestions were implemented unless they were actually accepted and used.

Clearly distinguish between suggestions that were accepted, rejected, or modified.

The final document should accurately represent the AI-assisted development process and provide a clear account of the tools, activities, and engineering decisions involved.

---

## 5. Transparency Statement

AI tools were used throughout the development process to support assignment analysis, technical design, data exploration, implementation, testing, debugging, and documentation.

Claude Code was the primary AI-assisted development tool, while ChatGPT was used for brainstorming and an independent review of the technical design.

Technical recommendations were evaluated against the assignment requirements and actual data rather than accepted automatically. The final implementation and its results were validated through automated tests, execution on the available datasets, inspection of diagnostic outputs, and an independent code review.
