# Learner B2

- Round: **round2**
- Group: **G1 - Product Management Internship**
- Learner: `learner-b2@example.invalid` (`10cafecf-ab1c-438d-b979-4a56be2714fd`)

---

## LX `0a020631-d910-4f51-884a-e13dcc74bdf5`

- flow: `flow0` · archetype: `single_submission`
- status: **terminated** · outcome: **expired**
- activated: 2026-07-29T09:05:57.137398+00:00
- log entries: 5

#### 2026-07-29T09:12:54.026Z  ·  `trig_timer_reminder`
*tags: deadline_reminder, actor_response*
> Sent friendly deadline reminder for Product Sprint 3 deliverables and invited submission or blockers.
- **mentor → learner:** Checking in as we reach the deadline today for your Product Sprint 3 deliverables. How are the interactive AI prototype, 1-page PRD, and sprint board setup coming along, or did you hit any final blockers? Once you're ready, feel free to send everything directly in our chat as a file attachment, link, or inline text.

#### 2026-07-29T09:13:00.556Z  ·  `trig_timer_deadline`
*tags: deadline_extended, actor_response*
> Original deadline reached without a passing submission. Manager granted a one-time 48h extension; new deadline 2026-07-31T09:13:00.556Z.
- **manager → learner:** Hi Learner B2, the deadline passed without a passing submission. A one-time 48-hour extension has been applied. Your new deadline is Friday, July 31, 2026, at 12:13 PM Cairo time. No further extensions will be granted, so focus on submitting a version that meets the required standard before this deadline.
<details><summary>scenario_events</summary>

```json
[
  {
    "at": "2026-07-29T09:13:00.556Z",
    "kind": "deadline_extended",
    "new_deadline": "2026-07-31T09:13:00.556Z"
  }
]
```
</details>

#### 2026-07-29T09:13:23.756Z  ·  `trig_timer_brief`
*tags: task_kickoff, actor_response*
> Delivered Product Sprint 3 initial task brief and expectations.
- **manager → learner:** You are assigned to Product Sprint 3: Interactive AI-feature Prototype + 1-Page PRD + User Stories & Acceptance Criteria + Sprint Board + Technical Integration Note. Your objective is to translate the AI capability scoped in Sprint 1 into a complete, interactive, and shippable feature package for Sprints.ai.
  
  Scope of Work:
  1. Interactive AI Prototype: Build a high-fidelity, production-quality prototype using an AI prototyping tool (such as Lovable or v0). It must cover the core interaction flow end-to-end, maintain a consistent visual design system, include all real UI states (loading, empty, error, success), and be accessible via a public shareable link.
  2. 1-Page PRD: Single-page document covering all 7 required sections—Problem, Primary User, Goals, In Scope, Out of Scope (non-goals), Technical/Business Constraints (explicitly addressing AI/model constraints: cost, latency, accuracy, data availability), and at least 3 Open Questions.
  3. User Stories & Acceptance Criteria: 5–8 user stories in standard "As a / I want to / So that" format based on your Sprint 1 persona. Each story must include at least 2 Given/When/Then acceptance criteria covering edge cases (API call failures/timeouts, missing data/context, mobile access).
  4. Sprint Board Setup: Configure epics, user stories, tasks, and a clear sprint goal in a project management tool. Include a board screenshot and a brief walkthrough.
  5. Technical Integration Note: A single-page technical sketch illustrating how the AI feature connects across Sprints.ai's frontend, backend, data layer, and AI/model layer (prompt design, API, or fine-tuning approach).
  
  Required Deliverables:
  - Public, clickable link to the hi-fi AI prototype
  - 1-Page PRD document
  - User Stories and Acceptance Criteria document
  - Sprint Board screenshot and walkthrough
  - 1-Page Technical Integration Note
  
  Assets and Templates:
  No external assets or template links are provided for this assignment.
  
  Deadline:
  Friday, July 31, 2026, at 12:13 PM Cairo time.
  
  Quality Standards:
  The submission package must be production-ready. Low-fidelity wireframes, missing UI states, incomplete PRD sections, or happy-path-only user stories fail to meet executive standards and will be rejected.
  
  Workflow and Routing:
  - Submit your final deliverables directly to your mentor for formal evaluation before the deadline.
  - Route technical questions, architectural queries, and draft feedback to your mentor.
  - Direct program, administrative, operational, or platform access issues to the internship group admins through the official team channel.

