from __future__ import annotations

import json
import time
from pathlib import Path

from baseline.agent import _chat, _json_action, _observe
from driftdoctor.evidence import collect_evidence, compact_evidence

SYSTEM = '''You are DriftDoctor, an evidence-first dbt incident repair agent.
Use the structured evidence bundle before editing. Prefer the smallest safe repair that preserves downstream contracts.
You have list_files, read_file, write_file, run_command. Stay inside the project and do not use network access or hidden benchmark files.

Respond with exactly one JSON object per turn, no markdown:
{"action":"list_files"}
{"action":"read_file","path":"models/example.sql"}
{"action":"write_file","path":"models/example.sql","content":"complete replacement contents"}
{"action":"run_command","command":"dbt build --profiles-dir ."}
{"action":"final","root_cause_class":"short_label","hypothesis":"...","evidence":["..."],"changed_files":["..."],"verification":"..."}

Do not stop merely because dbt is green. Check whether the incident can be a silent semantic regression.'''

REVIEW = '''Act as an adversarial analytics-engineering verifier. Review the incident, evidence, current files, and latest dbt result.
If there is a plausible unresolved semantic defect, output JSON {"verdict":"retry","reason":"...","suggested_focus":"..."}.
If the repair is sufficiently supported by the visible evidence, output {"verdict":"accept","reason":"..."}.
Do not invent hidden requirements.'''


def run_driftdoctor(root: Path, incident: str, model: str, max_steps: int = 14, max_retries: int = 2, command_timeout: int = 90) -> dict:
    root = root.resolve()
    initial_evidence = collect_evidence(root)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Incident:\n{incident}\n\nStructured evidence:\n{compact_evidence(initial_evidence)}\n\nStart with a root-cause hypothesis, then repair."},
    ]
    trajectory = []
    final = None
    final_evidence = initial_evidence
    started = time.monotonic()
    retries = 0
    model_calls = 0
    index = 0

    while model_calls < max_steps:
        index += 1
        text = _chat(model, messages)
        model_calls += 1
        action = _json_action(text)
        if action.get("action") == "final":
            latest = collect_evidence(root)
            final_evidence = latest
            if model_calls >= max_steps:
                trajectory.append({"index": index, "type": "final", "model_output": text, "action": action, "review": {"verdict": "budget_exhausted"}})
                final = action
                break

            review_text = _chat(model, [
                {"role": "system", "content": REVIEW},
                {"role": "user", "content": f"Incident:\n{incident}\n\nLatest evidence:\n{compact_evidence(latest)}\n\nAgent final:\n{json.dumps(action)}"},
            ])
            model_calls += 1
            review = _json_action(review_text)
            trajectory.append({"index": index, "type": "final_review", "model_output": text, "action": action, "review_output": review_text, "review": review})
            if review.get("verdict") == "retry" and retries < max_retries and model_calls < max_steps:
                retries += 1
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": "Verifier requested another attempt: " + str(review.get("reason")) + "\nFocus: " + str(review.get("suggested_focus"))})
                continue
            final = action
            break

        observation = _observe(root, action, command_timeout)
        trajectory.append({"index": index, "type": "tool", "model_output": text, "action": action, "observation": observation})
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Tool observation:\n" + observation + "\nReturn the next JSON action."})

    return {
        "system": "driftdoctor-v0.1",
        "model": model,
        "max_model_calls": max_steps,
        "model_calls": model_calls,
        "max_retries": max_retries,
        "retries": retries,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "initial_evidence": initial_evidence,
        "final_evidence": final_evidence,
        "final": final,
        "steps": trajectory,
    }
