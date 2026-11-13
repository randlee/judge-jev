"""Insert a Definitions paragraph at the top of each named record's Requirement Statement."""
import re, sys, textwrap
from pathlib import Path

ROOT = Path(sys.argv[1])
JEV = ("Jev is TypeSafe's hosted judge model: it answers each multiple-choice "
       "question about a text with one choice and a confidence from 0 to 1. "
       "A Jev request is one call to it.")
RAPTOR = ("Raptor is the requirements tool that imports Markdown records into "
          "its record store and serves them to other tools (ADR-JEV-0002).")
RECORD = ("A record is one requirement (REQ), non-functional requirement (NFR) "
          "or architecture decision record (ADR) as Raptor imports it; REQ, NFR "
          "and ADR are its record kinds.")
LOCATION = ("A location is the text judged against a record: a whole file "
            "(`path`), a Markdown section (`path#Heading`) or a code symbol "
            "(`path::Symbol`) (REQ-JEV-0207).")
MODE = ("A mode (target mode) names what a location holds: `prompt` (prompt "
        "text), `skill` (a skill file), `task` (a task template) or `code` "
        "(source code).")
QSET = ("A question set is the data file of questions judge-jev sends to Jev "
        "about a location for one record kind and target class.")
QTREE = ("A quality decision tree is the data file of questions that judges "
         "whether a record is well written: waves of questions, with rules that "
         "turn Jev's answers into the next wave or a verdict (REQ-JEV-0101).")
PROFILE = ("A profile is a TOML file listing locations, each with its mode and "
           "the ids of the records that govern it (REQ-JEV-0204).")
PAIR = "A pair is one (record, location) pair."
SCO = ("The sc-observability logger is the JSON-lines logger of the "
       "sc-observability package (version 1.5.0), which writes "
       "`.sc/judge-jev/logs/judge-jev.log.jsonl`.")
SCAGENT = ("sc-agent is the agent tool whose Rust Jev tool will replace "
           "judge-jev's Python Jev core (ADR-JEV-0007).")
TSG = ("Tree-sitter grammars are the parsers that find a named symbol in "
       "source code.")
TYPED = ("A typed error is a JSON error object with a stable `code` (such as "
         "`INPUT.MALFORMED`), a `message` and a `suggested_action`.")
DIGEST = "A digest is the SHA-256 of the bytes it covers."

