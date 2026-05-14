## Competitor Intelligence Agent

- **Name**: Competitor Intelligence Agent
- **Description**: Monitors competitor websites for content and pricing changes and stores summaries in long-term memory.
- **Version**: 1.0.0
- **Runtime**: v2 (filesystem agent)

### Inputs

- `urls` (list of strings): list of competitor URLs to monitor.

### Behavior

On each run the agent:

1. Reads the list of URLs from inputs.
2. Logs start/end events so the dashboard can show progress.
3. Uses long-term memory to store a simple snapshot per URL.
4. Returns a structured payload containing `summary` and `changes`.

The current implementation uses placeholder snapshots and is intended as a
production-ready template; HTTP fetching and real diffing logic can be added
incrementally without changing the surrounding platform APIs.

