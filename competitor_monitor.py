#!/usr/bin/env python3
"""
Insightto Competitor Monitor v3
数据抓取策略：
  1. 直接 HTTP 抓取 changelog（有效时使用）
  2. DuckDuckGo HTML 搜索（兜底）
  3. 生成结构化 JSON 供 AI 分析
"""

import json
import re
import sys
import time
import hashlib
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
REPORTS_DIR = BASE_DIR / "reports"

# ─── 竞品配置 ─────────────────────────────────────────────────────────────────
COMPETITORS = [
    {
        "name": "Typeform",
        "category": "Survey / Form Builder",
        "focus": ["NPS", "survey logic", "AI features", "integrations"],
        "search_queries": [
            "Typeform new feature update site:typeform.com 2026",
            "Typeform product update changelog 2026",
            "Typeform AI survey feature release",
        ],
        "changelog_urls": [
            "https://www.typeform.com/changelog/",
            "https://community.typeform.com/product-updates-6",
        ],
    },
    {
        "name": "Delighted",
        "category": "NPS / CSAT / CES",
        "focus": ["NPS", "CSAT", "CES", "exit survey", "reporting"],
        "search_queries": [
            "Delighted NPS new feature 2026",
            "Delighted app update changelog 2026",
        ],
        "changelog_urls": [
            "https://delighted.com/changelog",
            "https://help.delighted.com/hc/en-us/categories/360001556072",
        ],
    },
    {
        "name": "AskNicely",
        "category": "NPS / Customer Feedback",
        "focus": ["NPS", "frontline feedback", "coaching", "integrations"],
        "search_queries": [
            "AskNicely new feature product update 2026",
            "AskNicely NPS changelog release",
        ],
        "changelog_urls": [],
    },
    {
        "name": "Survicate",
        "category": "Survey / NPS / In-product",
        "focus": ["in-product survey", "NPS", "exit intent", "Shopify"],
        "search_queries": [
            "Survicate new feature update 2026",
            "Survicate survey tool changelog release notes",
        ],
        "changelog_urls": [
            "https://survicate.com/changelog/",
        ],
    },
    {
        "name": "Hotjar",
        "category": "Heatmap / Survey / Feedback",
        "focus": ["survey", "feedback widget", "heatmap", "session recording"],
        "search_queries": [
            "Hotjar new feature update 2026",
            "Hotjar survey feedback changelog release",
        ],
        "changelog_urls": [
            "https://www.hotjar.com/changelog/",
        ],
    },
    {
        "name": "SurveyMonkey",
        "category": "Survey Platform",
        "focus": ["NPS", "AI analysis", "enterprise", "integrations"],
        "search_queries": [
            "SurveyMonkey new feature release 2026",
            "SurveyMonkey AI survey update changelog",
        ],
        "changelog_urls": [],
    },
    {
        "name": "Qualtrics",
        "category": "Enterprise XM / NPS",
        "focus": ["NPS", "AI insights", "enterprise", "CX"],
        "search_queries": [
            "Qualtrics new feature release 2026",
            "Qualtrics XM AI update product news",
        ],
        "changelog_urls": [],
    },
    {
        "name": "Medallia",
        "category": "Enterprise CX / NPS",
        "focus": ["NPS", "AI", "enterprise CX", "real-time feedback"],
        "search_queries": [
            "Medallia new feature product update 2026",
            "Medallia AI CX release news",
        ],
        "changelog_urls": [],
    },
]


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 12) -> str | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [WARN] {url[:60]} → {type(e).__name__}: {e}")
        return None


