# judge-jev Requirements - Raptor Integration

**ID Range:** REQ-JEV-0001 through REQ-JEV-0010, NFR-JEV-0001  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-24  
**Owner:** Rand Lee  
**Version:** 0.4.0  

---

## Overview

judge-jev works with Raptor-parseable Markdown and Raptor's SQL store. It
reads records only through Raptor and sends every Jev request through one
batch command.

---

## REQ-JEV-0001: Records come from Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the tool that imports records.

**MUST statements:**

- judge-jev MUST obtain records through Raptor's query interface.

**MUST NOT statements:**

- judge-jev MUST NOT parse record Markdown itself.
- judge-jev MUST NOT run SQL (Structured Query Language) against the record
  store itself.

### Rationale

Raptor owns the schema and every conversion; the Raptor team can change
them and notify judge-jev without breaking it.

### Success Criteria

**Acceptance Criteria:**

- [ ] judge-jev contains no Markdown record parser and no SQL statement.

## REQ-JEV-0002: One batch command calls Jev

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. The batch command is `jev_judge.py
batch`: it reads request lines (one JSON request per line), sends each through
the adopted sc-agent client to Jev and writes a result line. The session
log is sc-agent's log of every Jev query: one row per query, keyed by the
query's `session_id`, holding the request and Jev's answers. A result
envelope is the `jev-batch-result/2` JSON result line for one request
(the sc-decidr wheel's `sc_agent/templates/jev-batch-result.schema.json`): it holds the request's
`session_id` and the verdict derived from Jev's answers, or its error. A
typed error code is a stable dotted code naming a failure, such as
`DECIDR.NETWORK` or `DECIDR.RATE_LIMITED`. The retry policy belongs to the
adopted sc-agent client; judge-jev does not resend requests. The request
size limit is the `--max-request-bytes` value, at most 64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes with
`--gate dev`. The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`logs/judge-jev.log.jsonl` under the wheel's log root (`JUDGE_JEV_LOG_ROOT`,
else `~/.sc-agent`; sc-agent REQ-SAG-0022).

**MUST statements:**

- judge-jev MUST send every Jev request through one batch command.
- The batch command MUST read request lines.
- The batch command MUST write one result envelope per request.
- The batch command MUST use typed error codes.
- The batch command MUST use the adopted sc-agent client's retry policy
  without resending requests itself.
- The batch command MUST enforce request size limits.
- Each result envelope of an answered request MUST carry the `session_id`
  of the session-log row that holds the request and its answers.
- The batch command MUST log every result envelope through the
  sc-observability logger (REQ-JEV-0008).
- judge-jev's record of a result envelope MUST be that envelope's `result`
  log event, which adds judge-jev's own ids (record id, `anchor_id`,
  `candidate_id`, repeat) and carries the run's `run_id` as
  `correlation_id`.

**MUST NOT statements:**

- The batch command MUST NOT write the request text, Jev's response, Jev's
  answers, the answering model or a send count into a result envelope.
- The batch command MUST NOT log the request text, Jev's response, Jev's
  answers, the answering model or a send count.

### Rationale

One call path keeps the Jev core stable while a Rust implementation
replaces it (ADR-JEV-0001).

Owner ruling (2026-11-24, phase j): every Jev query lands in sc-agent's
session log, so a tool's own records reference the query's `session_id`
and copy nothing the session row holds.

Lead ruling (2026-11-24, phase j plan review): the `result` log event is judge-jev's record
of a line; there is no third artifact beside the result line and the event.

### Success Criteria

**Acceptance Criteria:**

- [ ] A request file of three lines produces three result envelopes, each
  carrying its `session_id`, and three result log events.
- [ ] No result envelope or log event of the batch command holds a request
  text or an answer.

## REQ-JEV-0003: TypeSafe key lookup

**Status:** Draft  

### Requirement Statement

Definitions: TypeSafe is the company whose API (application programming
interface) serves Jev, the judge model; the TypeSafe API key authenticates
calls to it. The platform credential store is the macOS Keychain, the
Windows Credential Manager or, on Linux, the Secret Service (`secret-tool`).

**MUST statements:**