#### 2026-07-29T09:14:15.855Z  ·  `trig_timer_brief`
*tags: task_kickoff, actor_response*
> Delivered the full Product Sprint 3 task brief with required scope, deliverables, deadline, standards, and support routing.
- **manager → learner:** Hi,
  
  You are assigned to Product Sprint 3. Your task is to translate the AI capability scoped in Sprint 1 into an interactive, production-quality feature prototype and a complete product execution package for Sprints.ai.
  
  What You Must Build:
  1. Interactive AI Prototype: A high-fidelity, production-quality prototype built using an AI tool (such as Lovable or v0). It must cover the full core interaction flow, maintain a consistent visual design system, include all real UI states (loading, empty, error, success), and be accessible via a public shareable link.
  2. 1-Page PRD: A single-page specification covering all 7 required sections: Problem, Primary User, Goals, In Scope, Out of Scope, Technical/Business Constraints (explicitly detailing AI/model constraints: cost, latency, accuracy, data availability), and at least 3 Open Questions.
  3. User Stories & Acceptance Criteria: 5 to 8 user stories in standard "As a / I want to / So that" format based on your Sprint 1 persona. Each story must include at least 2 Given/When/Then acceptance criteria, with edge cases explicitly covered.
  4. Sprint Board Setup: Epics, stories, tasks, and sprint goal configured in a project management tool, documented via a board screenshot and short walkthrough.
  5. Technical Integration Note: A 1-page technical sketch mapping how the AI feature connects across frontend, backend, data layer, and AI/model layer.
  
  Required Deliverables:
  - Public clickable link to the hi-fi AI prototype
  - 1-Page PRD document
  - User Stories & Acceptance Criteria document
  - Sprint Board screenshot and walkthrough
  - 1-Page Technical Integration Note
  
  Assets and Links:
  No external assets or template links are provided for this task.
  
  Deadline:
  Friday, July 31, 2026, at 12:13 PM Cairo time. I expect this by the deadline.
  
  Success Standard:
  All deliverables must be complete and executive-ready. Wireframes, missing UI states, incomplete PRD sections, or happy-path-only user stories fail to meet required standards and will be rejected.
  
  Support Routing:
  - Submit your completed package directly to your mentor for evaluation before the deadline.
  - Direct all technical questions, architectural clarifications, and draft feedback to your mentor.
  - Direct operational, administrative, or platform access issues to the internship group admins through the official team channel.

#### 2026-07-29T09:14:27.633000+00:00  ·  `trig_human_mentor_msg`
*tags: human_mentor_message*
> Human mentor (via the manager account) messaged the learner directly: Hi,
You are assigned to Product Sprint 3. Your task is to translate the AI capability scoped in Sprint 1 into an interactive, production-quality feature prototype and a complete product execution pack
- **human_mentor → learner:** Hi,
  You are assigned to Product Sprint 3. Your task is to translate the AI capability scoped in Sprint 1 into an interactive, production-quality feature prototype and a complete product execution package for Sprints.ai.
  What You Must Build:
  Interactive AI Prototype: A high-fidelity, production-quality prototype built using an AI tool (such as Lovable or v0). It must cover the full core interaction flow, maintain a consistent visual design system, include all real UI states (loading, empty, error, success), and be accessible via a public shareable link.
  1-Page PRD: A single-page specification covering all 7 required sections: Problem, Primary User, Goals, In Scope, Out of Scope, Technical/Business Constraints (explicitly detailing AI/model constraints: cost, latency, accuracy, data availability), and at least 3 Open Questions.
  User Stories & Acceptance Criteria: 5 to 8 user stories in standard "As a / I want to / So that" format based on your Sprint 1 persona. Each story must include at least 2 Given/When/Then acceptance criteria, with edge cases explicitly covered.
  Sprint Board Setup: Epics, stories, tasks, and sprint goal configured in a project management tool, documented via a board screenshot and short walkthrough.
  Technical Integration Note: A 1-page technical sketch mapping how the AI feature connects across frontend, backend, data layer, and AI/model layer.
  Required Deliverables:
  Public clickable link to the hi-fi AI prototype
  1-Page PRD document
  User Stories & Acceptance Criteria document
  Sprint Board screenshot and walkthrough
  1-Page Technical Integration Note
  Assets and Links:
  No external assets or template links are provided for this task.
  Deadline:
  Friday, July 31, 2026, at 12:13 PM Cairo time. I expect this by the deadline.
  Success Standard:
  All deliverables must be complete and executive-ready. Wireframes, missing UI states, incomplete PRD sections, or happy-path-only user stories fail to meet required standards and will be rejected.
  Support Routing:
  Submit your completed package directly to your mentor for evaluation before the deadline.
  Direct all technical questions, architectural clarifications, and draft feedback to your mentor.
  Direct operational, administrative, or platform access issues to the internship group admins through the official team channel.

