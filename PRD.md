# BusinessRadar — 招投标信息智能提取工具

## Problem Statement

招投标和采购公告散落在各级政府采购网、招投标平台上。数据分析师、商务人员需要从这些网站上批量提取结构化的公告信息（标题、日期、预算金额、采购人等），但每个网站的页面结构不同、翻页机制不同、反爬策略不同。手动编写抓取脚本耗时且容易出错，非技术人员更是无从下手。

用户需要一个工具：给它一个列表页 URL 和一句自然语言描述（如"昨天的信息化采购公告"），工具自动分析页面结构、生成稳定的 Python 抓取脚本、通过试错循环验证效果，最终交付一个可以直接运行的脚本。

## Solution

BusinessRadar 是一个 CLI 工具，接收 URL + 自然语言查询，通过 LLM 驱动的试错循环自动生成可靠的 Python 数据抓取脚本。

**核心流程：**

1. 用户提供 URL 和自然语言描述
2. 工具获取页面内容，分析 HTML 结构
3. LLM 识别数据位置、翻页机制、筛选参数
4. 生成基于 Playwright + BeautifulSoup4 的 Python 脚本
5. 试运行脚本，验证结果（结构 + 语义）
6. 失败则修改脚本重试（自适应试错循环）
7. 成功后交付脚本，用户可独立运行

**混合模式：** 工具不仅生成脚本，还提供试运行调试环境。自动试错到一定阶段后可切换为人工介入。

## User Stories

### 基础使用

1. As a data analyst, I want to provide a URL and a natural language query, so that I can get a working Python scraping script without writing code manually.
2. As a data analyst, I want the tool to automatically detect the page structure and data fields, so that I don't need to inspect HTML manually.
3. As a data analyst, I want the generated script to handle pagination automatically, so that I can extract all matching records across multiple pages.
4. As a data analyst, I want the output to be JSON format, so that I can easily process the data downstream.
5. As a data analyst, I want core fields (title, date, link) to always be extracted, so that every record has essential identification information.
6. As a data analyst, I want to describe additional fields I need in natural language (e.g., "预算金额", "采购人"), so that the script adapts to different websites.

### 筛选与过滤

7. As a data analyst, I want to filter results by date (e.g., "昨天的"), so that I only get recent announcements.
8. As a data analyst, I want to filter by category (e.g., "信息化"), so that I only get relevant procurement types.
9. As a data analyst, I want the tool to try URL-level filtering first, so that fewer requests are needed when the site supports it.
10. As a data analyst, I want local filtering as a fallback, so that even sites without URL-based filtering can be handled.

### 试错与验证

11. As a data analyst, I want the tool to automatically retry when the generated script fails, so that minor issues are resolved without my intervention.
12. As a data analyst, I want the tool to show me the trial progress in real-time, so that I can understand what's happening.
13. As a data analyst, I want the tool to escalate to me when it's stuck, so that I can provide guidance instead of it looping forever.
14. As a data analyst, I want the tool to stop early if it's not making progress (same errors repeated), so that my time and API costs aren't wasted.
15. As a data analyst, I want a hard retry limit (10 rounds), so that the process always terminates.

### 反爬与验证码

16. As a data analyst, I want the tool to handle basic anti-scraping measures (random UA, request delays) automatically, so that the script works on most sites out of the box.
17. As a data analyst, I want the tool to automatically switch to browser mode when static requests fail, so that dynamic pages are handled.
18. As a data analyst, I want the tool to attempt CAPTCHA solving via LLM vision, so that simple captchas don't block the entire process.
19. As a data analyst, I want the tool to prompt me when it encounters a CAPTCHA it can't solve, so that I can decide whether to intervene or skip the site.

### 页面分析

20. As a data analyst, I want the tool to analyze HTML structure first, so that the process is fast and cost-effective for simple pages.
21. As a data analyst, I want the tool to upgrade to screenshot-based analysis when HTML analysis fails, so that complex layouts can still be understood.
22. As a data analyst, I want the tool to detect and handle pagination automatically, so that I get all matching data, not just the first page.