- judge-jev MUST obtain every provider key, the TypeSafe API key included,
  only through the adopted sc-agent client, which resolves it in the order of
  REQ-SAG-0401 (the environment, then the repository `.env` file, then the
  default platform credential entry: service `TYPESAFE_API_KEY`, current OS
  account).

**MUST NOT statements:**

- judge-jev MUST NOT pass keyring service or account overrides to sc-agent.
- judge-jev MUST NOT read a provider key itself.

### Rationale

Tools that call Jev share one stored key, saved once.

Consumers do not read keys; the wheel resolves them (REQ-SAG-0401). The
earlier `.env`-first order is replaced by the wheel's order (phase j plan
review, 2026-11-24).

### Success Criteria

**Acceptance Criteria:**

- [ ] A key stored in sc-agent's default credential entry is found with no
  other setup.

## REQ-JEV-0004: Remote-judge consent

**Status:** Draft  

### Requirement Statement

Definitions: Jev is TypeSafe's hosted judge model: it answers each
multiple-choice question about a text with one choice and a confidence from
0 to 1. A Jev request is one call to it. A live Jev call is a request sent
to Jev, as opposed to a dry run or an answers file.
`POLICY.REMOTE_JUDGE_DISABLED` is the typed error code for a refused live
call. `allow_remote_judge` is consent to send to TypeSafe only. `haiku`
and `luna` are the fast model names of REQ-JEV-0009.

**MUST statements:**

- judge-jev MUST refuse every live call whose model the sc-decidr wheel
  resolves to the TypeSafe provider with `POLICY.REMOTE_JUDGE_DISABLED`
  unless the committed `.sc/judge-jev/settings.yaml` sets
  `allow_remote_judge: true`.
- The consent check MUST be the adopted sc-agent client's gate, which
  compares the resolved provider with the wheel's TypeSafe constant.

**MUST NOT statements:**

- judge-jev MUST NOT write that setting without the user's answer.
- judge-jev MUST NOT refuse a request resolved to any other provider, such
  as a `haiku` or `luna` request, because `allow_remote_judge` is absent or
  false.
- judge-jev MUST NOT decide consent from the model name.

### Rationale

Text sent to Jev leaves the machine; the user decides once per repository.

Owner ruling (2026-11-24, phase j plan review): `allow_remote_judge` is
consent for TypeSafe only.

### Success Criteria

**Acceptance Criteria:**

- [ ] With the setting absent or false, a live call exits with
  `POLICY.REMOTE_JUDGE_DISABLED` and sends nothing.
- [ ] With the setting absent or false, a `--model haiku` request and a
  `--model luna` request each reach sc-agent's loopback provider stub.

## REQ-JEV-0005: Marketplace and installer

**Status:** Draft  

### Requirement Statement

Definitions: A harness is an agent tool judge-jev installs into: Claude
(Claude Code), Codex or Cursor. A marketplace plugin is a plugin a harness
installs from a plugin marketplace. A harness is locked when the install
lock records it, installed when its `.<harness>/skills/judge-jev/` directory
exists, and present when its `.<harness>/` directory exists in the
repository. An upgrade is an install of a newer judge-jev version.

**MUST statements:**

- judge-jev MUST ship as a marketplace plugin for Claude.
- judge-jev MUST ship as a marketplace plugin for Codex.
- judge-jev MUST ship as a marketplace plugin for Cursor.
- An upgrade MUST update every harness that is locked, installed or present.

### Rationale

No harness is left on an old version.

### Success Criteria

**Acceptance Criteria:**

- [ ] Upgrading in a repository with Claude, Codex and Cursor installs
  updates all three.

## REQ-JEV-0006: Local record database built through Raptor

**Status:** Draft  

### Requirement Statement

Definitions: Raptor is the requirements tool that imports Markdown records
into its record store and serves them to other tools (ADR-JEV-0002).
Raptor-parseable Markdown is Markdown in the record format Raptor's import
reads. SQLite is a single-file SQL (Structured Query Language) database.
Dolt is a SQL database with Git-style branches; a SQLite snapshot of a Dolt
branch is a SQLite copy of that branch's records. The Raptor interface is
the way Raptor hands records to another tool.

