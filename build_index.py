#!/usr/bin/env python3
"""
生成竞品情报中心 index.html
左侧目录树 + 右侧 iframe 加载报告（样式完全隔离）
"""

import json
import re
import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
DAILY_DIR  = BASE_DIR / "reports" / "daily"
WEEKLY_DIR = BASE_DIR / "reports" / "weekly"
OUTPUT     = BASE_DIR / "index.html"


def scan_reports() -> list[dict]:
    reports = []
    for p in sorted(DAILY_DIR.glob("daily_*.html"), reverse=True):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
        date_str = m.group(1) if m else p.stem
        reports.append({
            "id":    p.stem,
            "date":  date_str,
            "type":  "daily",
            "label": f"日报 {date_str}",
            "path":  f"reports/daily/{p.name}",
        })
    for p in sorted(WEEKLY_DIR.glob("weekly_*.html"), reverse=True):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
        date_str = m.group(1) if m else p.stem
        reports.append({
            "id":    p.stem,
            "date":  date_str,
            "type":  "weekly",
            "label": f"周报 {date_str}",
            "path":  f"reports/weekly/{p.name}",
        })
    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports


def build_index():
    reports = scan_reports()
    if not reports:
        print("⚠️  没有找到任何报告文件")
        return

    reports_json = json.dumps(reports, ensure_ascii=False)
    first_path   = reports[0]["path"]
    now_str      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insightto 竞品情报中心</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ height: 100%; overflow: hidden; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #f0f2f8; display: flex; flex-direction: column; }}

  /* ── Top Bar ── */
  .topbar {{
    height: 52px; flex-shrink: 0;
    background: linear-gradient(135deg, #5c4fff 0%, #7c3aed 100%);
    display: flex; align-items: center; padding: 0 20px; gap: 14px;
    box-shadow: 0 2px 8px rgba(92,79,255,.25);
  }}
  .topbar-logo {{
    font-size: 14px; font-weight: 700; color: white;
    display: flex; align-items: center; gap: 8px;
  }}
  .topbar-logo .sub {{ opacity: .65; font-weight: 400; }}
  .topbar-sep {{ width: 1px; height: 18px; background: rgba(255,255,255,.2); }}
  .topbar-sub {{ font-size: 12px; color: rgba(255,255,255,.75); }}
  .topbar-right {{ margin-left: auto; font-size: 11px; color: rgba(255,255,255,.55); }}
  .topbar-pill {{
    background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.2);
    color: white; font-size: 10px; font-weight: 600; letter-spacing: 1px;
    padding: 3px 9px; border-radius: 20px;
  }}

  /* ── Layout ── */
  .layout {{ display: flex; flex: 1; overflow: hidden; }}

  /* ── Sidebar ── */
  .sidebar {{
    width: 240px; flex-shrink: 0;
    background: white; border-right: 1px solid #e8e8f0;
    display: flex; flex-direction: column; overflow: hidden;
  }}
  .sidebar-head {{
    padding: 14px 16px 10px; border-bottom: 1px solid #f0f2f8; flex-shrink: 0;
  }}
  .sidebar-head h2 {{
    font-size: 11px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: .8px; margin-bottom: 10px;
  }}
  .search-box {{
    display: flex; align-items: center; gap: 7px;
    background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 7px;
    padding: 6px 10px;
  }}
  .search-box input {{
    border: none; background: transparent; outline: none;
    font-size: 12px; color: #374151; width: 100%; font-family: inherit;
  }}
  .search-box input::placeholder {{ color: #9ca3af; }}

  .sidebar-scroll {{ flex: 1; overflow-y: auto; padding: 6px 0; }}
  .sidebar-scroll::-webkit-scrollbar {{ width: 3px; }}
  .sidebar-scroll::-webkit-scrollbar-thumb {{ background: #e5e7eb; border-radius: 2px; }}

  .group-label {{
    font-size: 10px; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: .8px;
    padding: 10px 16px 4px;
  }}
  .nav-item {{
    display: flex; align-items: center; gap: 9px;
    padding: 8px 16px; cursor: pointer; transition: background .12s;
    position: relative;
  }}
  .nav-item:hover {{ background: #f9fafb; }}
  .nav-item.active {{ background: #f5f3ff; }}
  .nav-item.active::before {{
    content: ''; position: absolute; left: 0; top: 0; bottom: 0;
    width: 3px; background: #5c4fff; border-radius: 0 2px 2px 0;
  }}
  .nav-icon {{
    width: 26px; height: 26px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; flex-shrink: 0;
  }}
  .icon-d {{ background: #eff6ff; }}
  .icon-w {{ background: #f5f3ff; }}
  .nav-info {{ flex: 1; min-width: 0; }}
  .nav-date {{
    font-size: 12px; font-weight: 600; color: #1e1e2e;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .nav-item.active .nav-date {{ color: #5c4fff; }}
  .nav-type {{ font-size: 10px; color: #9ca3af; margin-top: 1px; }}
  .nav-dot {{
    width: 5px; height: 5px; border-radius: 50%;
    background: #5c4fff; flex-shrink: 0; opacity: 0;
  }}
  .nav-item.active .nav-dot {{ opacity: 1; }}

  .no-results {{ padding: 16px; text-align: center; font-size: 12px; color: #9ca3af; }}

  /* ── Main (iframe) ── */
  .main {{ flex: 1; overflow: hidden; background: #f0f2f8; }}
  #report-frame {{
    width: 100%; height: 100%;
    border: none; display: block;
  }}

  /* ── Empty ── */
  .empty {{
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 100%; color: #9ca3af; text-align: center;
  }}
  .empty .icon {{ font-size: 40px; margin-bottom: 12px; }}
  .empty p {{ font-size: 13px; }}
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
    <span class="topbar-pill">AUTO</span>&nbsp; 最后构建：{now_str}
  </div>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="sidebar-head">
      <h2>报告目录</h2>
      <div class="search-box">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <circle cx="5" cy="5" r="4" stroke="#9ca3af" stroke-width="1.2"/>
          <path d="M8.5 8.5L11 11" stroke="#9ca3af" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
        <input type="text" id="search" placeholder="搜索日期或类型…" oninput="filter(this.value)">
      </div>
    </div>
    <div class="sidebar-scroll" id="nav-list"></div>
  </div>

  <div class="main">
    <iframe id="report-frame" src="{first_path}"></iframe>
  </div>
</div>

<script>
const REPORTS = {reports_json};
let current = REPORTS.length ? REPORTS[0].id : null;

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
  Object.keys(groups).sort().reverse().forEach(m => {{
    html += `<div class="group-label">${{m}}</div>`;
    groups[m].forEach(r => {{
      const isW = r.type === 'weekly';
      html += `<div class="nav-item${{r.id === current ? ' active' : ''}}" id="nav-${{r.id}}" onclick="load('${{r.id}}','${{r.path}}')">
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

function load(id, path) {{
  current = id;
  document.getElementById('report-frame').src = path;
  renderNav(lastList);
  // scroll active into view
  setTimeout(() => {{
    const el = document.getElementById('nav-' + id);
    if (el) el.scrollIntoView({{ block: 'nearest' }});
  }}, 50);
}}

let lastList = REPORTS;
function filter(q) {{
  q = q.toLowerCase().trim();
  lastList = q ? REPORTS.filter(r =>
    r.date.includes(q) ||
    (q === '日报' && r.type === 'daily') ||
    (q === '周报' && r.type === 'weekly')
  ) : REPORTS;
  renderNav(lastList);
  if (lastList.length && !lastList.find(r => r.id === current)) {{
    load(lastList[0].id, lastList[0].path);
  }}
}}

renderNav(REPORTS);
</script>
</body>
</html>"""

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✓ 情报中心已生成: {OUTPUT}")
    print(f"  共收录 {len(reports)} 份报告")
    for r in reports:
        print(f"  - [{r['type']}] {r['date']}")


if __name__ == "__main__":
    build_index()
