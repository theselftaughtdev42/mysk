---
name: to-requirements
description: Turn the current conversation context into a requirements document and publish it to a file. Use when user wants to create requirements from the current context.
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

Domain knowledge can be found in `CONTEXT.md` or if there are many domain documents in the codebase then `CONTEXT-MAP.md` will contain references to their locations. Use this documentation to ensure your wording is inline with the codebase architecture.

ADRs can be found in a `docs/adr/` directory, or if a `CONTEXT-MAP.md` exists then there may be an `docs/adr/` directory alongside each `CONTEXT.md` file.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the PRD, and respect any ADRs in the area you're touching.

2. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

3. Write the requirements document using the template below and write it to a local `REQUIREMENTS.md` file so the user has something concrete to validate against.

<rd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A numbered list of concise user stories which together solve the problem at hand. Each user story should equate to a sensibly sized MR.

Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-examples>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-examples>

### Acceptance Criteria

Each user story should have a extensive list of acceptance criteria covering the implementation details. Each acceptance criteria should be in the format of:

1. <GIVEN>, <WHEN>, <THEN> (optionally <AND>)

<acceptance-criteria-examples>
1. GIVEN I have logged into my banking app, WHEN the homepage loads, THEN I am able to see balance on my accounts.
2. GIVEN I am calling `toolbox.io.IOFile.read_tabular`, WHEN I pass a list of field names to the `required_columns` argument AND at least one of those field names does not exist in the loaded data, THEN an error is thrown saying which field is missing.
</acceptance-criteria-examples>

This list of acceptance criteria should be extremely extensive and cover all aspects of the feature.

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</rd-template>
