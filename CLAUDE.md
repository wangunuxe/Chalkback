# For AI assistants

Before writing code:

1. Read §0 of `DESIGN.md`, then the parts of §5–§9 relevant to the current role.
2. **Ask which role you are helping (A / B / C / D)**, and only write code in files that role owns (see the owner table in README and DESIGN.md §7).
3. Do not modify `contracts/` or invent new data formats or interfaces. If the docs are unclear, raise a question and let the responsible teammate decide.
4. Privacy boundary: raw transcripts, screenshots and screenpipe ids must never appear in any data sent to the Hub.
5. Done = meets the acceptance criteria in §8, and `make check` passes.
