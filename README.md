# canon

the organizational continuity agent.

canon embeds in your team's workflow, automatically capturing micro-decisions, reasoning, and context that normally evaporate. it maintains a knowledge graph of decisions, incidents, and migrations - and surfaces relevant memory to your coding assistant before you write code.

## how it works

1. **orchestrator agent** receives a request from a coding assistant, searches organizational memory, traces relationships, reshapes the plan, and records what happened.
2. **semantic retriever** finds relevant knowledge through hybrid search (vector + full-text) over a mongodb atlas collection.
3. **graph explorer** walks edges recursively to build context around matched nodes.

all three agents run on gemini.

the agent talks to mongodb through the [mongodb mcp server](https://github.com/mongodb-js/mongodb-mcp-server). memories are stored as connected nodes in a single atlas collection, with $rankFusion hybrid search and $graphLookup traversal powering retrieval.

built with [agent development kit](https://adk.dev/), backed by mongodb atlas, and accessible via an http api (any agent can call it) or canon's own mcp server (for antigravity, claude code, etc.).

## structure

| directory   | purpose                                                     |
| ----------- | ----------------------------------------------------------- |
| `backend/`  | python http api - agent runtime, adk plugins, mongodb tools |
| `frontend/` | next.js reasoning feed + knowledge graph explorer           |
| `mcp/`      | mcp server that connects coding assistants to the api       |
| `docs/`     | internal documentation                                      |
| `local/`    | local development helpers                                   |

## local development

```bash
cd local
cp .env.example .env
./canon up
./canon init   # setup
./canon seed   # seed development data (sign up at localhost:3200, then replace TENANT_ID in backend/scripts/seed/node_definitions.py)
```
