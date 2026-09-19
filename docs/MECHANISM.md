# Python Agent Foundry Workbench: mechanism

[CollectionHandoff](../collection_handoff.py) owns local storage locations; fresh registry creation does not replace existing configuration. [PackageEditorController](../package_manager.py) saves package source/contracts, while [AssemblyManager](../Operations/assembly/assembly_manager.py) validates canonical agent JSON and writes task/group projections. [run_task](../Operations/task_runner.py) materializes and imports the trusted workflow in the current Python process. [main.py](../main.py) opens all six desktop tabs. The backend also includes durable chatroom records and attribution/cursor logic.

## Limits that matter

This is a historical prototype, distinct from the later TypeScript Skeleton. The optional visual skin and private host connectors are not bundled. The old Fake demo control stays disabled without its optional connector. Automatic package post-save review is off until a local review agent is deliberately configured. The live runner does not enforce its timeout argument and is not sandboxed. A hidden Tk launch check constructs all tabs, but this does not establish every visual interaction has been replayed.

## Demonstration contract

Input: A synthetic Python package and a workflow that calls it.

Expected observation: Desktop package, Foundry, Agent, User Control and Chatroom surfaces with inspectable local records.

The bundled example uses synthetic material. Its observed output establishes that bounded path, not every possible integration.
