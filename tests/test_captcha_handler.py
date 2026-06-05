"""Tests for CaptchaHandler — detect and solve captchas via LLM vision."""

import json

from businessradar.captcha_handler import CaptchaHandler
from businessradar.llm_client import StubLLMClient
from businessradar.models import CaptchaType, SolveResult


def _make_handler(text_response: str = "", vision_response: str = "") -> CaptchaHandler:
    return CaptchaHandler(StubLLMClient(response=text_response, vision_response=vision_response))


class TestCaptchaDetection:
    """Detect captcha type from a screenshot via LLM vision."""

    def test_detect_text_captcha(self) -> None:
        vision_resp = json.dumps({"kind": "text", "confidence": 0.9, "description": "distorted letters"})
        handler = _make_handler(vision_response=vision_resp)
        result = handler.detect(b"fake-screenshot-bytes")

        assert result.kind == "text"
        assert result.confidence == 0.9
        assert "distorted" in result.description

    def test_detect_arithmetic_captcha(self) -> None:
        vision_resp = json.dumps({"kind": "arithmetic", "confidence": 0.85, "description": "3+5=?"})
        handler = _make_handler(vision_response=vision_resp)
        result = handler.detect(b"fake-screenshot")

        assert result.kind == "arithmetic"
        assert result.confidence == 0.85

    def test_detect_no_captcha(self) -> None:
        vision_resp = json.dumps({"kind": "none", "confidence": 0.95, "description": "normal page"})
        handler = _make_handler(vision_response=vision_resp)
        result = handler.detect(b"fake-screenshot")

        assert result.kind == "none"

    def test_detect_with_markdown_fences(self) -> None:
        vision_resp = f"```json\n{json.dumps({'kind': 'text', 'confidence': 0.8, 'description': 'captcha'})}\n```"
        handler = _make_handler(vision_response=vision_resp)
        result = handler.detect(b"fake-screenshot")

        assert result.kind == "text"

    def test_detect_invalid_response_returns_none(self) -> None:
        handler = _make_handler(vision_response="not json at all")
        result = handler.detect(b"fake-screenshot")

        assert result.kind == "none"


class TestCaptchaSolve:
    """Solve detected captchas."""

    def test_solve_text_captcha(self) -> None:
        handler = _make_handler(vision_response="Ab7x")
        captcha_type = CaptchaType(kind="text", confidence=0.9, description="text captcha")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is True
        assert result.answer == "Ab7x"

    def test_solve_arithmetic_captcha(self) -> None:
        handler = _make_handler(vision_response="8")
        captcha_type = CaptchaType(kind="arithmetic", confidence=0.85, description="3+5=?")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is True
        assert result.answer == "8"

    def test_solve_unsolvable_recaptcha(self) -> None:
        handler = _make_handler()
        captcha_type = CaptchaType(kind="recaptcha", confidence=0.9, description="Google reCAPTCHA")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is False
        assert "recaptcha" in result.error.lower()

    def test_solve_unsolvable_hcaptcha(self) -> None:
        handler = _make_handler()
        captcha_type = CaptchaType(kind="hcaptcha", confidence= 0.9, description="hCaptcha")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is False
        assert "hcaptcha" in result.error.lower()

    def test_solve_unsolvable_sms(self) -> None:
        handler = _make_handler()
        captcha_type = CaptchaType(kind="sms", confidence=0.9, description="SMS verification")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is False
        assert "sms" in result.error.lower()

    def test_solve_unsolvable_slider(self) -> None:
        handler = _make_handler()
        captcha_type = CaptchaType(kind="slider", confidence=0.9, description="slider captcha")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is False
        assert "slider" in result.error.lower()

    def test_solve_none_type_returns_success(self) -> None:
        handler = _make_handler()
        captcha_type = CaptchaType(kind="none", confidence=0.0, description="no captcha")
        result = handler.solve(b"fake-screenshot", captcha_type)

        assert result.success is True
        assert result.answer is None


class TestDetectAndSolve:
    """Convenience method: detect + solve in one call."""

    def test_no_captcha_returns_success(self) -> None:
        vision_resp = json.dumps({"kind": "none", "confidence": 0.95, "description": "normal page"})
        handler = _make_handler(vision_response=vision_resp)
        result = handler.detect_and_solve(b"fake-screenshot")

        assert result.success is True
        assert result.answer is None

    def test_text_captcha_detected_and_solved(self) -> None:
        # detect_and_solve calls call_vision twice: once for detect, once for solve
        # StubLLMClient returns same vision_response for both calls
        vision_resp = json.dumps({"kind": "text", "confidence": 0.9, "description": "letters"})
        handler = _make_handler(vision_response=vision_resp)
        # The second call (solve) will also get the JSON, which is the "answer"
        result = handler.detect_and_solve(b"fake-screenshot")

        assert result.success is True
