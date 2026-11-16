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
   and by ChatGPT (below), then approved by me.
4. **Plan.** Claude Code wrote a 17-task implementation plan, which I
   approved.
5. **Implementation.** Each task was built test-first: write a failing test,
   implement, pass, commit. Deviations from the plan were logged with their
   reasons. The 30 real scans were used for validation at each step.
6. **Validation and answers.**
   - The full analysis was run on both datasets.
   - All 30 diagnostic figures were inspected.
   - Every number in `ANSWERS.md` was cross-checked against the CSVs.
   - A fresh clone of the repository was run from the README instructions.
   - A final independent code review was done.
7. **Final polish.** At my request, the ten minor findings the
   reviewer had left for later were addressed, each test-first. Nine were
   fixed; one did not reproduce and got a regression test instead. The results
   were then regenerated and compared cell by cell with the previous ones:
   only the intended columns changed.

### ChatGPT's design review and what was done with it

ChatGPT made five main recommendations. I passed them to Claude
Code (prompt 8 below), and Claude assessed each one; the outcome is recorded
in `docs/design.md` §12:

| Recommendation | Outcome |
|---|---|
| Strengthen segmentation with geometric relationships, not height alone | **Accepted:** a consistency check of the labeling was added. |
| Validate the rotation estimate | **Accepted:** an independent check via the element positions on the channel axis. |
| Separate structural, nominal and statistical faults | **Accepted:** three separate flag columns. |
| Avoid over-engineering | **Accepted:** dropped the Hough-only route and the bootstrap. |
| Make the principal curvatures the main Xpander result | **Not accepted:** the assignment explicitly asks for the radius along X and Y. Principal radii are reported as an extra. |

## Prompts

Every prompt I sent, exactly as I typed it (typos included), in the order I
sent them. Times are UTC. Three long pasted texts are shortened and marked
[...]: ChatGPT's design review (summarised above), Teramount's reply about
the test data, and the review prompt (prompt 37), which ran in a separate
Claude Code session as a final independent check before submission. One
message meant for an unrelated project is left out.

**1.** 15 Nov, 13:33

```text
hi , do you know teramount ?
```

**2.** 15 Nov, 13:37

```text
yes read the assismint and tell me what is this assigmint please
```

**3.** 15 Nov, 13:44

```text
for now install the required stuff
```

**4.** 15 Nov, 13:49

```text
yes do the design , this i want this to be profiistional and you do you maximum to give the best resutls please
```

**5.** 15 Nov, 13:51

```text
idk , iam applying for a software enginner position
```

**6.** 15 Nov, 13:51

```text
yes but read the doc first to understand what they are asking for , the code will be tested on this data set and real data set
```

**7.** 15 Nov, 14:13

```text
a few days, maybe i need to explain it idk why ? but i can use ai to solve it and use what ever i want
```

**8.** 15 Nov, 14:27

```text
i used chat gpt to review the design , he wrote me this iwhile brainstorming , 

[pasted: ChatGPT's review of the design, summarised in the table above]

 , what do you think about what he sees ? notice that chatgpt dies not have the assigmn he has only the design
```

**9.** 15 Nov, 14:32

```text
yes do it
```

**10.** 15 Nov, 15:40

```text
yes go with native, start building ,how much will it take ??
```

**11.** 15 Nov, 16:22

```text
how much you will take ??
```

**12.** 15 Nov, 17:06

```text
how much time left until the review finishes?
```

**13.** 15 Nov, 17:08

```text
use the promts and inhence them to look profisinal , i used chat gpt to brain storm how to solve the problem
```

**14.** 15 Nov, 17:12

```text
https://chatgpt.com/share/6af9e79d-72d0-83eb-8888-6beb5caa7c44, but i as i told you write the promts in more profinsinla way
```

**15.** 15 Nov, 21:36

```text
so now what , is the assigmnt done ? where are we now
```

**16.** 15 Nov, 21:42

```text
merge and make a github repo , and do the small fixes take your time i want the perfect assigmint
```

**17.** 15 Nov, 23:00

```text
the ai usage md i changed it and saved it notice that
```

**18.** 15 Nov, 23:18

```text
we are done now ?
```

**19.** 15 Nov, 23:19

```text
i stoped it by accedent continue
```

**20.** 15 Nov, 23:21

```text
make it public
```

**21.** 15 Nov, 23:23

