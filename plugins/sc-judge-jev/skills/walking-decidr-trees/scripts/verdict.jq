if .ok == false then error(.error | tojson)
elif .verdict == "yes" and .stage == "gates" then .
elif .ok == true then
  .value as $value
  | $value.answers.which_part as $answer
  | if $answer.type != "choice" or ($answer.choice | type != "string")
       or ($answer.confidence | type != "number")
       or $answer.confidence < 0 or $answer.confidence > 1
    then error("Missing or invalid which_part answer")
    else {verdict: "review", stage: "which-part", which_part: $answer.choice,
          confidence: $answer.confidence, model: $value.model}
    end
else error("Expected a decidr result or a gate leaf")
end