**MUST statements:**

- judge-jev MUST obtain its record database by asking Raptor to build a
  local SQLite database from the repository's Raptor-parseable Markdown on
  each run.
- When Raptor supplies a SQLite snapshot of a Dolt branch, judge-jev MUST
  query it through the same Raptor interface.

### Rationale

Querying SQLite is the same work whether it was built from Markdown or
pulled from Dolt, so the source can change without changing judge-jev.

### Success Criteria

**Acceptance Criteria:**

- [ ] A run in a repository with a `.raptor/` configuration judges records
  from a database built in that run.

## REQ-JEV-0007: judge-jev's own records are Raptor-parseable

**Status:** Draft  

### Requirement Statement

Definitions: An issue is a diagnostic Raptor's import reports.

**MUST statements:**

- judge-jev's requirements, non-functional requirements and decisions MUST
  import through Raptor with no issues.

### Rationale

judge-jev depends on Raptor's format, so its own records prove the format
first.

### Success Criteria

**Acceptance Criteria:**

- [ ] Raptor's import of this repository reports zero issues.

## REQ-JEV-0008: Logging through the sc-observability logger

**Status:** Draft  

### Requirement Statement

Definitions: The sc-observability logger is the JSON-lines logger of the
sc-observability package (version 1.5.0), which writes
`logs/judge-jev.log.jsonl` under the wheel's log root (`JUDGE_JEV_LOG_ROOT`,
else `~/.sc-agent`; sc-agent REQ-SAG-0022). sc-agent is the agent tool whose
Rust Jev tool will replace judge-jev's Python Jev core (ADR-JEV-0007). A
quality-tree branch is the next wave a quality decision tree's rules select
from Jev's answers. The session log is sc-agent's log of every Jev
query: one row per query, keyed by the query's `session_id`, holding the
request and Jev's answers.

**MUST statements:**

- judge-jev MUST write its run logs (result envelopes, quality-tree
  branches and verdicts, each referencing the `session_id`s it used)
  through the sc-observability logger, the logger sc-agent uses.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own log format alongside it.
- judge-jev MUST NOT write Jev requests or Jev's answers to its run logs.

### Rationale

Rand (2026-11-08): "we will need to use sc-observability logger for both
(this is what sc-agent uses). we should implement in judge-jev first then
we can upgrade plan-anchor which is currently working solidly."

Owner ruling (2026-11-24, phase j): requests and answers are read from the
session log by `session_id`; judge-jev's logs do not copy them.

### Success Criteria

**Acceptance Criteria:**

- [ ] A live `quality` run's quality-tree branches and verdicts appear in
  the sc-observability log with the `session_id`s they used.
- [ ] No event of that run in the sc-observability log holds a request
  text or an answer.
- [ ] No judge-jev command writes `anchor-runs/tournament-*.jsonl`.

### Implementation Notes

Today the copied core writes its own `anchor-runs/tournament-<run>.jsonl`
(`jev_judge.py` `pump_batch`). plan-anchor moves to the same logger after
judge-jev.

## REQ-JEV-0009: Fast models without a TypeSafe key

**Status:** Draft  

### Requirement Statement

Definitions: `haiku` and `luna` are fast model names. A model selector is
a short name or model id the sc-decidr wheel resolves. The wheel resolves
each selector to a provider (the global model configuration
`models.<alias>`, else the first model-table row, newest first, whose
provider is keyless or whose key resolves) and resolves that provider's key; it reports a missing key. A live request
is a request sent to a model, as opposed to a dry run or an answers
file.

**MUST statements:**

- The sending commands `batch`, `quality`, `compare-definition` and `drift`
  MUST each take `--model <selector>`.
- Each sending command MUST accept `--model haiku`.
- Each sending command MUST accept `--model luna`.
- Each sending command MUST pass the caller's selector unchanged to the
  command's one `Run` and send every request of that command with that one
  model.
- With no `--model`, a sending command MUST pass no model, so the wheel's
  configured default model (setting `model`, built-in `jev`; sc-agent
  REQ-SAG-0019) applies.

**MUST NOT statements:**