### 输出与脚本

23. As a data analyst, I want the generated script to be self-contained and runnable independently, so that I can integrate it into my own workflows.
24. As a data analyst, I want the generated script to use Playwright + BeautifulSoup4, so that it handles both static and dynamic pages reliably.
25. As a data analyst, I want the generated script to stop scraping when it reaches records outside my query scope (e.g., older dates), so that I don't get irrelevant data.
26. As a data analyst, I want a page count limit as a safety net in the generated script, so that it doesn't scrape infinitely if the termination condition isn't met.

### 配置与模型

27. As a developer, I want to configure my preferred LLM provider and model, so that I can use the API I'm most comfortable with.
28. As a developer, I want to set API keys via config file or environment variables, so that sensitive credentials aren't in my command history.
29. As a developer, I want to override settings via CLI arguments, so that I can make one-off changes without editing config files.
30. As a developer, I want the tool to support multiple LLM backends (OpenAI, Anthropic, local models), so that I'm not locked into one provider.

## Implementation Decisions

### Module Architecture

The system is decomposed into 8 modules with clear interfaces:

- **PageFetcher**: Encapsulates all network requests. Handles static→browser escalation, random UA, request delays. Interface: `fetch(url, strategy) → FetchResult`.
- **PageAnalyzer**: Calls LLM to analyze HTML structure, identifying list item selectors, pagination mechanism, filter parameters, and extra fields. Interface: `analyze(html, user_query) → PageAnalysis`.
- **ScriptGenerator**: Generates runnable Python scripts based on PageAnalysis. All scripts use Playwright + BeautifulSoup4. Interface: `generate(page_analysis, user_query, url) → GeneratedScript`.
- **ScriptRunner**: Executes generated scripts in subprocess, captures JSON output and error logs. Interface: `run(script_code, timeout) → RunResult`.
- **ResultEvaluator**: Two-phase evaluation — structural validation (fields present, non-empty) then semantic validation (LLM checks if data matches user query). Interface: `evaluate(data, user_query, page_analysis) → Evaluation`.
- **TrialLoop**: Orchestrates the full trial cycle. Manages retry limit (10 rounds), stagnation detection (3 consecutive rounds with no improvement), and auto→human handoff. Interface: `execute(url, user_query, config) → TrialResult`.
- **CaptchaHandler**: Detects CAPTCHA type via LLM vision, attempts to solve via Playwright driver. Falls back to user prompt on failure. Interface: `detect(screenshot) → CaptchaType`, `solve(screenshot, type, page_handle) → SolveResult`.
- **ConfigManager**: Three-tier config priority (CLI args > config file > env vars). Validates required fields (API key). Interface: `get(key) → str`, `load() → Config`.

### Anti-Scraping Strategy

Generated scripts implement a layered defense:
1. Random User-Agent + random delay (1-3s) — always on
2. Upgrade to Playwright browser mode — automatic on failure
3. Proxy support — if user has configured proxy settings
4. CAPTCHA handling — LLM vision + Playwright, fallback to user

### Success Criteria

Two-phase validation:
- **Structure**: Script runs without errors, returns non-empty data, core fields (title, date, link) are present and non-null.
- **Semantic**: LLM compares extracted data against the user's original natural language query to verify relevance (e.g., dates match "yesterday", categories match "IT-related").

### Trial Loop Control

- Hard retry limit: 10 rounds
- Early stop: if 3 consecutive rounds show no improvement (same errors, same issues), halt and escalate to user
- Phase transition: auto-retry phase → human-in-the-loop phase (when stuck or user interrupts)

### Pagination Strategy

