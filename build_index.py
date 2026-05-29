#!/usr/bin/env python3
"""
生成竞品情报中心 index.html
读取 reports/daily/ 和 reports/weekly/ 下所有报告，
构建一个带左侧目录、右侧内容的单页应用
"""

import json
import re
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DAILY_DIR  = BASE_DIR / "reports" / "daily"
WEEKLY_DIR = BASE_DIR / "reports" / "weekly"
OUTPUT     = BASE_DIR / "index.html"


def load_report(path: Path) -> dict:
    """读取单个报告 HTML，提取标题和正文内容"""
    html = path.read_text(encoding="utf-8")

    # 提取 <title>
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    title = m.group(1).strip() if m else path.stem

    # 提取 .card 内容（报告主体）
    # 取 body 内全部内容，去掉 header 和 footer，保留 card 部分
    body_m = re.search(r"<body>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    body = body_m.group(1) if body_m else html

    # 去掉 header div（渐变顶栏）和 footer
    body = re.sub(r'<div class="header">.*?</div>\s*', "", body, flags=re.DOTALL)
    body = re.sub(r'<div class="footer">.*?</div>\s*', "", body, flags=re.DOTALL)
    body = re.sub(r'<div class="container">\s*', "", body)
    body = re.sub(r'</div>\s*$', "", body.strip())

    # 提取日期
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", path.stem)
    date_str = date_m.group(1) if date_m else ""

    return {
        "id": path.stem,
        "title": title,
        "date": date_str,
        "type": "weekly" if "weekly" in path.stem else "daily",
        "content": body.strip(),
    }


def build_index():
    reports = []

    # 加载日报
    for p in sorted(DAILY_DIR.glob("daily_*.html"), reverse=True):
        reports.append(load_report(p))

    # 加载周报
    for p in sorted(WEEKLY_DIR.glob("weekly_*.html"), reverse=True):
        reports.append(load_report(p))

    # 按日期排序（最新在前）
    reports.sort(key=lambda r: r["date"], reverse=True)

    if not reports:
        print("⚠️  没有找到任何报告文件")
        return

    # 构建侧边栏条目 JSON（供 JS 使用）
    sidebar_data = json.dumps(
        [{"id": r["id"], "title": r["title"], "date": r["date"], "type": r["type"]} for r in reports],
        ensure_ascii=False
    )

    # 构建内容区 HTML 片段
    content_sections = ""
    for r in reports:
        display = "block" if r == reports[0] else "none"
        content_sections += f"""
<div id="section-{r['id']}" class="report-section" style="display:{display}">
  <div class="report-header">
    <div class="report-meta">Insightto · 竞品情报系统</div>
    <h1 class="report-title">{r['title']}</h1>
    <div class="report-meta">{r['date']} · {'周报' if r['type'] == 'weekly' else '日报'}</div>
  </div>
  {r['content']}
</div>
"""

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insightto 竞品情报中心</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* ── Reset ── */
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#f0f2f8;color:#1e1e2e;display:flex;flex-direction:column}}

/* ── Top Bar ── */
.topbar{{
  height:56px;flex-shrink:0;
  background:linear-gradient(135deg,#5c4fff 0%,#7c3aed 100%);
  display:flex;align-items:center;padding:0 24px;gap:16px;
  box-shadow:0 2px 8px rgba(92,79,255,.3);
  z-index:100;
}}
.topbar-logo{{
  font-size:15px;font-weight:700;color:white;letter-spacing:-.3px;
  display:flex;align-items:center;gap:8px;
}}
.topbar-logo span{{opacity:.7;font-weight:400}}
.topbar-divider{{width:1px;height:20px;background:rgba(255,255,255,.25)}}
.topbar-title{{font-size:13px;color:rgba(255,255,255,.85);font-weight:500}}
.topbar-right{{margin-left:auto;font-size:12px;color:rgba(255,255,255,.6)}}
.topbar-badge{{
  background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);
  color:white;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;
}}

/* ── Layout ── */
.layout{{display:flex;flex:1;overflow:hidden}}

/* ── Sidebar ── */
.sidebar{{
  width:260px;flex-shrink:0;
  background:white;
  border-right:1px solid #e8e8f0;
  display:flex;flex-direction:column;
  overflow:hidden;
}}
.sidebar-header{{
  padding:16px 20px 12px;
  border-bottom:1px solid #f0f2f8;
  flex-shrink:0;
}}
.sidebar-header h2{{font-size:12px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.8px}}
.sidebar-search{{
  margin-top:10px;
  display:flex;align-items:center;gap:8px;
  background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;
  padding:7px 12px;
}}
.sidebar-search input{{
  border:none;background:transparent;outline:none;
  font-size:13px;color:#374151;width:100%;
  font-family:inherit;
}}
.sidebar-search input::placeholder{{color:#9ca3af}}

.sidebar-scroll{{flex:1;overflow-y:auto;padding:8px 0}}
.sidebar-scroll::-webkit-scrollbar{{width:4px}}
.sidebar-scroll::-webkit-scrollbar-track{{background:transparent}}
.sidebar-scroll::-webkit-scrollbar-thumb{{background:#e5e7eb;border-radius:2px}}

.sidebar-group{{margin-bottom:4px}}
.sidebar-group-label{{
  font-size:11px;font-weight:600;color:#9ca3af;
  text-transform:uppercase;letter-spacing:.8px;
  padding:10px 20px 4px;
}}
.sidebar-item{{
  display:flex;align-items:center;gap:10px;
  padding:9px 20px;cursor:pointer;
  border-radius:0;transition:background .15s;
  position:relative;
}}
.sidebar-item:hover{{background:#f9fafb}}
.sidebar-item.active{{background:#f5f3ff}}
.sidebar-item.active::before{{
  content:'';position:absolute;left:0;top:0;bottom:0;
  width:3px;background:#5c4fff;border-radius:0 2px 2px 0;
}}
.sidebar-item-icon{{
  width:28px;height:28px;border-radius:6px;
  display:flex;align-items:center;justify-content:center;
  font-size:13px;flex-shrink:0;
}}
.icon-daily{{background:#eff6ff;color:#2563eb}}
.icon-weekly{{background:#f5f3ff;color:#7c3aed}}
.sidebar-item-info{{flex:1;min-width:0}}
.sidebar-item-date{{font-size:13px;font-weight:600;color:#1e1e2e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.sidebar-item.active .sidebar-item-date{{color:#5c4fff}}
.sidebar-item-type{{font-size:11px;color:#9ca3af;margin-top:1px}}
.sidebar-item-dot{{
  width:6px;height:6px;border-radius:50%;background:#5c4fff;
  flex-shrink:0;opacity:0;
}}
.sidebar-item.active .sidebar-item-dot{{opacity:1}}

/* ── Main Content ── */
.main{{flex:1;overflow-y:auto;padding:28px 32px}}
.main::-webkit-scrollbar{{width:6px}}
.main::-webkit-scrollbar-track{{background:transparent}}
.main::-webkit-scrollbar-thumb{{background:#d1d5db;border-radius:3px}}

/* ── Report Sections ── */
.report-section{{max-width:820px;margin:0 auto}}
.report-header{{
  background:linear-gradient(135deg,#5c4fff 0%,#7c3aed 100%);
  border-radius:16px;padding:28px 32px;color:white;margin-bottom:20px;
}}
.report-title{{font-size:20px;font-weight:700;margin:6px 0}}
.report-meta{{font-size:12px;opacity:.75}}

/* ── Cards (inherited from report HTML) ── */
.card{{background:white;border-radius:12px;padding:24px 28px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.comp-section{{margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid #f0f2f8}}
.comp-section:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.comp-header{{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}}
.comp-name{{font-size:15px;font-weight:700;color:#1e1e2e}}
.comp-cat{{font-size:12px;color:#6b7280;background:#f3f4f6;padding:3px 10px;border-radius:20px}}
.source-tag{{font-size:11px;color:#9ca3af;margin-left:auto}}
.update-item{{margin-bottom:7px;font-size:14px;color:#374151;padding-left:16px;position:relative}}
.update-item::before{{content:"•";position:absolute;left:0;color:#5c4fff}}
.highlight{{background:#fef3c7;border-radius:4px;padding:2px 6px;font-size:13px;color:#92400e;font-weight:600;display:inline-block;margin-top:4px}}
.shutdown-badge{{background:#fee2e2;color:#991b1b;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px}}
.action-section{{background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%);border-radius:12px;padding:22px 26px;margin-top:8px}}
.action-section h2{{font-size:15px;font-weight:700;color:#5c4fff;margin-bottom:14px}}
.action-item{{display:flex;gap:12px;margin-bottom:12px;align-items:flex-start}}
.action-num{{background:#5c4fff;color:white;font-size:12px;font-weight:700;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}}
.action-text{{font-size:14px;color:#374151;line-height:1.6}}
.action-text strong{{color:#1e1e2e}}
.trend-box{{background:#f0fdf4;border-left:3px solid #22c55e;padding:10px 14px;border-radius:0 8px 8px 0;margin:10px 0;font-size:13px;color:#166534}}
h2{{font-size:15px;font-weight:700;color:#1e1e2e;margin-bottom:12px}}
h3{{font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin:12px 0 7px}}
p{{margin-bottom:8px;font-size:14px;color:#374151;line-height:1.7}}
li{{font-size:14px;color:#374151;margin-left:20px;margin-bottom:4px;line-height:1.6}}
strong{{color:#1e1e2e}}
blockquote{{background:#fef3c7;border-left:3px solid #f59e0b;padding:10px 14px;border-radius:0 8px 8px 0;font-size:13px;color:#92400e;margin:10px 0}}
hr{{border:none;border-top:1px solid #e8e8f0;margin:16px 0}}

/* ── Empty State ── */
.empty-state{{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:60vh;color:#9ca3af;text-align:center;
}}
.empty-state .icon{{font-size:48px;margin-bottom:16px}}
.empty-state h3{{font-size:16px;font-weight:600;color:#6b7280;margin-bottom:8px}}
.empty-state p{{font-size:14px}}

/* ── No results ── */
.no-results{{padding:20px;text-align:center;font-size:13px;color:#9ca3af}}
</style>
</head>
<body>

<!-- Top Bar -->
<div class="topbar">
  <div class="topbar-logo">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect width="20" height="20" rx="5" fill="rgba(255,255,255,0.2)"/>
      <circle cx="10" cy="10" r="4" fill="white" opacity="0.9"/>
      <circle cx="10" cy="10" r="2" fill="#5c4fff"/>
    </svg>
    Insightto <span>竞品情报中心</span>
  </div>
  <div class="topbar-divider"></div>
  <div class="topbar-title">Competitor Intelligence Hub</div>
  <div class="topbar-right">
    <span class="topbar-badge">自动更新</span>
    &nbsp; 最后构建：{now_str}
  </div>
</div>

<!-- Layout -->
<div class="layout">

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>报告目录</h2>
      <div class="sidebar-search">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="6" cy="6" r="4.5" stroke="#9ca3af" stroke-width="1.3"/>
          <path d="M9.5 9.5L12 12" stroke="#9ca3af" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <input type="text" id="search-input" placeholder="搜索报告..." oninput="filterReports(this.value)">
      </div>
    </div>
    <div class="sidebar-scroll" id="sidebar-list">
      <!-- 由 JS 渲染 -->
    </div>
  </div>

  <!-- Main -->
  <div class="main" id="main-content">
    {content_sections}
  </div>

</div>

<script>
const REPORTS = {sidebar_data};

function renderSidebar(list) {{
  const container = document.getElementById('sidebar-list');
  if (!list.length) {{
    container.innerHTML = '<div class="no-results">没有找到匹配的报告</div>';
    return;
  }}

  // 按月分组
  const groups = {{}};
  list.forEach(r => {{
    const month = r.date ? r.date.slice(0, 7) : '未知';
    if (!groups[month]) groups[month] = [];
    groups[month].push(r);
  }});

  let html = '';
  Object.keys(groups).sort().reverse().forEach(month => {{
    html += `<div class="sidebar-group">
      <div class="sidebar-group-label">${{month}}</div>`;
    groups[month].forEach(r => {{
      const isWeekly = r.type === 'weekly';
      const icon = isWeekly ? '📊' : '📋';
      const iconClass = isWeekly ? 'icon-weekly' : 'icon-daily';
      const typeLabel = isWeekly ? '周报' : '日报';
      html += `
      <div class="sidebar-item" id="nav-${{r.id}}" onclick="showReport('${{r.id}}')">
        <div class="sidebar-item-icon ${{iconClass}}">${{icon}}</div>
        <div class="sidebar-item-info">
          <div class="sidebar-item-date">${{r.date}}</div>
          <div class="sidebar-item-type">${{typeLabel}}</div>
        </div>
        <div class="sidebar-item-dot"></div>
      </div>`;
    }});
    html += '</div>';
  }});
  container.innerHTML = html;
}}

function showReport(id) {{
  // 隐藏所有
  document.querySelectorAll('.report-section').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));

  // 显示目标
  const section = document.getElementById('section-' + id);
  if (section) {{
    section.style.display = 'block';
    document.getElementById('main-content').scrollTop = 0;
  }}

  const nav = document.getElementById('nav-' + id);
  if (nav) nav.classList.add('active');
}}

function filterReports(query) {{
  const q = query.toLowerCase().trim();
  const filtered = q ? REPORTS.filter(r =>
    r.date.includes(q) ||
    r.title.toLowerCase().includes(q) ||
    r.type.includes(q) ||
    (q === '日报' && r.type === 'daily') ||
    (q === '周报' && r.type === 'weekly')
  ) : REPORTS;
  renderSidebar(filtered);

  // 激活第一个
  if (filtered.length) {{
    setTimeout(() => showReport(filtered[0].id), 0);
  }}
}}

// 初始化
renderSidebar(REPORTS);
if (REPORTS.length) {{
  showReport(REPORTS[0].id);
}}
</script>
</body>
</html>"""

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"✓ 情报中心已生成: {OUTPUT}")
    print(f"  共收录 {len(reports)} 份报告")
    for r in reports:
        print(f"  - [{r['type']}] {r['date']} {r['title'][:40]}")


if __name__ == "__main__":
    build_index()
