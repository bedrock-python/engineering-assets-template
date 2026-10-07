---
name: app-stop
description: Stop the local run of the service that /app-start started.
disable-model-invocation: true
---

Stop the local run of the service.

1. Use the "Stop the local run" command from `.agents/project.md` if it has one. Otherwise stop the process that `/app-start` started in this session and the local services it brought up, and nothing else.
2. Never stop processes or containers this session did not start, and never delete volumes or data unless the user asks.
3. Say what you stopped.
