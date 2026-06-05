"""CaptchaHandler — detect and solve captchas via LLM vision + Playwright."""

import json
import re

from businessradar.llm_client import LLMClient
from businessradar.models import CaptchaType, SolveResult

# Types we can auto-solve
_SOLVABLE_TYPES = {"text", "arithmetic"}
# Types that require user intervention
_UNSOLVABLE_TYPES = {"recaptcha", "hcaptcha", "sms", "slider", "point_select"}

_DETECT_PROMPT = """\
Analyze this screenshot and determine if it contains a CAPTCHA challenge.

Respond ONLY with a JSON object (no markdown fences):
{
  "kind": "text|arithmetic|slider|point_select|recaptcha|hcaptcha|sms|none",
  "confidence": 0.0-1.0,
  "description": "brief description of what you see"
}

Types:
- text: image with distorted characters/letters to type
- arithmetic: math problem to solve (e.g. "3+5=?")
- slider: drag a piece to fill a gap
- point_select: click specific objects in an image grid
- recaptcha: Google reCAPTCHA ("I'm not a robot" checkbox or image grid)
- hcaptcha: hCaptcha challenge
- sms: SMS/phone verification required
- none: no captcha detected
"""

_SOLVE_PROMPT_TEMPLATE = """\
This is a CAPTCHA image of type: {kind}.
{extra_instruction}

Respond ONLY with the answer. No explanation, no quotes, just the raw answer.
"""


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response, handling markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    # Find first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in response: {text[:200]}")


class CaptchaHandler:
    """Detect and solve captchas using LLM vision analysis."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def detect(self, screenshot: bytes) -> CaptchaType:
        """Analyze a screenshot to detect if a captcha is present."""
        response = self._llm.call_vision(_DETECT_PROMPT, screenshot)
        try:
            data = _extract_json(response)
            return CaptchaType(
                kind=data.get("kind", "none"),
                confidence=data.get("confidence", 0.0),
                description=data.get("description", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return CaptchaType(kind="none", confidence=0.0, description="Failed to parse detection response")

    def solve(self, screenshot: bytes, captcha_type: CaptchaType) -> SolveResult:
        """Attempt to solve a detected captcha.

        Returns SolveResult with success=True and the answer, or
        success=False with an error for unsolvable types.
        """
        kind = captcha_type.kind

        if kind == "none":
            return SolveResult(success=True, answer=None)

        if kind in _UNSOLVABLE_TYPES:
            return SolveResult(
                success=False,
                error=f"Captcha type '{kind}' requires user intervention",
            )

        if kind not in _SOLVABLE_TYPES:
            return SolveResult(
                success=False,
                error=f"Unknown captcha type: {kind}",
            )

        extra = ""
        if kind == "text":
            extra = "Type exactly the characters shown in the image."
        elif kind == "arithmetic":
            extra = "Solve the math problem shown and give only the numeric answer."

        prompt = _SOLVE_PROMPT_TEMPLATE.format(kind=kind, extra_instruction=extra)
        answer = self._llm.call_vision(prompt, screenshot).strip()

        if not answer:
            return SolveResult(success=False, error="LLM returned empty answer for captcha")

        return SolveResult(success=True, answer=answer)

    def detect_and_solve(self, screenshot: bytes) -> SolveResult:
        """Convenience: detect captcha type and attempt to solve in one call."""
        captcha_type = self.detect(screenshot)
        if captcha_type.kind == "none":
            return SolveResult(success=True, answer=None)
        return self.solve(screenshot, captcha_type)
