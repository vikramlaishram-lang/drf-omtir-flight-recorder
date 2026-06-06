from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any


LIVE_PROPOSAL_PROMPT = (
    "Return exactly one JSON object and no prose. The JSON object must match this schema: "
    '{"intent":"propose_action","action":"search_logs | read_metrics | restart_service | delete_index",'
    '"arguments":{}}. Choose one action for a bounded DevOps diagnosis step.'
)

STRICT_LIVE_PROPOSAL_PROMPT = (
    "Your previous response was not valid JSON. Return only one JSON object. No markdown. No prose. "
    'Example: {"intent":"propose_action","action":"search_logs","arguments":{"query":"error OR critical OR timeout"}}'
)


class MissingTrueFoundryConfig(RuntimeError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("Missing required TrueFoundry environment variables: " + ", ".join(missing))


class MalformedProposalError(RuntimeError):
    pass


class TrueFoundryClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrueFoundryProposal:
    raw_model_output: str
    raw_model_output_sha256: str
    parsed_proposal: dict[str, Any]
    model: str


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _extract_first_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    if start == -1:
        raise MalformedProposalError("Model response did not contain a JSON object.")
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]
    raise MalformedProposalError("Model response contained an unterminated JSON object.")


def parse_proposal(raw_model_output: str) -> dict[str, Any]:
    try:
        parsed = json.loads(_extract_first_json_object(raw_model_output))
    except json.JSONDecodeError as exc:
        raise MalformedProposalError(f"Model response JSON parsing failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise MalformedProposalError("Model response JSON root must be an object.")
    if parsed.get("intent") != "propose_action":
        raise MalformedProposalError("Model response intent must be propose_action.")
    action = parsed.get("action")
    if not isinstance(action, str) or not action:
        raise MalformedProposalError("Model response action must be a non-empty string.")
    arguments = parsed.get("arguments")
    if arguments is None:
        parsed["arguments"] = {}
    elif not isinstance(arguments, dict):
        raise MalformedProposalError("Model response arguments must be an object.")
    return parsed


def _response_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise TrueFoundryClientError("TrueFoundry response did not match OpenAI chat format.") from exc
    if not isinstance(content, str) or not content.strip():
        raise MalformedProposalError("TrueFoundry model response was empty.")
    return content


class TrueFoundryProposalClient:
    def __init__(self, *, gateway_url: str, api_key: str, model: str):
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_env(cls) -> "TrueFoundryProposalClient":
        required = ["TRUEFOUNDRY_GATEWAY_URL", "TRUEFOUNDRY_API_KEY", "TRUEFOUNDRY_MODEL"]
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise MissingTrueFoundryConfig(missing)
        return cls(
            gateway_url=os.environ["TRUEFOUNDRY_GATEWAY_URL"].strip(),
            api_key=os.environ["TRUEFOUNDRY_API_KEY"],
            model=os.environ["TRUEFOUNDRY_MODEL"].strip(),
        )

    def get_proposal(self) -> TrueFoundryProposal:
        raw = self._call_model(LIVE_PROPOSAL_PROMPT)
        try:
            parsed = parse_proposal(raw)
        except MalformedProposalError:
            raw = self._call_model(STRICT_LIVE_PROPOSAL_PROMPT)
            parsed = parse_proposal(raw)
        return TrueFoundryProposal(
            raw_model_output=raw,
            raw_model_output_sha256=_sha256_text(raw),
            parsed_proposal=parsed,
            model=self.model,
        )

    def _call_model(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TrueFoundryClientError("The openai package is required for live-proposal-demo.") from exc

        client = OpenAI(api_key=self.api_key, base_url=self.gateway_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You produce action proposals for a governance gateway. Return strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return _response_text(response)
