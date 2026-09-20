# Python Agent Foundry Workbench

The integrated historical Python workbench: author capability packages, assemble agent tasks, and inspect the local records that connect them. It includes package editing, Agent Foundry, Assembly, user-control and chatroom surfaces in Tkinter.

## Try it

Python 3.11 or newer with Tkinter. Windows is the primary tested desktop environment.

```sh
python -m pip install -r requirements.txt
python -m examples.first_workflow --workspace ./demo-workspace
python main.py --workspace ./demo-workspace
```

The example creates a synthetic `normalizer` package and `DemoAgent` with one `Normalize` task, runs `{"value":"  hello   foundry  "}`, and checks `{"normalized":"hello foundry"}`. It requires an empty workspace. Open the desktop, choose Agent, and load DemoAgent to inspect the saved task and embedded source. The ordinary desktop also creates local registry defaults for a new workspace.

## How it works

The authoring environment connects inspectable package definitions to concrete task assembly rather than treating prompts as the whole system. Read the [mechanism and implementation notes](docs/MECHANISM.md) for the specific boundaries and source links.

## Scope

This is a historical prototype, distinct from the later TypeScript Skeleton. The optional visual skin and private host connectors are not bundled. The old Fake demo control stays disabled without its optional connector. Automatic package post-save review is off until a local review agent is deliberately configured. The live runner does not enforce its timeout argument and is not sandboxed. The verified desktop walkthrough loads DemoAgent and inspects its saved task and workflow; it does not cover every visual interaction.

## Check a saved revision

`python -m examples.revision_walkthrough` saves and runs two task revisions in one process, checking that the second run uses the second saved source. The [worked guide](docs/MECHANISM.md) explains embedded package snapshots, persistent System tasks, failures and the import-cache repair.

## Verify

`python -m pytest` runs the behavior tests (install `pytest` first). The runnable example above provides a separate first-use check.

MIT licensed; see [LICENSE.md](LICENSE.md). Origin and release boundaries are documented in [ORIGIN.md](ORIGIN.md) and [SECURITY.md](SECURITY.md).

## Inspect the example result

Open the [saved synthetic result](examples/captured-result.json) alongside its [input and demonstration](examples/first_workflow.py). The result is from the bundled synthetic example; local machine paths and temporary run identifiers are excluded from public projections.