DEFS = {
"REQ-JEV-0201": [RECORD, LOCATION, MODE, QSET,
    "`--profile` names a profile: a TOML file listing locations, each with "
    "its mode and the ids of the records that govern it (REQ-JEV-0204)."],
"REQ-JEV-0202": [JEV, RECORD, LOCATION, PAIR,
    "A stream of single requests is a sequence of Jev requests, one per "
    "pair, sent one at a time through the batch command (REQ-JEV-0002)."],
"REQ-JEV-0203": [MODE, LOCATION,
    "sc-compose is the template renderer; in strict mode it fails on any "
    "template variable the vars file does not set. A vars file holds the "
    "values of a template's variables. An assignment is the text a task "
    "template renders to.", SCAGENT, TSG],
"REQ-JEV-0204": [
    "TOML is Tom's Obvious Minimal Language, a configuration file format.",
    "A profile is a TOML file listing locations, each with its mode and "
    "the ids of the records that govern it.", LOCATION, MODE, PAIR,
    "A vars file holds the values of a task template's variables."],
"REQ-JEV-0205": [RECORD, QSET.replace("about a location ", "about a location "),
    "A target class is agent text (modes `prompt`, `skill` and `task`) or "
    "code (mode `code`).", QTREE,
    "A question-set id is the `id` field of a question set or tree file. "
    "The content digest of a file is the SHA-256 of its bytes. A log entry "
    "is one event a run writes through the sc-observability logger "
    "(REQ-JEV-0008)."],
"REQ-JEV-0207": [
    "Raptor is the requirements tool that imports Markdown records; its "
    "rules decide which text belongs to which heading.", SCAGENT, TSG],
"REQ-JEV-0208": [JEV, RAPTOR,
    "A dry run is a run with `--dry-run`: it composes every request and "
    "sends none. A dry-run entry is its report of one request a live run "
    "would send. A composed request is the full JSON body judge-jev would "
    "send to Jev. The record's Raptor source is the Raptor index the record "
    "was read from.", LOCATION.replace("A location", "A location (resolved: its path, section or symbol)"),
    "The digest of a text is its SHA-256.", MODE,
    "A question set is the data file of questions sent to Jev; its shipped "
    "id is the `id` of a set shipped with the tool, its override path the "
    "file given with `--questions`. A vars file holds the values of a task "
    "template's variables.",
    "The request limit is 24000 bytes by default.",
    QTREE + " The wave-1 request is the request for its first wave.", TYPED],
"REQ-JEV-0209": [
    "A run name is the name every log event of one invocation carries "
    "(`--run-name`)."],
"REQ-JEV-0001": [RAPTOR +
    " Its query interface is the way Raptor hands records to another tool."],
"REQ-JEV-0002": [JEV,
    "The batch command is `jev_judge.py batch`: it reads request lines (one "
    "JSON request per line), sends each to Jev and writes a result line. A "
    "result envelope is the JSON result line for one request, holding its "
    "answers or its error (`assets/schemas/jev-batch-result.schema.json`). "
    "A typed error code is a stable dotted code naming a failure, such as "
    "`JEV.NETWORK` or `JEV.RATE_LIMITED`.",
    "The fixed retry policy is one retry of a call that failed with a "
    "recoverable or transient error (`JEV.RATE_LIMITED`, `JEV.OVERLOADED`, "
    "`JEV.NETWORK`, `JEV.RESPONSE_INVALID`), after the response's "
    "Retry-After delay capped at 30 seconds, or after 1 second without one.",
    "The request size limit is the `--max-request-bytes` value, at most "
    "64000 bytes; by default 24000 bytes with `--gate plan` and 64000 bytes "
    "with `--gate dev`.", SCO],
"REQ-JEV-0003": [
    "TypeSafe is the company whose API (application programming interface) "
    "serves Jev, the judge model; the TypeSafe API key authenticates calls "
    "to it. The platform credential store is the macOS Keychain, the "
    "Windows Credential Manager or, on Linux, the Secret Service "
    "(`secret-tool`)."],
"REQ-JEV-0004": [JEV,
    "A live Jev call is a request sent to Jev, as opposed to a dry run or "
    "an answers file. `POLICY.REMOTE_JUDGE_DISABLED` is the typed error "
    "code for a refused live call."],
"REQ-JEV-0005": [
    "A harness is an agent tool judge-jev installs into: Claude (Claude "
    "Code), Codex or Cursor. A marketplace plugin is a plugin a harness "
    "installs from a plugin marketplace. A harness is locked when the "
    "install lock records it, installed when its `.<harness>/skills/judge-jev/` "
    "directory exists, and present when its `.<harness>/` directory exists "
    "in the repository. An upgrade is an install of a newer judge-jev "
    "version."],
"REQ-JEV-0006": [RAPTOR,
    "Raptor-parseable Markdown is Markdown in the record format Raptor's "
    "import reads. SQLite is a single-file SQL (Structured Query Language) "
    "database. Dolt is a SQL database with Git-style branches; a SQLite "
    "snapshot of a Dolt branch is a SQLite copy of that branch's records. "
    "The Raptor interface is the way Raptor hands records to another tool."],
"REQ-JEV-0007": [
    "Raptor is the requirements tool that imports Markdown records. An "
    "issue is a diagnostic Raptor's import reports for a record, such as "
    "`UNKNOWN_SECTION`."],
"REQ-JEV-0008": [SCO, SCAGENT,
    "A quality-tree branch is the next wave a quality decision tree's rules "
    "select from Jev's answers."],
"REQ-JEV-0101": [JEV, RAPTOR,
    "Diagnostics are the problems Raptor's import reports for a record, "
    "and the structure it checks is the record format.",
    "A quality decision tree is a data file of prompts (questions to Jev) "
    "in waves; a wave is one set of questions, and its reason is the "
    "report of its questions and Jev's answers. A per-statement wave asks "
    "its questions once for each MUST and MUST NOT statement. A verdict "
    "rule is a rule in the tree file that turns a wave's answers into a "
    "verdict (`yes` or `no`). The walk is the sequence of waves from the "
    "first to the one that gives the verdict; its decision-tree path is "
    "the list of those waves' ids. A consumer is a repository that uses "
    "judge-jev."],
"NFR-JEV-0001": [JEV,
    "Recorded Jev answers are an answers file (`--answers-file`): JSON "
    "answers given to judge-jev in place of a live Jev call."],
"REQ-JEV-0210": [JEV,
    "The model for an input kind is the Pydantic model (a typed schema "
    "class) judge-jev validates that input with (ADR-JEV-0005). A field "
    "path is the dotted path of keys and list indexes to the refused "
    "field, such as `nodes.wave-1.questions.context.criteria`.",
    "An answers file is a JSON file of Jev's answers, keyed by request, "
    "that `--answers-file` gives judge-jev in place of a live call. Its "
    "envelope is its outer structure: its keys and the type of each value. "
    "`JEV.RESPONSE_INVALID` is the typed error code for an answer whose "
    "questions, choices or probabilities do not match the request."],
"REQ-JEV-0211": [JEV,
    "A `judge-jev` command's result is the JSON object it prints on "
    "success. " + TYPED,
    "A tree is a quality decision tree file, a question set a file of "
    "questions, an index a Raptor import index, a request stream the "
    "request lines of the batch command, and a run directory the folder "
    "that holds a run's log.",
    "A log event is one event written through the sc-observability logger; "
    "the logger's event size limit is 65536 bytes (sc-observability 1.5.0)."],
"REQ-JEV-0212": [
    "A definition is a term with its meaning, from a "
    "`.sc/judge-jev/*.definitions.ttl` file (ADR-JEV-0008). It is attached "
    "to a record, or to a record and a location (the file, Markdown section "
    "or code symbol being judged). A request's state is the data it sends "
    "to Jev next to the questions, which holds the record. The size limit "
    "of a request is 24000 bytes. A definition's digest is the SHA-256 of "
    "its term, text and source."],
"REQ-JEV-0213": [
    "A definition is a term with its meaning, attached to a record "
    "(ADR-JEV-0008); a candidate definition is one being tested. The "
    "comparison is `judge-jev compare-definition`. The requests a candidate "
    "would reach are the requests about the records it is attached to. An "
    "answer is Jev's choice for one question, with its confidence from 0 to "
    "1. The decision threshold is 0.6 unless `--threshold` sets it; a "
    "confidence at or above it decides."],
"REQ-JEV-0214": [
    "A question IRI (Internationalized Resource Identifier) is the URN that "
    "names a question, such as `urn:judge-jev:question:req.term`. A tree "
    "file is a Turtle file of quality decision trees. A consumer extension "
    "is a tree file that a repository using judge-jev adds. `jj:id` is a "
    "question's short id within its tree."],
"REQ-JEV-0215": [JEV,
    "The scope is the trees and question sets shipped with judge-jev, the "
    "tree and definitions files at the top level of `.sc/judge-jev/`, and "
    "each path given to `judge-jev doctor`. A tree is a quality decision "
    "tree file; a question set is a file of questions; a definitions file "
    "is a `.definitions.ttl` file of definitions, each a term with its "
    "meaning and the `source` file it comes from. A file's schema is the "
    "model that checks its fields. The ontology's shapes are the SHACL "
    "(Shapes Constraint Language) files in `assets/shapes/`; an edge is a "
    "link from one node of a tree to another, and a cycle is a chain of "
    "edges that leads back to its start. An attachment links a definition "
    "to a record, or to a record and a location (a file, Markdown section "
    "or code symbol). The Raptor index is the record file Raptor's import "
    "writes."],
}

def para(sentences):
    return textwrap.fill("Definitions: " + " ".join(sentences), width=76, break_on_hyphens=False, break_long_words=False) + "\n\n"

for path in sorted((ROOT / "docs/requirements").glob("*.md")):
    text = path.read_text(encoding="utf-8")
    for rid, sents in DEFS.items():
        m = re.search(r"^## " + re.escape(rid) + r":.*?^### Requirement Statement\n\n", text, re.S | re.M)
        if not m:
            continue
        rest = text[m.end():]
        if rest.startswith("Definitions:"):
            end = rest.index("\n\n") + 2
            text = text[:m.end()] + para(sents) + rest[end:]
        else:
            text = text[:m.end()] + para(sents) + rest
    path.write_text(text, encoding="utf-8")