---

## LX `28fe75c4-1eb2-401f-bc3f-ffff5142c611`

- flow: `flow0` · archetype: `single_submission`
- status: **terminated** · outcome: **expired**
- activated: 2026-08-03T09:05:24.108019+00:00
- log entries: 8

#### 2026-08-03T09:06:00.859Z  ·  `trig_timer_brief`
*tags: task_kickoff, actor_response*
> Delivered the initial kickoff brief for Sprint 4 task requirements, deliverables, deadline, and routing instructions.
- **manager → learner:** Learner B2, your task for Sprint 4 is now active: GTM Plan, Launch Checklist, A/B Experiment, Metrics Dashboard & Final Demo Day.
  
  Context & Scope:
  Prepare the product for go-live and present the complete end-to-end product journey. Your work must build directly on your completed artifacts from Sprints 1, 2, and 3.
  
  Required Build:
  1. Go-To-Market (GTM) Plan: Define your target segment with prioritization logic, research-grounded messaging, at least two distribution channels, rollout phases (Beta, Staged, Full) with quantitative exit triggers, and a launch timeline.
  2. Launch Checklist: Create a checklist with a minimum of 10 items spanning pre-launch, launch day, and post-launch. Assign ownership strictly by role title and include quantitative rollback or pause triggers.
  3. A/B Experiment Design: Design one A/B experiment for your riskiest assumption using the format 'If change X, then metric Y moves Z because W' tied to your Sprint 2 Metric Tree. Specify control/variant, minimum sample size, run duration, and a pre-mortem with failure modes and corrective actions.
  4. Metrics Dashboard Mockup: Track at least 5 metrics from your Sprint 2 Metric Tree, detailing definition, tracking cadence, role owner, and action triggers for underperformance.
  5. Final Demo Day Deck: Develop a presentation deck covering the full four-week product narrative arc and explicit trade-offs made.
  
  Deliverables & Assets:
  Submit strategy and launch documentation, checklist, experiment brief, dashboard mockup, and presentation deck. No external assets are provided; align strictly with your prior sprint artifacts.
  
  Deadline:
  The final deadline for submission is Thursday, August 6, 2026, at 11:59 PM Cairo time.
  
  Evaluation & Support Routing:
  Evaluation will focus on completeness, logical alignment across all four sprints, role-based governance, and quantitative thresholds. Technical guidance and draft feedback must be directed to your mentor, to whom you will submit your final work. Direct platform access or administrative issues to the internship team group mentioning the group admins.
  
  Review these requirements and proceed immediately with execution.

#### 2026-08-03T09:06:51.827Z  ·  `trig_timer_status_check`
*tags: daily_check, actor_response*
> Checked in with Learner B2 on Sprint 4 go-live deliverables and suggested a focus area.
- **mentor → learner:** Hi Learner B2! 👋 How are things coming along with the Sprint 4 go-live package today?
  
  I wanted to check in on the GTM plan and launch checklist, and see if any blockers popped up with the experiment design or metrics dashboard. 
  
  Focusing on the core GTM messaging and quantitative rollout triggers first is a great place to start—it'll make putting together the final Demo Day deck much easier.

