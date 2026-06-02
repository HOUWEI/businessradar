"""Data models shared across BusinessRadar modules."""

from typing import Literal

from pydantic import BaseModel


class FetchResult(BaseModel):
    """Result of fetching a page."""

    html: str
    used_browser: bool = False


class PaginationInfo(BaseModel):
    """Pagination mechanism detected by LLM."""

    type: Literal["url_param", "button", "js"]
    selector: str | None = None
    param_name: str | None = None


class FilterParams(BaseModel):
    """Filter parameters detected by LLM."""

    url_constructable: bool
    params: dict[str, str] = {}


class PageAnalysis(BaseModel):
    """LLM analysis of a page's HTML structure."""

    list_item_selector: str
    fields: dict[str, str]
    page_type: Literal["static", "dynamic"]
    pagination: PaginationInfo | None = None
    filter_params: FilterParams | None = None


class GeneratedScript(BaseModel):
    """A generated Python scraping script."""

    code: str


class RunResult(BaseModel):
    """Result of running a generated script."""

    success: bool
    data: list[dict] | None = None
    error: str | None = None


class Evaluation(BaseModel):
    """Two-phase evaluation result: structure + semantic."""

    structure_ok: bool
    semantic_ok: bool
    issues: list[str] = []
    suggestions: list[str] = []