def clean_html(html: str, max_chars: int = 5000) -> str:
    html = re.sub(
        r"<(script|style|nav|footer|header|aside)[^>]*>.*?</(script|style|nav|footer|header|aside)>",
        " ", html, flags=re.DOTALL | re.IGNORECASE
    )
    html = re.sub(r"<(br|p|li|h[1-6]|div|section|article|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 15]
    return "\n".join(lines)[:max_chars]


def search_duckduckgo(query: str) -> str:
    """DuckDuckGo HTML 搜索，返回标题+摘要列表"""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}&kl=us-en"
    html = fetch_url(url, timeout=20)
    if not html:
        return ""

    results = []
    # 提取结果块
    blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    if not blocks:
        # 备用提取方式
        titles   = re.findall(r'class="result__a"[^>]*>(.*?)</(?:a|span)>', html, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>', html, re.DOTALL)
        blocks = list(zip(titles, snippets))

    for t, s in blocks[:8]:
        t_clean = re.sub(r"<[^>]+>", "", t).strip()
        s_clean = re.sub(r"<[^>]+>", "", s).strip()
        if t_clean and len(t_clean) > 5:
            results.append(f"• {t_clean}\n  {s_clean}")

    return "\n".join(results)


def get_cache_path(key: str) -> Path:
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.json"


def load_cache(key: str, ttl: int = 21600) -> str | None:
    p = get_cache_path(key)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if time.time() - data.get("ts", 0) < ttl:
                return data.get("content", "")
        except Exception:
            pass
    return None


def save_cache(key: str, content: str):
    p = get_cache_path(key)
    p.write_text(json.dumps({"ts": time.time(), "content": content}, ensure_ascii=False))


# ─── 核心抓取 ─────────────────────────────────────────────────────────────────

def collect_competitor_data() -> list[dict]:
    results = []
    for comp in COMPETITORS:
        print(f"\n📡 {comp['name']}")
        content = ""
        source_used = ""

        # 1. 尝试 changelog 直连
        for url in comp.get("changelog_urls", []):
            cached = load_cache(url)
            if cached:
                content = cached
                source_used = f"changelog (cached): {url}"
                print(f"  ✓ cache: {url[:50]}")
                break
            html = fetch_url(url)
            if html and len(html) > 500:
                text = clean_html(html, 5000)
                if len(text) > 200:
                    save_cache(url, text)
                    content = text
                    source_used = f"changelog: {url}"
                    print(f"  ✓ changelog: {len(text)} chars")
                    break
            time.sleep(1)

        # 2. 搜索兜底
        if not content:
            for query in comp.get("search_queries", []):
                cached = load_cache(query)
                if cached:
                    content = cached
                    source_used = f"search (cached): {query}"
                    print(f"  ✓ cache search")
                    break
                result = search_duckduckgo(query)
                if result and len(result) > 100:
                    save_cache(query, result)
                    content = result
                    source_used = f"search: {query}"
                    print(f"  ✓ search: {len(result)} chars")
                    break
                time.sleep(2)

        if not content:
            print(f"  ✗ no data found")

        results.append({
            "name": comp["name"],
            "category": comp["category"],
            "focus": comp["focus"],
            "content": content,
            "source": source_used,
            "fetched_at": datetime.datetime.now().isoformat(),
        })

    return results


# ─── AI 分析 ──────────────────────────────────────────────────────────────────

def analyze_with_claude(raw_data: list[dict], report_type: str = "daily") -> str:
    today = datetime.date.today().strftime("%Y-%m-%d")

    sections = []
    for comp in raw_data:
        if not comp["content"]:
            continue
        sections.append(
            f"## {comp['name']} ({comp['category']})\n"
            f"关注领域: {', '.join(comp['focus'])}\n"
            f"数据来源: {comp['source']}\n\n"
            f"{comp['content'][:3000]}"
        )

    all_text = "\n\n---\n\n".join(sections)

    if report_type == "weekly":
        task_desc = (
            "生成一份竞品周报（过去7天），包含：\n"
            "1. 各竞品本周重要功能/页面更新汇总\n"
            "2. 行业趋势洞察（AI、NPS、Shopify 生态等）\n"
            "3. 对 Insightto 产品路线图的战略建议（具体可执行）"
        )
    else:
        task_desc = (
            "生成一份竞品日报，包含：\n"
            "1. 各竞品近期功能更新、页面改版、新上线功能（重点！）\n"
            "2. 值得关注的产品动作或营销策略\n"
            "3. 对 Insightto 产品迭代的 1-3 条具体参考建议"
        )

    prompt = f"""你是 Insightto 的产品竞品分析师。

Insightto 是一款面向 Shopify 商家的 NPS/Survey/Feedback SaaS 工具，核心功能：
- NPS 问卷（0-10 评分 + 追问跳转）
- Exit Survey（离开意图弹窗）
- CRM 客户反馈管理
- AI 分析洞察（情感分析、关键词提取）
- 问卷模版库
- Shopify App Store 上架

今天是 {today}，请根据以下竞品的功能更新/产品动态数据，{task_desc}。

输出要求：
- 中文输出
- 每个竞品单独一节，标注数据来源类型
- 重点标注「⚡ 与 Insightto 直接相关」的功能点
- 如果某竞品没有近期更新数据，直接跳过
- 最后单独一节「📌 对 Insightto 的行动建议」

竞品数据：

{all_text[:14000]}
"""

    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except ImportError:
        return fallback_summary(raw_data, report_type, today)
    except Exception as e:
        print(f"  [WARN] Claude API: {e}")
        return fallback_summary(raw_data, report_type, today)


def fallback_summary(raw_data: list[dict], report_type: str, today: str) -> str:
    lines = [f"# Insightto 竞品{'周' if report_type == 'weekly' else '日'}报 — {today}\n"]
    lines.append("> ⚠️ Claude API 不可用，以下为原始数据摘要\n")
    for comp in raw_data:
        if not comp["content"]:
            continue
        lines.append(f"\n## {comp['name']} ({comp['category']})")
        lines.append(f"**来源**: {comp['source']}")
        lines.append(f"\n{comp['content'][:600]}...")
    lines.append("\n---\n## 📌 建议\n1. 关注 Delighted/Survicate 的 Shopify 集成\n2. 跟进 Typeform AI 功能\n3. 差异化 Exit Survey 体验")
    return "\n".join(lines)


# ─── HTML 报告生成 ────────────────────────────────────────────────────────────

def generate_html_report(analysis: str, report_type: str, date_str: str) -> str:
    title = f"Insightto 竞品{'周报' if report_type == 'weekly' else '日报'} — {date_str}"
    badge_color = "#7c3aed" if report_type == "weekly" else "#2563eb"
    badge_text = "WEEKLY" if report_type == "weekly" else "DAILY"

    html = analysis
    html = re.sub(r"^# (.+)$",   r"<h1>\1</h1>",   html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$",  r"<h2>\1</h2>",   html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>",   html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"⚡ (.+?)(?=\n|$)", r'<span class="highlight">⚡ \1</span>', html, flags=re.MULTILINE)
    html = re.sub(r"^(\d+)\. (.+)$", r"<li>\2</li>", html, flags=re.MULTILINE)
    html = re.sub(r"^[-•] (.+)$",    r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)
    html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)
    html = html.replace("\n\n", "</p><p>").replace("\n", "<br>")
    html = f"<p>{html}</p>"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Inter',-apple-system,sans-serif;background:#f0f2f8;color:#1e1e2e;padding:32px 16px;line-height:1.75}}
  .container{{max-width:880px;margin:0 auto}}
  .header{{background:linear-gradient(135deg,#5c4fff 0%,#7c3aed 100%);border-radius:16px;padding:32px 36px;color:white;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between}}
  .header h1{{font-size:22px;font-weight:700;margin-bottom:6px}}
  .header .meta{{font-size:13px;opacity:.8}}
  .badge{{background:{badge_color};border:2px solid rgba(255,255,255,.3);color:white;font-size:11px;font-weight:700;letter-spacing:1.5px;padding:6px 14px;border-radius:20px;white-space:nowrap}}
  .card{{background:white;border-radius:12px;padding:28px 32px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
  h1{{font-size:20px;font-weight:700;color:#1e1e2e;margin-bottom:12px}}
  h2{{font-size:16px;font-weight:600;color:#5c4fff;margin:24px 0 10px;padding-bottom:8px;border-bottom:2px solid #ede9fe}}
  h3{{font-size:14px;font-weight:600;color:#374151;margin:14px 0 6px}}
  p{{margin-bottom:10px;font-size:14px;color:#374151}}
  li{{font-size:14px;color:#374151;margin-left:20px;margin-bottom:5px}}
  strong{{color:#1e1e2e}}
  .highlight{{background:#fef3c7;border-radius:4px;padding:1px 6px;font-size:13px;color:#92400e;font-weight:500}}
  blockquote{{background:#fef3c7;border-left:3px solid #f59e0b;padding:10px 16px;border-radius:0 8px 8px 0;font-size:13px;color:#92400e;margin:12px 0}}
  hr{{border:none;border-top:1px solid #e8e8f0;margin:20px 0}}
  .footer{{text-align:center;font-size:12px;color:#9ca3af;margin-top:24px}}
  .generated-by{{display:inline-flex;align-items:center;gap:6px;background:white;border-radius:20px;padding:6px 14px;font-size:12px;color:#6b7280;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="meta">Insightto · 竞品情报系统</div>
      <h1>{title}</h1>
      <div class="meta">生成时间：{now_str}</div>
    </div>
    <div class="badge">{badge_text}</div>
  </div>
  <div class="card">
    {html}
  </div>
  <div class="footer">
    <span class="generated-by">⚡ 由 Insightto 竞品监控系统自动生成</span>
  </div>
</div>
</body>
</html>"""


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def run(report_type: str = "daily"):
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")

    print(f"\n{'='*52}")
    print(f"🔍 Insightto 竞品监控 v3 — {report_type.upper()} — {date_str}")
    print(f"{'='*52}")

    print("\n[1/3] 抓取竞品功能更新数据...")
    raw_data = collect_competitor_data()

    raw_path = CACHE_DIR / f"raw_{date_str}.json"
    raw_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2))
    print(f"\n✓ 原始数据: {raw_path}")

    print("\n[2/3] AI 分析...")
    analysis = analyze_with_claude(raw_data, report_type)

    print("\n[3/3] 生成 HTML 报告...")
    html = generate_html_report(analysis, report_type, date_str)

    sub = "weekly" if report_type == "weekly" else "daily"
    report_path = REPORTS_DIR / sub / f"{sub}_{date_str}.html"
    report_path.write_text(html, encoding="utf-8")

    latest_path = BASE_DIR / f"latest_{report_type}_report.html"
    latest_path.write_text(html, encoding="utf-8")

    print(f"✓ 报告: {report_path}")
    print(f"✓ 最新: {latest_path}")
    return str(report_path)


if __name__ == "__main__":
    rtype = sys.argv[1] if len(sys.argv) > 1 else "daily"
    run(rtype)