#### 2026-08-03T09:06:20.697000+00:00  ·  `trig_human_mentor_msg`
*tags: human_mentor_message*
> Human mentor (via the manager account) messaged the learner directly: Learner B2, your task for Sprint 4 is now active: GTM Plan, Launch Checklist, A/B Experiment, Metrics Dashboard & Final Demo Day.
Context & Scope:
Prepare the product for go-live and present the complete e
- **human_mentor → learner:** Learner B2, your task for Sprint 4 is now active: GTM Plan, Launch Checklist, A/B Experiment, Metrics Dashboard & Final Demo Day.
  Context & Scope:
  Prepare the product for go-live and present the complete end-to-end product journey. Your work must build directly on your completed artifacts from Sprints 1, 2, and 3.
  Required Build:
  Go-To-Market (GTM) Plan: Define your target segment with prioritization logic, research-grounded messaging, at least two distribution channels, rollout phases (Beta, Staged, Full) with quantitative exit triggers, and a launch timeline.
  Launch Checklist: Create a checklist with a minimum of 10 items spanning pre-launch, launch day, and post-launch. Assign ownership strictly by role title and include quantitative rollback or pause triggers.
  A/B Experiment Design: Design one A/B experiment for your riskiest assumption using the format 'If change X, then metric Y moves Z because W' tied to your Sprint 2 Metric Tree. Specify control/variant, minimum sample size, run duration, and a pre-mortem with failure modes and corrective actions.
  Metrics Dashboard Mockup: Track at least 5 metrics from your Sprint 2 Metric Tree, detailing definition, tracking cadence, role owner, and action triggers for underperformance.
  Final Demo Day Deck: Develop a presentation deck covering the full four-week product narrative arc and explicit trade-offs made.
  Deliverables & Assets:
  Submit strategy and launch documentation, checklist, experiment brief, dashboard mockup, and presentation deck. No external assets are provided; align strictly with your prior sprint artifacts.
  Deadline:
  The final deadline for submission is Thursday, August 6, 2026, at 11:59 PM Cairo time.
  Evaluation & Support Routing:
  Evaluation will focus on completeness, logical alignment across all four sprints, role-based governance, and quantitative thresholds. Technical guidance and draft feedback must be directed to your mentor, to whom you will submit your final work. Direct platform access or administrative issues to the internship team group mentioning the group admins.
  Review these requirements and proceed immediately with execution.

#### 2026-08-03T09:07:18.426Z  ·  `trig_timer_reminder`
*tags: deadline_reminder, actor_response*
> Sent a friendly deadline reminder for Sprint 4 with submission instructions and an invitation for questions.
- **mentor → learner:** We have about 84 hours left until Thursday's Sprint 4 go-live submission deadline. If you run into any questions while finalizing the launch checklist, A/B experiment design, or Demo Day deck, share what you're working on here. You can submit your draft right here as a document link, file attachment, or text whenever you're ready.

#### 2026-08-04T09:06:19.705Z  ·  `trig_timer_status_check`
*tags: daily_check, actor_response*
> Checked in on daily progress and offered guidance on setting launch checklist rollback triggers for Sprint 4.
- **mentor → learner:** How are things moving with your Sprint 4 go-live deliverables today? 👋 If you've already got the GTM messaging and metrics dashboard mapped out, defining the quantitative rollback triggers for your launch checklist is a great place to focus. How is the draft coming along, and is anything blocking you?

#### 2026-08-05T09:03:32.495Z  ·  `trig_timer_status_check`
*tags: daily_check, actor_response*
> Checked in with the learner on Sprint 4 go-live deliverables and suggested next steps for the Demo Day deck.
- **mentor → learner:** How are your Sprint 4 go-live deliverables coming along today? 👋 If you've run into any blockers with the quantitative rollback triggers or the metrics dashboard, drop a note here with where you're stuck. Once those core pieces are solid, drafting the narrative for your Final Demo Day presentation is a great next step.

#### 2026-08-06T09:01:59.609Z  ·  `trig_timer_status_check`
*tags: daily_check, actor_response*
> Daily status check-in asking about progress on Sprint 4 deliverables and any remaining blockers before tonight's deadline.
- **mentor → learner:** With tonight's Sprint 4 deadline getting closer, how are things shaping up with your GTM plan, metrics dashboard, and Final Demo Day deck? If you're running into any quick blockers with the rollback triggers or experiment design, drop them here so we can clear them out before submission.

#### 2026-08-06T20:59:19.439Z  ·  `trig_timer_deadline`
*tags: deadline_extended, actor_response*
> Original deadline reached without a passing submission. Manager granted a one-time 48h extension; new deadline 2026-08-08T20:59:19.439Z.
- **manager → learner:** Hi Learner B2, the deadline passed without a passing submission. A one-time 48-hour extension has been granted, bringing your new deadline to Saturday, August 8 at 11:59 PM Cairo time. No further extensions will be granted, so focus on submitting your finalized deliverable.
<details><summary>scenario_events</summary>

```json
[
  {
    "at": "2026-08-06T20:59:19.439Z",
    "kind": "deadline_extended",
    "new_deadline": "2026-08-08T20:59:19.439Z"
  }
]
```
</details>