```text
all the tests are passed , is the code gonna work on future tests that we dont have now ? are you 100% sure we are done ?
```

**22.** 15 Nov, 23:27

```text
i edited the ai usage my self  . also i recieved a main from vercel about a web page deploy what is that ??
```

**23.** 15 Nov, 23:29

```text
edit ai usage such that it has no errors
```

**24.** 15 Nov, 23:35

```text
now its the last result , iedit it , dont add anything to it
```

**25.** 15 Nov, 23:49

```text
you reccomend us doing these fixes ? are there any failed tests or this fix is just in case , i dont want to optamize my solution and reuining what we did before
```

**26.** 15 Nov, 23:52

```text
we can ask the hairing manger about that what do you think ??
```

**27.** 15 Nov, 23:55

```text
no lest do other thing , lets write them a mail  that we finished the assigment , and in that mail we would ask if the quastions that we would sent before , and tell them we are finshed imliminting the assigment but if there ansewer is yes i would make some fixes regarfing that
```

**28.** 15 Nov, 23:58

```text
my name is suleiman 
and i should sent the mail to Nermeen and Amit and  Elad
```

**29.** 16 Nov, 00:00

```text
can you do an atrifact that eplains every thing that we did and also prepers me for the interview , also is there a way to scedule that mail in the 8:00 am in the morning ?
```

**30.** 16 Nov, 00:05

```text
for the mail i want you to ask the quastion first then to show the git hub that we finished
```

**31.** 16 Nov, 00:08

```text
wher is the mail ?
```

**32.** 16 Nov, 00:13

```text
no still the mail , you should say if not  ,the assigmint is ready , if yes i will make some changes to deal with the expected tests
```

**33.** 16 Nov, 00:17

```text
do you recommend adding ana artifact exaplinig our solution to the reviewer or no ?
```

**34.** 16 Nov, 09:36

```text
i got this mail back 


[pasted: Teramount's reply about the test data]
```

**35.** 16 Nov, 09:41

```text
yes
```

**36.** 16 Nov, 12:40

```text
no , are we done now can i submit it ?
```

**37.** 16 Nov, 12:50

```text
# Assignment Review — Senior Software Engineer & Technical Evaluator

You are acting as a **Senior Software Engineer, Code Reviewer, and Technical Assignment Evaluator**.

Your task is to thoroughly review my assignment as if you were evaluating it for submission to a university, technical interviewer, or professional engineering team.

Your goal is to determine whether the assignment is correct, complete, well-implemented, properly tested, cleanly written, and ready for submission.

## CRITICAL RULES

1. **DO NOT MODIFY ANYTHING.** [...]
2. This is a REVIEW-ONLY task. Your only responsibility is to inspect, analyze, test, and report.
3. Do not assume the assignment is correct just because it runs. [...]
4. Be honest and critical. [...]
5. Do not invent problems. [...]
6. Do not claim that tests passed unless you actually executed them or verified their results.

[... PHASE 1 — Understand the assignment; PHASE 2 — Review the entire implementation;
PHASE 3 — Review and execute the tests; PHASE 4 — Review test coverage and quality;
PHASE 5 — Review documentation; PHASE 6 — Assignment requirements checklist;
PHASE 7 — Final evaluation; PHASE 8 — Generate a complete review report ...]
```

**38.** 16 Nov, 14:43

```text
put it in an md file , and change the ai-usage such that i wrote those quastions not somoeelse okay ??
```

**39.** 16 Nov, 14:46

```text
what do you think about the temount report ??
```

**40.** 16 Nov, 14:47

```text
no this report \Users\LENOVO\Downloads\Teramount_Review_Report.md.
```

**41.** 16 Nov, 14:50

```text
1 i fixed can you check ?? it nows has real promts not the candidates said .. 
2 - do you think we should do this work in order to pass the tests ??
```

**42.** 16 Nov, 14:54

```text
yes , and also change the ai usage to only have the promts not the candiate and also add this final test promt that discovered the last 2 bugs , 

[pasted: the review prompt above]

 but dont use it all use some of itt ,,
after that do the fixes and make sure the results are the same and edit the required data
```

## Prompts — ChatGPT

My ChatGPT conversation (brainstorming and the design review), with every
prompt and reply:

**https://chatgpt.com/share/6af9e79d-72d0-83eb-8888-6beb5caa7c44**
