# Iteration 2 addendum (read after proposer-brief.md)

Every statement of every record now passes in 6 of 6 runs. An added definition or a reword can no longer lower the failure count, and a confidence gain on a passing answer is not counted as an improvement. So in this iteration propose ONLY type `remove` tweaks (deletions, `new` may also be a shorter replacement of the same span that drops words without changing meaning, but then use type `reword` and say "shortening" in `why`).

Targets:
- a definition, or part of one, that defines a term no MUST/MUST NOT statement uses, or a term Jev reads as common usage;
- a definition clause that repeats what another definition in the record already says;
- example values, version numbers, vendor names, file paths or parentheticals inside a definition that no statement relies on;
- record-id citations inside a definition that duplicate a citation already in a statement.
Do NOT remove anything from the MUST/MUST NOT statements themselves (the author rejects any tweak that drops a code span, number or record id from a statement), and do not touch Rationale quotes from Rand.
The author already tries removing each whole definition sentence one by one; your value is in partial-sentence removals and in removals that span two sentences that only make sense together.
Aim for 3 to 6 tweaks per record that has a Definitions paragraph.
