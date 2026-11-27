# j-6 plan: judge-jev on the rendered j-4 client

Base: judge-jev origin/plan/phase-j @031a61f (records already trimmed; J6-16 of the old bead is done there). `S/` = `plugins/sc-judge-jev/install/templates/skills/judge-jev/scripts/`, `T/` = `tests/sc-judge-jev/`, `jj:` = `S/jev_judge.py.j2`. Line numbers are at 031a61f. Upstream: sc-agent origin/sprint/j-4 @6af95bc8 `docs/plans/phase-j/j-4-plan.md` (the template surface used here), j-2/j-3 plans, j-1 signatures. Written by reading the code; no j-6 code yet. The old prose bead (agt-j-6) is intent only.

## Goal

Rand (ANC-015, ANC-016, ANC-010, ANC-002/003, rule 0): "judge-jev and plan-anchor simply supply tool name and follow the rules established for all decidr based tools"; "derivative tools should defer to the default tool rules and not use injection path for production code (test only)". Measurable: judge-jev sends only through `decidr_client.run_batch` on one `decidr_client.open_run(...)` per sending command; `S/result.py.j2`, `S/jev_errors.py.j2` and `assets/schemas/jev-batch-result.schema.json` are gone; stdout lines are `jev-batch-result/2` with the 14 generic fields; no production code passes `general_log`/`seams`; `grep -rnE 'jev-batch-result/1|redact_sensitive|remote_preflight|DEFAULT_MODEL|from result import|from jev_errors|fixture_attempt|check_fixture_coverage|BATCH_MAX_WORKERS|BATCH_RETRIES|general_log|\.sc-agent/logs' S/ T/` finds nothing except `general_log` inside `seams=` in T/.

## Layout

| file | holds after j-6 |
|---|---|
| S/decidr_client.py.j2 | fresh `--strict` render of sc-agent `consumer.py.j2` 2.0.0 (`client_name: judge-jev`, `sitr: true`, `tool_version: {{ version }}`); generated, not edited |
| S/jev_judge.py.j2 | commands; job authoring (`batch_jobs`), `decide()`, `batch_verdict` (the typed verdict callback), `judge_batch` (thin wrapper over `run_batch`), `result_event`, the walk; no pump, consent, redaction or attempt code |
| S/jev_runs.py.j2 | rebuild: result events + `answers_for` → triples |
| S/jev_ports.py.j2, S/jev_graph.py.j2, S/jev_gate.py.j2, S/judge_jev_settings.py.j2 | import lines only (`from decidr_client import ...` instead of `from result import ...`) |
| S/result.py.j2, S/jev_errors.py.j2, assets/schemas/jev-batch-result.schema.json | deleted |
| scripts/integration.py | live runner: haiku and luna cases need no TypeSafe key |
| T/test_client_run.py (new) | tests below |

## Library pattern (rule 0)

- Config: judge-jev passes `--model` (or `None`) and its timeout/workers to `open_run`; the wheel's layered config resolves model, provider, cache, project and limits. No model literal, no worker cap, no provider name in judge-jev.
- Logging: the Run's default logger (`tool=CLIENT_NAME`) writes sends; judge-jev's own result/wave/verdict/compare/drift events go through the same Run: `decidr_client.log_event(run, ...)` (j-4 addition, see Plan decision 1), so they land in the Run's default logger (ANC-005). judge-jev imports no `sc_agent`. Every command that logs has a Run (fixture runs go through a real Run); a dry run logs nothing (REQ-JEV-0208), so no Run-less logging path exists. Injection exists only in tests (`open_run(seams={"general_log": ...})`, ANC-016); tests otherwise set `JUDGE_JEV_LOG_ROOT`.
- Limits: none of judge-jev's own (`--max-workers` is passed through to the Run unchecked; the Run returns its own error).
- Results: every client call returns `Ok`/`Err` from the template; judge-jev uses `isinstance(x, Err)` / `x.value` / `x.error` and has no `["ok"]` dict reads of client results.

## Public surface (exact Python; judge-jev is Python)

Imports (jj:99-104 replaced):

