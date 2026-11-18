# Shared sc-agent client contracts

judge-jev's generated client and sitr integration follow these producer-owned records:

- [REQ-SAG-0018: generated Python consumer module](https://github.com/randlee/sc-agent/blob/develop/docs/requirements/REQ-SAG-0018.md) defines the consumer template and the controlled sitr extraction-to-dry-run check.
- [ADR-SAG-0019: shared Python decision harness](https://github.com/randlee/sc-agent/blob/develop/docs/adr/ADR-SAG-0019.md) defines the matched wheel versions and the separate, lazily imported sitr section.

judge-jev always enables sitr, pins it to the sc-decidr version, and imports `sc_treesitter` lazily inside `extract()`; there is no install-time sitr switch.

judge-jev uses sc-agent's default credential lookup (keyring service = variable name, account = OS user), per [REQ-JEV-0003](../requirements/raptor-integration.md#req-jev-0003-typesafe-key-lookup) and owner ruling `agt-wfav`.
[REQ-JEV-0004](../requirements/raptor-integration.md#req-jev-0004-remote-judge-consent) governs remote-judge consent; it does not define sitr integration.
