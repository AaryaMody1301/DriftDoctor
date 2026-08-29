from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Step:
    index: int
    model_output: str
    action: dict
    observation: str
    elapsed_seconds: float


SYSTEM = '''You are a coding agent responsible for repairing a broken dbt project.
You are given a local project directory and an incident description. Inspect the project, run any available local commands you think are useful, identify the root cause, and make the code or configuration changes needed to fix the incident.
Do not access external systems, deploy anything, or modify files outside the provided project directory.
When you believe the incident is fixed, stop and provide your primary root-cause class, a concise explanation, changed files, and verification performed.

You have four tools. Respond with exactly one JSON object per turn, no markdown:
{"action":"list_files"}
{"action":"read_file","path":"models/example.sql"}
{"action":"write_file","path":"models/example.sql","content":"complete replacement contents"}
{"action":"run_command","command":"dbt build --profiles-dir ."}
{"action":"final","root_cause_class":"short_label","explanation":"...","changed_files":["..."],"verification":"..."}'''


def _chat(model: str, messages: list[dict], timeout: int = 180) -> str:
    payload = json.dumps({"model": model, "messages": messages, "stream": False, "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(
        os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat"),
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    return data["message"]["content"]


def _json_action(text: str) -> dict:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            value = json.loads(match.group(0))
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    return {"action": "invalid", "raw": text[:2000]}


def _safe_path(root: Path, raw: str) -> Path:
    target = (root / raw).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path escapes project directory")
    return target


def _observe(root: Path, action: dict, command_timeout: int) -> str:
    kind = action.get("action")
    if kind == "list_files":
        files = []
        for p in sorted(root.rglob("*")):
            if p.is_file() and not any(part in {"target", "logs", ".git"} for part in p.parts):
                files.append(str(p.relative_to(root)))
        return "\n".join(files[:300])
    if kind == "read_file":
        p = _safe_path(root, str(action.get("path", "")))
        return p.read_text(errors="replace")[:20000]
    if kind == "write_file":
        p = _safe_path(root, str(action.get("path", "")))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(action.get("content", "")))
        return f"wrote {p.relative_to(root)}"
    if kind == "run_command":
        command = str(action.get("command", ""))
        lowered = command.lower()
        forbidden = [
            "curl ", "wget ", "http://", "https://", "ssh ", "scp ",
            "../", "/home/", "benchmark/", "cases.json", "oracles.py", "reference_repairs",
        ]
        if any(x in lowered for x in forbidden):
            return "command rejected: external/hidden benchmark access is disabled"
        try:
            proc = subprocess.run(command, cwd=root, shell=True, text=True, capture_output=True, timeout=command_timeout)
            output = f"returncode={proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            return output[-20000:]
        except subprocess.TimeoutExpired:
            return f"command timed out after {command_timeout}s"
    return "invalid action; return one of list_files/read_file/write_file/run_command/final"


def run_baseline(root: Path, incident: str, model: str, max_steps: int = 14, command_timeout: int = 90) -> dict:
    root = root.resolve()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Incident:\n" + incident},
    ]
    steps: list[Step] = []
    final: dict | None = None
    started = time.monotonic()

    for index in range(1, max_steps + 1):
        turn_started = time.monotonic()
        text = _chat(model, messages)
        action = _json_action(text)
        if action.get("action") == "final":
            final = action
            steps.append(Step(index, text, action, "agent declared completion", time.monotonic() - turn_started))
            break
        observation = _observe(root, action, command_timeout)
        steps.append(Step(index, text, action, observation, time.monotonic() - turn_started))
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Tool observation:\n" + observation + "\nReturn the next JSON action."})

    return {
        "model": model,
        "max_steps": max_steps,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "final": final,
        "steps": [asdict(s) for s in steps],
    }