```python
from decidr_client import (Err, Ok, Result, ClientError, BatchSettings, BatchJob, ResultLine, StreamedResult,
                           BATCH_FIXTURE_ERROR, BATCH_ID_RE, REPO_ROOT_HELP, batch_request_id, safe_id, utf8_stdio, log_event)
Run = Any   # the wheel's sc_agent.Run, typed through the client; judge-jev never imports sc_agent
```
`S/judge_jev_settings.py.j2:63` → `from decidr_client import Err, Ok, Result, ToolError, err, run_main`; `S/jev_gate.py.j2:40` → `from decidr_client import run_main`; `S/jev_ports.py.j2:38`, `S/jev_runs.py.j2:44`, `S/jev_graph.py.j2:55` → `from decidr_client import Err, Ok, Result`. The consent block's import of `judge_jev_settings` is inside the gate function (j-4 owns it), so no import cycle.

jev_judge (changed or new; everything else keeps its signature):

```python
def batch_verdict(job: BatchJob, settings: BatchSettings, answers: Mapping[str, Any] | None
                  ) -> tuple[str | None, float | None, str | None]
    # (verdict, min_confidence, leaning); (None, None, None) when answers is None or job.anchor_id is None; calls decide()

def batch_jobs(line, number: int, settings: BatchSettings, base_roles: dict) -> Result[list[BatchJob], ClientError]
    # unchanged signature; body = {"state": ..., "questions": ...} (no "model": the Run owns the model)

def result_event(line: ResultLine, job: BatchJob, fields: Mapping[str, Any]) -> dict[str, Any]
    # {**fields, **line._asdict() minus schema/tool/tool_version/agent_role, error encoded,
    #  "item_id", "anchor_id", "candidate_id", "repeat"}  -- judge-jev's record of the line (ADR-JEV-0007 l.389-390)

def log_result_line(run: Run, line: ResultLine, job: BatchJob, fields: Mapping[str, Any]) -> Result[None, ClientError]
    # decidr_client.log_event(run, LOG_TARGET, "result", line.run_id, result_event(line, job, fields))

def judge_batch(run: Run | None, lines: list, settings: BatchSettings, *, fixture: Mapping[str, Any] | None,
                echo: bool, fields: Mapping[str, Any] | None = None, cache: bool | None = None,
                repository_root: str = ".") -> Result[list[tuple[ResultLine, Mapping[str, Any] | None]], ClientError]
    # builds jobs, calls decidr_client.run_batch(run, jobs, settings, fixture=..., verdict=batch_verdict,
    #   abort_on=frozenset({"auth"}), repository_root=..., consent_what=..., on_line=collect + log_result_line + echo)
    # run None only for a dry run (no line, no event); returns (line, answers) in index order; answers are what the walk and drift need, never logged

def open_command_run(args: argparse.Namespace, *, timeout_secs: float | None, workers: int | None,
                     cache: bool | None = None, repeat: int = 1) -> Result[Run, ClientError]
    # decidr_client.open_run(model=args.model, cache=cache, repeat=repeat, timeout_secs=..., workers=...)

def walk_tree(tree: QualityTree, record: dict, settings: BatchSettings, fixture, fields: dict,
              definitions=(), location=None, *, run: Run, repository_root=".") -> Result[tuple, ClientError]

def wave_log_events(fields: dict, node_id: str, node: Wave, statements: list, results: list, per_choices: list,
                    matched: list, nxt, verdict, rank=None) -> tuple
    # same signature; results are (ResultLine, answers) pairs; events carry request_id and session_id,
    # choices and reason (derived); no "request", "answers" or "models" key

def quality_settings(dry_run: bool) -> BatchSettings   # BatchSettings("plan", 1, QUALITY_PREFIX, DEFAULT_THRESHOLD, dry_run)
```

jev_runs:

```python
def read_run_events(run_name: str, log_file: pathlib.Path) -> Result[dict, ClientError]       # log_file required: no hard-coded path
def rebuild_from_log(run_name: str, tree: Any, repository: Optional[str] = None, *,
                     log_file: pathlib.Path) -> Result[list, ClientError]
    # result events -> decidr_client.answers_for(lines) -> {request_id: answers} -> run_triples
def run_triples(tree: Any, run: dict, result_lines: list, walk: dict) -> list           # unchanged; lines carry "answers" merged by the caller
```

