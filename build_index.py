#!/usr/bin/env python3
"""
生成竞品情报中心 index.html
单页应用：左侧目录 + 右侧内容区独立滚动
报告内容直接内嵌，用 shadow DOM 隔离样式
"""

import json
import re
import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
DAILY_DIR  = BASE_DIR / "reports" / "daily"
WEEKLY_DIR = BASE_DIR / "reports" / "weekly"
OUTPUT     = BASE_DIR / "index.html"


def extract_body_content(html: str) -> str:
    """提取 <body> 内的全部内容"""
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else html


def extract_styles(html: str) -> str:
    """提取 <style> 块内容"""
    styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    return "\n".join(styles)


def scan_reports() -> list[dict]:
    reports = []
    for p in sorted(DAILY_DIR.glob("daily_*.html"), reverse=True):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
        date_str = m.group(1) if m else p.stem
        html = p.read_text(encoding="utf-8")
        reports.append({
            "id":     p.stem,
            "date":   date_str,
            "type":   "daily",
            "styles": extract_styles(html),
            "body":   extract_body_content(html),
        })
    for p in sorted(WEEKLY_DIR.glob("weekly_*.html"), reverse=True):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
        date_str = m.group(1) if m else p.stem
        html = p.read_text(encoding="utf-8")
        reports.append({
            "id":     p.stem,
            "date":   date_str,
            "type":   "weekly",
            "styles": extract_styles(html),
            "body":   extract_body_content(html),
        })
    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports


def build_index():
    reports = scan_reports()
    if not reports:
        print("⚠️  没有找到任何报告文件")
        return

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 侧边栏数据（不含 body/styles，减小 JSON 体积）
    nav_data = json.dumps(
        [{"id": r["id"], "date": r["date"], "type": r["type"]} for r in reports],
        ensure_ascii=False
    )

    # 每份报告生成一个 <div class="report-panel"> 用 shadow DOM 挂载
    panels_html = ""
    for i, r in enumerate(reports):
        display = "block" if i == 0 else "none"
        # 转义反引号，避免 JS 模板字符串冲突
        safe_styles = r["styles"].replace("`", "\\`").replace("${", "\\${")
        safe_body   = r["body"].replace("`", "\\`").replace("${", "\\${")
        panels_html += f"""
<div id="panel-{r['id']}" class="report-panel" style="display:{display}"
     data-styles="{{}}" data-id="{r['id']}">
</div>
<script>
(function(){{
  var host = document.getElementById('panel-{r['id']}');
  var shadow = host.attachShadow({{mode:'open'}});
  shadow.innerHTML = `<style>
    :host {{ display:block; }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    {safe_styles}
  </style>
  <div class="report-root">{safe_body}</div>`;
}})();
</script>"""

    html_out = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insightto 竞品情报中心</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ height: 100%; font-family: 'Inter', -apple-system, sans-serif; background: #f0f2f8; }}
  body {{ display: flex; flex-direction: column; overflow: hidden; }}

  /* ── Top Bar ── */
  .topbar {{
    height: 52px; flex-shrink: 0;
    background: linear-gradient(135deg, #5c4fff 0%, #7c3aed 100%);
    display: flex; align-items: center; padding: 0 20px; gap: 14px;
    box-shadow: 0 2px 8px rgba(92,79,255,.25); z-index: 10;
  }}
  .topbar-logo {{ font-size: 14px; font-weight: 700; color: white; display: flex; align-items: center; gap: 8px; }}
  .topbar-logo .sub {{ opacity: .65; font-weight: 400; }}
  .topbar-sep {{ width: 1px; height: 18px; background: rgba(255,255,255,.2); }}
  .topbar-sub {{ font-size: 12px; color: rgba(255,255,255,.75); }}
  .topbar-right {{ margin-left: auto; font-size: 11px; color: rgba(255,255,255,.55); display: flex; align-items: center; gap: 8px; }}
  .topbar-pill {{ background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.2); color: white; font-size: 10px; font-weight: 600; letter-spacing: 1px; padding: 3px 9px; border-radius: 20px; }}

  /* ── Layout ── */
  .layout {{ display: flex; flex: 1; min-height: 0; }}

  /* ── Sidebar ── */
  .sidebar {{
    width: 220px; flex-shrink: 0;
    background: white; border-right: 1px solid #e8e8f0;
    display: flex; flex-direction: column; overflow: hidden;
  }}
  .sidebar-head {{ padding: 14px 14px 10px; border-bottom: 1px solid #f0f2f8; flex-shrink: 0; }}
  .sidebar-head h2 {{ font-size: 10px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 10px; }}
  .search-box {{ display: flex; align-items: center; gap: 7px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 7px; padding: 6px 10px; }}
  .search-box input {{ border: none; background: transparent; outline: none; font-size: 12px; color: #374151; width: 100%; font-family: inherit; }}
  .search-box input::placeholder {{ color: #9ca3af; }}
  .sidebar-scroll {{ flex: 1; overflow-y: auto; padding: 6px 0; }}
  .sidebar-scroll::-webkit-scrollbar {{ width: 3px; }}
  .sidebar-scroll::-webkit-scrollbar-thumb {{ background: #e5e7eb; border-radius: 2px; }}
  .group-label {{ font-size: 10px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: .8px; padding: 10px 14px 4px; }}
  .nav-item {{ display: flex; align-items: center; gap: 8px; padding: 8px 14px; cursor: pointer; transition: background .12s; position: relative; }}
  .nav-item:hover {{ background: #f9fafb; }}
  .nav-item.active {{ background: #f5f3ff; }}
  .nav-item.active::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: #5c4fff; border-radius: 0 2px 2px 0; }}
  .nav-icon {{ width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }}
  .icon-d {{ background: #eff6ff; }}
  .icon-w {{ background: #f5f3ff; }}
  .nav-info {{ flex: 1; min-width: 0; }}
  .nav-date {{ font-size: 12px; font-weight: 600; color: #1e1e2e; }}
  .nav-item.active .nav-date {{ color: #5c4fff; }}
  .nav-type {{ font-size: 10px; color: #9ca3af; margin-top: 1px; }}
  .nav-dot {{ width: 5px; height: 5px; border-radius: 50%; background: #5c4fff; flex-shrink: 0; opacity: 0; }}
  .nav-item.active .nav-dot {{ opacity: 1; }}
  .no-results {{ padding: 16px; text-align: center; font-size: 12px; color: #9ca3af; }}

  /* ── Main ── */
  .main {{ flex: 1; overflow-y: auto; min-height: 0; }}
  .main::-webkit-scrollbar {{ width: 6px; }}
  .main::-webkit-scrollbar-thumb {{ background: #d1d5db; border-radius: 3px; }}

  /* ── Report panels ── */
  .report-panel {{ min-height: 100%; }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-logo">
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <rect width="18" height="18" rx="5" fill="rgba(255,255,255,0.2)"/>
      <circle cx="9" cy="9" r="3.5" fill="white" opacity="0.9"/>
      <circle cx="9" cy="9" r="1.8" fill="#5c4fff"/>
    </svg>
    Insightto <span class="sub">竞品情报中心</span>
  </div>
  <div class="topbar-sep"></div>
  <div class="topbar-sub">Competitor Intelligence Hub</div>
  <div class="topbar-right">
    <span class="topbar-pill">AUTO</span>
    最后构建：{now_str}
  </div>
</div>

<div class="layout">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-head">
      <h2>报告目录</h2>
      <div class="search-box">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <circle cx="5" cy="5" r="4" stroke="#9ca3af" stroke-width="1.2"/>
          <path d="M8.5 8.5L11 11" stroke="#9ca3af" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
        <input type="text" id="search" placeholder="搜索…" oninput="filterNav(this.value)">
      </div>
    </div>
    <div class="sidebar-scroll" id="nav-list"></div>
  </div>

  <!-- Main content -->
  <div class="main" id="main">
    {panels_html}
  </div>
</div>

<script>
const REPORTS = {nav_data};
let currentId = REPORTS.length ? REPORTS[0].id : null;
let filteredList = REPORTS;

function renderNav(list) {{
  const el = document.getElementById('nav-list');
  if (!list.length) {{
    el.innerHTML = '<div class="no-results">没有匹配的报告</div>';
    return;
  }}
  const groups = {{}};
  list.forEach(r => {{
    const m = r.date.slice(0, 7);
    (groups[m] = groups[m] || []).push(r);
  }});
  let html = '';
  Object.keys(groups).sort().reverse().forEach(month => {{
    html += `<div class="group-label">${{month}}</div>`;
    groups[month].forEach(r => {{
      const isW = r.type === 'weekly';
      html += `<div class="nav-item${{r.id === currentId ? ' active' : ''}}" onclick="showReport('${{r.id}}')">
        <div class="nav-icon ${{isW ? 'icon-w' : 'icon-d'}}">${{isW ? '📊' : '📋'}}</div>
        <div class="nav-info">
          <div class="nav-date">${{r.date}}</div>
          <div class="nav-type">${{isW ? '周报' : '日报'}}</div>
        </div>
        <div class="nav-dot"></div>
      </div>`;
    }});
  }});
  el.innerHTML = html;
}}

function showReport(id) {{
  // 隐藏当前
  if (currentId) {{
    const prev = document.getElementById('panel-' + currentId);
    if (prev) prev.style.display = 'none';
  }}
  currentId = id;
  // 显示新的
  const panel = document.getElementById('panel-' + id);
  if (panel) panel.style.display = 'block';
  // 滚回顶部
  document.getElementById('main').scrollTop = 0;
  // 更新导航高亮
  renderNav(filteredList);
}}

function filterNav(q) {{
  q = q.toLowerCase().trim();
  filteredList = q ? REPORTS.filter(r =>
    r.date.includes(q) ||
    (q === '日报' && r.type === 'daily') ||
    (q === '周报' && r.type === 'weekly')
  ) : REPORTS;
  renderNav(filteredList);
  if (filteredList.length && !filteredList.find(r => r.id === currentId)) {{
    showReport(filteredList[0].id);
  }}
}}

// 初始化
renderNav(REPORTS);
</script>
</body>
</html>"""

    OUTPUT.write_text(html_out, encoding="utf-8")
    print(f"✓ 情报中心已生成: {OUTPUT}")
    print(f"  共收录 {len(reports)} 份报告")
    for r in reports:
        print(f"  - [{r['type']}] {r['date']}")


if __name__ == "__main__":
    build_index()