- judge-jev MUST NOT refuse a live `haiku` or `luna` request because
  `TYPESAFE_API_KEY` is unset when the wheel resolves a key for that
  model.
- judge-jev MUST NOT choose a provider for a model.
- judge-jev MUST NOT name a model in code; the caller chooses the model.
- judge-jev MUST NOT keep a default model of its own.
- judge-jev MUST NOT check a provider's key itself.

### Rationale

Owner ruling (2026-11-24, phase j): every tool built on sc-agent works with
`--model haiku` and `--model luna`, including when no `TYPESAFE_API_KEY`
is set.

Owner ruling (2026-11-24, phase j plan review): consumers pass only the
model name; the wheel resolves the provider (sc-agent phase j).

Owner ruling (2026-11-24, phase j plan review): no model name is
hard-coded in a call; the caller runs jev or haiku or luna or laya or
decider, one model per command, and fan-out across models is the caller's
job.

Owner ruling (2026-11-24, phase j plan review): with no `--model` the model
is `jev`, overridable by a configuration variable (the wheel's `model`
setting).

### Success Criteria

**Acceptance Criteria:**

- [ ] With `TYPESAFE_API_KEY` unset and the key of the provider the wheel
  resolves for the model set to a test value, `--model haiku` and `--model luna` each send their request to
  sc-agent's loopback provider stub and write a result envelope.
- [ ] `batch`, `quality`, `compare-definition` and `drift` each pass
  `--model haiku` unchanged to their one `Run`, and with no `--model` each
  opens its `Run` with no model.
- [ ] No test uses a real key or the keyring, and no test sets `HOME`.

## REQ-JEV-0010: Provider keys are redacted

**Status:** Draft  

### Requirement Statement

Definitions: The provider-key list is the list of key names the
sc-decidr wheel exports, one or more for every provider it can send to,
TypeSafe included. A provider key is the value of a name in that list in
judge-jev's environment. An emitted value is any value judge-jev writes to
stdout, to a file or to a log event.

**MUST statements:**

- judge-jev MUST replace each provider key's exact value with `[redacted]`
  in every emitted value.
- judge-jev MUST replace each bearer token with `[redacted]` in every
  emitted value.
- judge-jev MUST redact provider keys and bearer tokens through the
  adopted sc-agent client's redaction.

**MUST NOT statements:**

- judge-jev MUST NOT keep its own list of provider key names.
- judge-jev MUST NOT keep its own redaction code.

### Rationale

Owner ruling (2026-11-24, phase j): secret redaction covers every provider
key, not only `TYPESAFE_API_KEY`.

Owner ruling (2026-11-24, phase j plan review): the wheel owns the
provider-key list; consumers keep no copy of it.

### Success Criteria

**Acceptance Criteria:**

- [ ] A canary value in each variable of the wheel's provider-key list,
  fed through a request's text, is absent from stdout, the written files
  and the log events.

### Implementation Notes

Today `_redact_text` in `scripts/jev_errors.py.j2` reads only
`TYPESAFE_API_KEY`; phase j deletes `jev_errors.py.j2` and its callers use
the client's `redact_secrets`. The placeholder is the client's
`[redacted]`.

## NFR-JEV-0001: Deterministic offline tests

**Status:** Draft  

### Requirement Statement

Definitions: Jev is a judge model. Recorded Jev answers are an answers file.

**MUST statements:**

- judge-jev tests MUST run offline against recorded Jev answers.
- A run from recorded answers (an answers file) MUST open no sc-agent
  `Run` and write no result line or result event.
- A recorded answer MUST be one answer or one error; an answers file
  MUST NOT simulate send attempts.

**MUST NOT statements:**

- judge-jev tests MUST NOT depend on timing.
- judge-jev tests MUST NOT depend on sleeps.
- judge-jev tests MUST NOT depend on ordering.

### Rationale

Flaky tests are prohibited; live Jev calls are neither free nor
repeatable.

Lead ruling (2026-11-24, phase j plan review): a fixture run answers in process and
writes nothing a live run would; retries belong to the sc-agent client.

### Success Criteria

**Acceptance Criteria:**

- [ ] The test suite passes 20 consecutive runs with networking disabled.
