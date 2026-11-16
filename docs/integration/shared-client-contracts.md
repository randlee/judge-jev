# Shared sc-agent client contracts

judge-jev's generated client and optional sitr integration follow these producer-owned records:

- [REQ-SAG-0018: generated Python consumer module](https://github.com/randlee/sc-agent/blob/develop/docs/requirements/REQ-SAG-0018.md) defines the consumer template and the controlled sitr extraction-to-dry-run check.
- [ADR-SAG-0019: shared Python decision harness](https://github.com/randlee/sc-agent/blob/develop/docs/adr/ADR-SAG-0019.md) defines the matched wheel versions and the separate, lazily imported sitr section.

These sc-agent records apply while judge-jev uses its generated client and sitr support.
[REQ-JEV-0004](../requirements/raptor-integration.md#req-jev-0004-remote-judge-consent) governs remote-judge consent; it does not define sitr integration.
