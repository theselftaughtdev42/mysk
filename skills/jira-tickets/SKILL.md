---
name: jira-tickets
description: View and edit Jira tickets using the acli CLI. Use when user mentions a Jira ticket key (e.g. "WVE-376"), asks to view/update/edit/transition a ticket, wants to change a ticket's summary, description, status.
---

# Improve Jira Ticket
Views are free — read tickets without asking.

If `acli` is not available or fails with an auth error, tell the user to install/configure it before proceeding.

When editing a ticket:
- If the task/s required are small enough to be completed in a single MR, then add the list of task/s to the ticket description with appropriate acceptance criteria
- If the tasks required should reasonably be spread over more than one MR, then create sequential subtasks ensuring each subtask has appropriate acceptance criteria

## Task

### Viewing a ticket
1. Run `acli jira workitem view <KEY>`

### Editing a ticket
1. Run `acli jira workitem view <KEY>` to show current state
2. Discuss the proposed changes with the user
3. **Draft the update and get user approval before submitting**
4. Run `acli jira workitem edit --key "<KEY>" --<field> "<value>"`
    - Supported fields include: `--summary`, `--description`
5. Confirm success and show the updated ticket

### Transitioning a ticket
1. Run `acli jira workitem view <KEY>` to see the current status
2. Propose the transition to the user
3. **Get user approval before transitioning**
4. Run `acli jira workitem transition --key "<KEY>" --status "<status>"`
    - Supported status include: `BACKLOG`, `READY FOR DEVELOPMENT`, `IN PROGRESS`, `DONE`, `CAN'T FIX`, `WON'T FIX`

### Creating a subtask
1. Run `acli jira workitem view <PARENT-KEY>` to understand the parent ticket
2. Propose a summary and description for the subtask — subtasks must always include a `--description`
3. **Get user approval before creating**
4. Run `acli jira workitem create --summary "<title>" --description "<description>" --type "Sub-task" --parent "<PARENT-KEY>" --project "<PROJECT>"`
    - Derive the project from the parent key prefix (e.g. `ABC` from `ABC-123`)
5. Confirm success and share the link

## Rules
- **Always confirm with the user before pushing any edit to Jira.**
- For multi-line descriptions, pass the value directly in the `--description` flag with literal newlines: `--description "As a user...\n\nAcceptance criteria:\n- First criterion\n- Second criterion"`
