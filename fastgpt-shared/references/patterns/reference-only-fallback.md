# Pattern: reference-only / explicit fallback

Use this pattern when the source system distinguishes between:
- direct primary evidence hit
- supporting/reference-only evidence
- no reliable evidence

## Rules

- If the target primary evidence is missing, say so explicitly.
- Do not present secondary evidence as if it were the requested target text.
- Encode fallback mode in workflow state so the final answer prompt can behave differently.
- Friendly fallback is still a deliverable: give a conservative, practical judgment/framework first, then explain the evidence boundary.
- When the missing piece is about permissions, qualifications, responsibilities, or other high-risk constraints, do **not** infer that conclusion from device conditions or generic process clauses alone.
- Avoid cold “system failed / not found” wording; state what the current evidence does cover, what it does not cover, and what additional project/system inputs are needed.

## Typical implementation

1. Rank or judge evidence quality.
2. Compute a boolean or enum such as `answerMode=primary_first|reference_only|no_answer`.
3. Route the final `chatNode` prompt based on that mode.
4. Include explicit wording that the target clause/standard was not directly hit when applicable.
5. If the risk comes from adjacent evidence only, downgrade to a conservative boundary mode rather than manufacturing a strong answer from supporting chunks.
