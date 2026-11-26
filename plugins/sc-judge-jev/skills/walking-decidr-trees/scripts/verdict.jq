if .ok == false then error(.error | tojson)
elif .verdict == "yes" and .stage == "gates" then .
elif .ok == true then
  .value as $value
  | $value.answers.which_part as $answer
  | ($answer.probabilities // {}) as $p
  | if $answer.type != "choice" or ($answer.choice | type != "string")
       or ($answer.confidence | type != "number")
       or $answer.confidence < 0 or $answer.confidence > 1
       or ($p | type != "object")
       or (all($p[]; type == "number" and . >= 0 and . <= 1) | not)
    then error("Missing or invalid which_part answer")
    else ($answer.choice != "none" and ($p.none // 0) > 0
          and $p.none == $p[$answer.choice] and $p.none == ([$p[]] | max)) as $tie
    | {verdict: "review", stage: "which-part",
          which_part: (if $tie then "none" else $answer.choice end),
          model_choice: $answer.choice, tied_with_none: $tie,
          confidence: $answer.confidence, model: $value.model}
    end
else error("Expected a decidr result or a gate leaf")
end
