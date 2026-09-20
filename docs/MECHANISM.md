# From package source to a saved agent task

This workbench preserves an authored Python desktop environment for building packages and assembling them into agents. Its useful first path is a small, inspectable local transformation: save a function, embed it in a task, run that task, and inspect the records the desktop loads.

## The first result

```sh
python -m examples.first_workflow --workspace ./demo-workspace
python main.py --workspace ./demo-workspace
```

Use an empty workspace. The example saves `normalizer`, embeds it in DemoAgent's **Normalize** task, and runs `{"value":"  hello   foundry  "}`. The result must be `{"normalized":"hello foundry"}`. [captured-result.json](../examples/captured-result.json) is a portable projection of that synthetic result; the command also prints local paths so you can inspect your own workspace.

In the desktop, choose **Agent**, then **Open Agent**, and load **DemoAgent**. Under **Outcasts → Normalize**, inspect **Packages** and **Workflow**. The saved task is **On Demand**. The disabled demo control belongs to an optional connector; it is not needed by the command-line example.

The bounded desktop walkthrough loads this saved agent, reads its embedded source through the UI state, and opens the Workflow tab. It does not establish every operation in every tab or any private connector integration.

## Which record owns what?

| Record or component | Responsibility |
|---|---|
| [CollectionHandoff](../collection_handoff.py) | Workspace storage registry and locations; fresh initialization preserves an existing registry |
| [PackageEditorController](../package_manager.py) | Saved reusable package source and contracts |
| [AssemblyManager](../Operations/assembly/assembly_manager.py) | Validates and writes canonical agent JSON, with generated task/group projections |
| The task's embedded package entries | The specific package source selected for that task |
| [TaskRunner](../Operations/task_runner.py) | Reads the saved task, materializes Python files and invokes `run_workflow(payload)` |

The canonical agent JSON is the source of truth for its tasks. The task is not a live alias to whichever version of a standalone package was edited most recently. Save the intended package snapshot into the agent task before expecting its run to change. Group and task files are derived projections, not competing authorities.

## Prove that a saved revision actually runs

```sh
python -m examples.revision_walkthrough
```

The example saves two successive **On Demand** task snapshots with a function returning `first` and then `second`. It runs both in one process and checks `["first", "second"]`; see [the captured result](../examples/revision-result.json).

This exposed a concrete defect in the historical runner: Python could retain the first materialized package in its import cache, so a newly saved task still returned `first`. The current runner temporarily removes conflicting module names, loads the materialized revision, then cleans up its modules and restores earlier host modules, including on failure. This supports sequential task runs. It does not isolate concurrent imports or sandbox code.

## Runtime and failure boundaries

- **On Demand:** the runner recreates the runtime directory from the saved task and removes it after execution, including failures. An exception propagates to the caller. Cleanup failures produce a warning; the canonical saved agent remains available.
- **System:** the runtime directory persists. `run_system_task` materializes only when that directory is absent. After editing a saved System task, call `materialize_system_task` deliberately to refresh its runtime before relying on the new source.
- **Timeout:** `timeout_seconds` is accepted but does not interrupt execution in this in-process runner. Use only trusted, terminating functions in this walkthrough. A hung function can hang its caller.
- **Access:** task source executes with the current Python process's access and installed dependencies. Do not treat workspace boundaries, package contracts or the UI as an operating-system sandbox.

Automatic package post-save review stays off until deliberately configured. The optional visual skin and private host connectors are not bundled. Chatroom attribution and storage have separate tests; this walkthrough makes no claim about live multi-agent coordination.

## Historical scope and further work

[ORIGIN.md](../ORIGIN.md) places this workbench before the later TypeScript Skeleton and identifies the extracted mechanism repositories. Keep this edition useful as a working, inspectable historical authoring environment. Process isolation, enforceable deadlines and concurrent execution would need their own design and tests; they are limitations to account for, not completed features implied by this repair.
