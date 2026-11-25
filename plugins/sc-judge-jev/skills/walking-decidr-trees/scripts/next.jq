# Inputs: one decidr result, --slurpfile item item.json,
# --slurpfile terms terms.json, --argjson bar 0.8.
def valid_answer($choices):
  .type == "choice" and (.choice as $c | $choices | index($c) != null)
  and (.confidence | type == "number" and . >= 0 and . <= 1);

if .ok == false then error(.error | tojson)
elif .ok != true then error("Expected a decidr ok envelope")
elif ($bar | type != "number") or $bar < 0 or $bar > 1 then error("bar must be in [0,1]")
elif ($item | length) != 1 or ($terms | length) != 1 then error("Supply one item and one terms array")
else
  # An optional --slurpfile tree supplies the example's ADR/NFR gate policy.
  # The original REQ-SAG-0104 pipeline keeps its default three gates.
  ($ARGS.named.tree // [null])[0] as $tree
  | ($tree.nodes.gates.policy // [
      {id: "obligations", pass: "1", choices: ["1", "2", "3", "4+"]},
      {id: "term", pass: "yes", choices: ["yes", "no"]},
      {id: "checkable", pass: "yes", choices: ["yes", "needs a measure", "no"]}
    ]) as $policy
  | .value.answers as $a
  | if ($policy | length) > 0 and all($policy[]; . as $gate | $a[$gate.id] | valid_answer($gate.choices))
    then . else error("Missing or invalid gate answer") end
  | $policy
  | map(. as $gate | $a[$gate.id] as $answer
      | select($answer.choice != $gate.pass or $answer.confidence < $bar)
      | {question: $gate.id, answer: $answer,
         cause: (if $answer.choice != $gate.pass then "choice" else "confidence" end)})
  | if length == 0 then
      {verdict: "yes", stage: "gates", item: $item[0].id}
    else
      .[0] as $failed
      | {state: {item: $item[0], gate: $failed, bar: $bar},
         questions: ($tree.nodes["which-part"].questions // {which_part: {
           type: "choice",
           instructions: ("`item.text` is JSON with statement and record. The gate "
             + ($failed | tojson)
             + " did not meet the bar. Which part of the statement accounts for that answer or uncertainty? "
             + "Select one literal term; choose none if no listed term accounts for it. "
             + "Use record as context; do not invent an explanation."),
           criteria: ($terms[0] | map({key: ., value:
             (if . == "none" then "No listed term accounts for the gate answer or uncertainty."
              else "The literal term `" + . + "` accounts for the gate answer or uncertainty." end)}) | from_entries)
         }})}
    end
end
