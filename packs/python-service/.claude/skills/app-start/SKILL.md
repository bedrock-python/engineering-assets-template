---
name: app-start
description: Start the service locally with the command from the project profile.
disable-model-invocation: true
---

Start the service locally.

1. Take the "Run locally" command from `.agents/project.md`. If the profile has none, look in the README, the Makefile, `pyproject.toml` and the compose files, show what you found and ask before running it.
2. Check what it needs first: installed dependencies, configuration copied from the example files, local services such as a database. Never fill in real credentials: ask the user.
3. Start it in the background so the session stays usable. Wait until it reports that it is ready or its health check answers, then give the address and say that `/app-stop` stops it.
4. If it fails to start, show the relevant lines of its log and the likely cause.
