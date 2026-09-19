# Security and privacy

- No environment file, credential, database, generated agent, chat, transcript, model state, or private connector is included.
- Generated state defaults beneath the repository's `Storage/Generated Artifacts` area and is ignored by Git.
- Embedded package and workflow source is executable Python. Review it as code before running it.
- User approval screens are workflow controls, not an operating-system sandbox.
- The historical runner can create and remove its own contained temporary task directories; it should not be pointed at an untrusted storage root.
- Chatroom files contain plaintext message bodies.

Use this snapshot in a disposable environment for evaluation. Do not load untrusted packages or agent documents.