CLI: `--model` (default `None`, help "model selector; default from config") on `batch`, `quality`, `compare-definition`, `drift`; `quality --no-cache`. `--max-workers` default `None` (help "parallel requests; default from config"). Error ids: no new ids. Used: `VALIDATION.INPUT` (answers-file envelope), `POLICY.REMOTE_JUDGE_DISABLED` (client gate), `DEPENDENCY.SC_DECIDR` (`open_run`/`load_wheel` Err), `LOG.READ` (rebuild), `CANCELED` (template `run_main`).

## Replaces (each item; what is deleted with it)

| item | replaces (file:line) | deleted with it |
|---|---|---|
| fresh render of decidr_client.py.j2 | S/decidr_client.py.j2 (659, 1.0.0 render) | the old render |
| decidr_client imports | S/result.py.j2:27-126 (Ok/Err/Result/ToolError/err/utf8_stdio/run_main) and its 6 importers; jj:99-104 | S/result.py.j2 whole file (126); `BATCH_MAX_WORKERS`, `BATCH_RETRIES as BATCH_FIXTURE_RETRY_LIMIT`, `CANCELED_EXIT`, `canceled_envelope` imports |
| template `redact_secrets` (inside `encode_result_line` and `call_*`) | S/jev_errors.py.j2:17-59 `redact_sensitive`, jj:100, uses jj:215, :949, :973, :1003, :1648, :1653, :1884, :2252, :2617 | S/jev_errors.py.j2 whole file (59) incl. the direct `TYPESAFE_API_KEY` read :24; `emit`/event/stderr calls use `decidr_client.redact_secrets` |
| `batch_verdict` (typed `verdict=` callback) | jj:851-857 `batch_verdict_fields` (dict) | the dict merge of tool keys into the line |
| `judge_batch` over `run_batch` | jj:860-893 `_batch_result_line`, `run_batch_job`; jj:953-984 `_live_batch_results`; jj:987-1005 old `judge_batch` | fixture attempt loop, `FIXTURE_RETRYABLE_CODES` jj:807-808, `ATTEMPT_MESSAGE_LIMIT` jj:134, two pump paths, `call_batch_results(on_result=persist, general_log=log, model=, timeout_secs=, workers=)` |
| `open_command_run` | jj:923-928 `open_run_log` (`decidr_client._logger`), `stamp` jj:231-232 (run name default) | `open_run_log`, `stamp`; run name default becomes `run.run_id` |
| `result_event`, `log_result_line` on `log_event(run, ...)` | jj:931-950 and every `sc_agent.log`/`sc_agent.flush`/`import sc_agent` in jj (:946-950, :1503, :1593-1659, :1820-1890, :2235-2253) `result_line_events` (request, answer, result events) | request and answer events (REQ-JEV-0212 owner ruling: no per-request event; ADR-JEV-0007 l.402-405) |
| client consent gate (inside `run_batch`) | 4 `remote_preflight` blocks jj:1042-1049, :1520-1527, :1857-1864, :2209-2213 | the 4 blocks |
| `run_batch` fixture coverage | `check_fixture_coverage` calls jj:1035-1037, :1626-1631, :2195-2197 | 3 call sites |
| `run_low_layer` (same signature) | jj:1008-1062 | dict `["ok"]` reads, `remote_preflight`, `streamed_result` |
| `--model default=None` on 4 commands | `DEFAULT_MODEL` jj:125, `add_stream_options` jj:1078; quality/compare/drift hard-code `DEFAULT_MODEL` in `quality_settings` jj:1387-1388 and drift jj:2184 | `DEFAULT_MODEL`; BatchSettings `model/timeout/max_workers` args |
| `quality --no-cache` → `open_command_run(cache=False)` | none in code; ADR-JEV-0001 l.41-43 and REQ-JEV-0209 require it | new capability (counted separately) |
| `wave_log_events` without answers/request/models | jj:1553-1585 (`answering_models`, `"answers"`, `"request"` keys) | `answering_models` jj:1553-1556 |
| `walk_tree(run=)` | jj:1593-1659 own `check_fixture_coverage` + `judge_batch(..., log, ...)` | coverage block, `result["answers"]`/`result["ok"]` dict reads |
| `FixtureError`/list envelope | jj:602-624 `FixtureError` and list branch of `_fixture_problems` | see rule-7 item 2 (deleted only if Rand confirms) |
| `read_run_events(log_file)` required | jev_runs:266-268 hard-coded `~/.sc-agent/logs/judge-jev.log.jsonl` | the path literal (ANC-015) |
| `rebuild_from_log` via `answers_for` | jev_runs:205-206 `decidr_client.json_answers(result_lines)` (answers read from /1 lines) | /1 reader (ANC-002/003) |
| port docstring | jev_ports:72 `jev_judge.pump_batch` | stale name |
| (none) | assets/schemas/jev-batch-result.schema.json | file (ADR-JEV-0007 l.391-395) |
| integration runner haiku/luna | scripts/integration.py:44-47 (`TypeSafe key is required`) | the hard requirement; new capability for the haiku/luna cases |

