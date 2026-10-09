# Eval suite

Run with Claude Code 2.1.269 or later. Every eval run is a real model call and counts against your plan or API bill.

```bash
# skill-routing check (cheap graders, one arm):
claude plugin eval . --tag trigger --ablation none --runs 1 --threshold 0.8
```

`triggers/` holds one case per headline skill, phrased the way a user would ask without naming the skill, plus one unrelated request that must NOT invoke the plugin. A failing trigger case means the skill's `description` / `when_to_use` no longer routes natural requests to it. Results land in `evals/results/` (gitignored).

Every case sets `max_turns: 1`. The graders only check that the model's first action is the right skill, and that Skill call is already in the trace after one turn; at `max_turns: 2` or 4 runs kept going (the model launched a subagent and read long references) and cost several times more with no extra routing signal. The trade-off is that stay-quiet cases are slightly weaker at one turn, because a wrong skill call that would only come in a second turn is not seen.