LLM analyzes pagination mechanism from HTML: URL parameters, next-button links, or JavaScript-based navigation. Generated script implements the detected strategy. Termination is dual: semantic (user's query implies a boundary like date range) + hard page limit.

### Technology Stack for Generated Scripts

All generated scripts uniformly use Playwright + BeautifulSoup4, regardless of whether the page is static or dynamic. This ensures consistency and avoids conditional logic in generated code.

## Testing Decisions

### What Makes a Good Test

Tests should verify **external behavior** of modules through their public interfaces, not internal implementation details. Each module's test suite should:

- Mock dependencies (LLM calls, network requests, subprocess execution)
- Test the contract (given input X, module returns Y)
- Cover edge cases (empty pages, network errors, malformed HTML, CAPTCHA pages)
- Be runnable without API keys (all LLM calls mocked)

### Modules to Test (Priority Order)

1. **ResultEvaluator** — Pure logic, easiest to test. Verify structure validation rules and mock LLM for semantic evaluation.
2. **PageAnalyzer** — Mock LLM responses, test that HTML is properly cleaned and prompts are correctly constructed. Verify PageAnalysis output structure.
3. **TrialLoop** — Mock all sub-modules, test orchestration: retry counting, stagnation detection, phase transitions.
4. **ScriptRunner** — Test with real subprocess execution of small scripts. Verify timeout behavior and output parsing.
5. **CaptchaHandler** — Mock LLM vision responses for different CAPTCHA types. Test detection accuracy.
6. **ConfigManager** — Test priority resolution across CLI args, config file, and env vars.
7. **PageFetcher** — Integration-level tests with mock HTTP responses and Playwright sessions.
8. **ScriptGenerator** — Hardest to test in isolation; validate that generated code is syntactically valid Python and contains expected patterns.

### Test Infrastructure

- Use `pytest` as the test framework
- Use `unittest.mock` for mocking LLM calls and subprocess execution
- Use `responses` or `aioresponses` for HTTP mocking
- Provide fixture HTML files from real procurement websites (sanitized)

## Out of Scope

- **Detail page extraction**: Only list pages are supported. Extracting data from individual announcement detail pages is not in scope.
- **Multi-step navigation**: The tool does not navigate from a homepage to a list page. Users must provide a direct URL to a list page.
- **Scheduled/monitoring runs**: Generated scripts are one-shot scrapers, not cron-scheduled monitors. No built-in scheduling, deduplication, or incremental sync.
- **Authentication / Login**: Sites requiring login are not supported. Users must provide URLs to publicly accessible pages.
- **Data storage / database**: No built-in database integration. Output is JSON files only.
- **Web UI**: No web interface. CLI only.
- **Distributed scraping / proxy rotation services**: No integration with proxy pools or scraping services.
- **reCAPTCHA / hCaptcha solving**: These advanced CAPTCHA types are out of scope. The tool will detect them and prompt the user.
- **SMS / email verification codes**: These require external input and cannot be automated.

## Further Notes

### Project Name

**BusinessRadar** — reflects the tool's purpose of scanning and extracting business procurement information.

### User Query Language

The tool should accept natural language queries in Chinese, as the primary target websites are Chinese government procurement and bidding platforms. LLM prompts should be optimized for Chinese language understanding.

### Typical Target Websites

- 中国政府采购网 (www.ccgp.gov.cn)
- 各省级政府采购网
- 全国公共资源交易平台
- 各行业招投标平台

### Cost Considerations

Each trial loop iteration involves:
- 1 LLM call for page analysis (input: full HTML)
- 1 LLM call for script generation
- 1 LLM call for result evaluation
- Possible LLM call for CAPTCHA detection

With a 10-round retry limit, worst case is ~30-40 LLM calls per URL. Users should be aware of API costs for complex sites.

### Future Expansion Possibilities

- Detail page extraction (follow links from list items)
- Multi-site monitoring with scheduled runs
- Database output (PostgreSQL, SQLite)
- Export to Excel format
- Web UI for non-technical users