## External contracts (examples)

stdout line (`batch`, one per job, index order; the template writes it):
```json
{"schema":"jev-batch-result/2","tool":"judge-jev","tool_version":"0.8.0","run_id":"01KC...","session_id":"01KC...",
 "request_id":"batch/I-1/ANC-001/c1/r1","project":"judge-jev","agent_role":"judge-jev","threshold":0.6,
 "verdict":"pass","min_confidence":0.82,"leaning":"pass","ok":true,"error":null}
```
`result` event in `<JUDGE_JEV_LOG_ROOT|~/.sc-agent>/logs/judge-jev.log.jsonl` (judge-jev's record; ids reference the session row):
```json
{"target":"judge-jev.batch","action":"result","correlation_id":"01KC...","fields":{"run":"nightly","run_id":"01KC...",
 "session_id":"01KC...","request_id":"quality/REQ-JEV-0002/n1/r1","item_id":"REQ-JEV-0002","anchor_id":null,
 "candidate_id":"n1","repeat":1,"verdict":null,"ok":true,"error":null,"record_id":"REQ-JEV-0002",
 "tree_sha256":"...","definitions":[{"iri":"...","sha256":"..."}]}}
```
Fixture run (`--answers-file`): same events through a real Run, `session_id` null, nothing sent. Dry run: no Run, no line, no event (REQ-JEV-0208). CLI: `jev_judge.py quality --req REQ-JEV-0002 --model haiku --no-cache`; `jev_judge.py batch --input req.jsonl --model luna --max-workers 4`.

## Deletions (file:line at 031a61f)

- Files: S/result.py.j2 (126), S/jev_errors.py.j2 (59), assets/schemas/jev-batch-result.schema.json, T/test_result.py, T/test_jev_error_contracts.py.
- jj: :99-104 imports, :125, :134, :231-232, :602-624 (rule-7 item 2), :807-808, :851-893, :923-950, :953-1005, :1035-1037, :1042-1049, :1520-1527, :1553-1556, :1626-1631, :1857-1864, :2195-2197, :2209-2213; `"model"` in `batch_jobs` body :843.
- jev_runs: :205-206, :268 path literal. jev_ports:72 name.
- Tests: T/test_jev_batch.py retry-policy and attempts cases; T/test_jev_result.py helper tests now covered by the template; T/test_decidr_client.py client-internal tests (kept: render equality); T/test_no_plugin_env_vars.py `TYPESAFE_API_KEY` allowance (:40, :44-46).

## Done checks

- Build: `sc-compose render --strict` of the template equals S/decidr_client.py.j2 (`test_client_equals_fresh_strict_render_of_installed_template`); `python3 -m compileall` on rendered scripts.
- Tests (`python -m pytest tests/sc-judge-jev -q` with the j-4 prerelease wheel; every Run is `sc_agent.testing.fake_open_run` or the real wheel on a loopback `http.server` at 127.0.0.1:0; `JUDGE_JEV_LOG_ROOT` per test; no sleeps, timing or HOME writes): T/test_client_run.py `test_each_sending_command_opens_one_run_with_its_timeout_and_workers`, `test_model_is_passed_unchanged_and_absent_model_passes_none`, `test_every_line_and_event_carries_the_run_id`, `test_dry_run_opens_no_run_and_writes_no_event`, `test_events_hold_no_request_answers_or_models`, `test_quality_no_cache_opens_run_with_cache_false`, `test_lines_match_wheel_schema_and_share_run_id` (real wheel, 3 lines), `test_result_event_holds_tool_ids_and_session_id`, `test_consent_only_for_typesafe` (real wheel), `test_canaries_absent_from_stdout_and_events`, `test_rebuild_reads_answers_through_answers_for`; T/test_decidr_client.py `test_scripts_import_with_result_module_absent`; T/test_no_plugin_env_vars.py `test_only_listed_variables_are_read`; T/test_jev_batch.py `test_fixture_batch_runs_through_a_run_and_logs_result_events`.
- Greps: the Goal grep; `find plugins/sc-judge-jev -name jev-batch-result.schema.json` empty; `grep -rnE '"(jev-latest|haiku|luna)"|provider=' S/` empty.
- Records: `python scripts/extract.py` 0 issues; `python scripts/check_version_sync.py` exits 0 (VERSION 0.8.0).
- Gate: sc-agent `scripts/gate/rewrite.py` unchanged by j-6 (0 Rust lines).

## Budget

Phase Rust: 0 lines from j-6 (cap 2,500 untouched). judge-jev production Python (S/*.py.j2 without decidr_client = 5,103 measured, plus scripts/integration.py 119 = 5,222): deletions of copies the template replaces ≈ −185 (two files) and ≈ −190 in jev_judge/jev_runs (pump, attempts, consent blocks, coverage calls, request/answer events, log opener, stamp, model constant); restructure (open_command_run, judge_batch wrapper, result_event, batch_verdict, imports) ≈ +60 against those, so net ≈ −315, restructure ≤ 0. New capability counted separately: `--model` on 3 more commands, `--no-cache`, integration haiku/luna ≈ +30. decidr_client.py.j2 is generated and counted in j-4 (delta reported, 659 → render). Tests: net negative (attempt/retry/client-internal tests deleted; T/test_client_run.py added).

## Plan decisions (rule 0, no question to Rand)

1. judge-jev's own events go through the Run it already holds (rule 0: the tool's logger comes through its client). j-4's surface has no such accessor, so j-6 needs this j-4 addition (not in j-4's plan yet):
   `def log_event(run: Any, target: str, action: str, correlation_id: str | None, fields: Mapping[str, Any]) -> Result[None, ClientError]` -- `redact_secrets(fields)`, then `run.log({"target": target, "action": action, "correlation_id": correlation_id, "fields": ...})` and flush on the Run's own logger; Err(`DEPENDENCY.SC_DECIDR` / the wheel's `log.*` error). It needs the wheel's `PyRun.log(event: dict) -> Envelope` (the Run's logger through j-3's kept `pub fn log(logger, action, fields)`; new capability, about +8 Rust). Tests redirect with `JUDGE_JEV_LOG_ROOT`.
2. `abort_on={"auth"}` kept (core unchanged, ADR-JEV-0001); passed to `run_batch`.
3. Run name default = `run.run_id` (replaces `stamp()`); `--run-name` still overrides; compare-definition keeps `<run>.with`/`<run>.without` as fields under one Run.
4. Records need no edit except rule-7 item 2: the trim on plan/phase-j already landed the old J6-16 deletions and ADR-JEV-0007's `/2` text.

## Rule-7 items

1. Rebuild from fixture runs. ADR-JEV-0007 l.405-407: "A rebuild reads answers through the adopted client's `answers_for` ... judge-jev reads no session-log file"; j-4: a fixture run's lines have `session_id` null, so `answers_for` has nothing to read. Tests that rebuild from `--answers-file` runs (T/test_graph_runs.py RunCase.run_quality, T/test_rule_rank_record_iri.py, T/test_definitions.py rebuild cases) cannot pass unchanged. Proposed: those tests drive the real wheel through a loopback stub that serves the recorded answers (offline, NFR-JEV-0001), so session rows exist; cost ≈ +40 test lines.
2. REQ-JEV-0210 (prose-evaluation.md:462-463) "each key's value to be an object or a non-empty list of objects" conflicts with j-4 `fixture_answer` (one answer or one error; list entries deleted) and the 2026-11-24 owner approval "fixture-attempts-removed". Proposed: conflict deletion of "or a non-empty list of objects" on develop; a list becomes `VALIDATION.INPUT`; jj:602-624 shrink accordingly.
