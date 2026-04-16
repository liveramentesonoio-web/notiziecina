import html
import json
import uuid

import streamlit as st

from news_monitor.config import KEYWORD_GROUPS, KEYWORD_TRANSLATIONS
from news_monitor.database import get_connection, get_monitor_stats, get_regions, list_articles
from news_monitor.service import refresh_articles, rewrite_article
from news_monitor.translator import has_translation_api_key


REGION_LABELS = {
    "Prato": "Prato / 普拉托",
    "Milano": "Milano / 米兰",
    "Roma": "Roma / 罗马",
    "Toscana": "Toscana / 托斯卡纳",
    "Lombardia": "Lombardia / 伦巴第",
    "China": "China / 中国",
}


def _keyword_badges(values: str) -> list[str]:
    try:
        items = json.loads(values or "[]")
    except json.JSONDecodeError:
        items = []
    return [KEYWORD_TRANSLATIONS.get(item, item) for item in items]


def _region_label(region: str) -> str:
    return REGION_LABELS.get(region, region)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
          font-family: "Source Han Sans SC", "Noto Sans CJK SC", "Noto Sans SC",
                       "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        .block-container {
          max-width: 980px;
          padding-top: 1rem;
          padding-bottom: 4rem;
          padding-left: 1rem;
          padding-right: 1rem;
        }
        .header-card {
          background: linear-gradient(135deg, #fff8ef 0%, #ffffff 62%, #fff4f1 100%);
          border: 1px solid #f7d8cf;
          border-radius: 24px;
          padding: 18px 18px 14px 18px;
          margin-bottom: 14px;
          box-shadow: 0 18px 40px rgba(15, 23, 42, 0.04);
        }
        .app-subtitle {
          color: #596579;
          font-size: 0.97rem;
          line-height: 1.55;
        }
        .status-box {
          background: linear-gradient(180deg, #fffdf9 0%, #ffffff 100%);
          border: 1px solid #f0e3d1;
          border-radius: 16px;
          padding: 12px 14px;
          margin: 10px 0 14px 0;
        }
        .sidebar-tip {
          color: #64748b;
          font-size: 0.82rem;
          line-height: 1.55;
        }
        .sidebar-keywords {
          background: #faf8f6;
          border: 1px solid #ece4dd;
          border-radius: 16px;
          padding: 10px 12px;
          margin-top: 10px;
        }
        .sidebar-keywords-title {
          font-weight: 700;
          font-size: 0.9rem;
          margin-bottom: 8px;
          color: #0f172a;
        }
        .sidebar-keywords-group {
          font-size: 0.83rem;
          color: #334155;
          margin-top: 8px;
          margin-bottom: 4px;
          font-weight: 700;
        }
        .sidebar-keywords-text {
          font-size: 0.79rem;
          color: #64748b;
          line-height: 1.55;
        }
        .article-divider {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 20px 0 14px 0;
        }
        .article-divider-line {
          flex: 1;
          height: 2px;
          background: linear-gradient(90deg, rgba(220,38,38,0.18), rgba(220,38,38,0.78), rgba(220,38,38,0.18));
          border-radius: 999px;
        }
        .article-score-circle {
          width: 78px;
          height: 78px;
          border-radius: 50%;
          background: radial-gradient(circle at 30% 30%, #fff1f2 0%, #ffe4e6 28%, #ef4444 100%);
          color: #7f1d1d;
          border: 1px solid #fca5a5;
          box-shadow: 0 12px 28px rgba(220, 38, 38, 0.18);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          line-height: 1.1;
          text-align: center;
          flex-shrink: 0;
        }
        .article-score-circle small {
          font-size: 0.7rem;
          margin-bottom: 2px;
        }
        .article-score-circle strong {
          font-size: 1.18rem;
          color: #ffffff;
          text-shadow: 0 1px 2px rgba(127, 29, 29, 0.35);
        }
        .meta-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 6px 0 10px 0;
        }
        .meta-pill {
          display: inline-flex;
          align-items: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          color: #475569;
          font-size: 0.82rem;
          line-height: 1.2;
        }
        .meta-pill strong {
          margin-right: 4px;
          color: #0f172a;
        }
        .keyword-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 8px;
          margin-bottom: 8px;
        }
        .keyword-chip {
          display: inline-flex;
          align-items: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: #fff5f5;
          border: 1px solid #fecaca;
          color: #9f1239;
          font-size: 0.8rem;
          line-height: 1.2;
        }
        .status-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 4px 0 10px 0;
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 5px 10px;
          border-radius: 999px;
          font-size: 0.76rem;
          border: 1px solid #d1d5db;
          color: #334155;
          background: #f8fafc;
        }
        .status-ok {
          background: #f0fdf4;
          border-color: #86efac;
          color: #166534;
        }
        .status-warn {
          background: #fff7ed;
          border-color: #fdba74;
          color: #9a3412;
        }
        .section-box {
          border-radius: 16px;
          padding: 12px 13px;
          border: 1px solid #e5e7eb;
          margin-top: 10px;
        }
        .section-box.section-translation {
          background: #f8fafc;
          border-color: #e2e8f0;
        }
        .section-box.section-rewrite {
          background: linear-gradient(180deg, #fff8f1 0%, #fffdfb 100%);
          border-color: #fed7aa;
        }
        .section-kicker {
          color: #7c2d12;
          font-size: 0.8rem;
          font-weight: 800;
          letter-spacing: 0.02em;
          margin-bottom: 8px;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.rewrite-shell) {
          border: 1.5px solid rgba(251, 146, 60, 0.95) !important;
          box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.08), 0 12px 26px rgba(251, 146, 60, 0.08);
          background: linear-gradient(180deg, rgba(255, 247, 237, 0.82) 0%, rgba(255, 255, 255, 0.98) 100%);
        }
        .section-title {
          font-weight: 700;
          font-size: 0.92rem;
          margin: 0;
          color: #0f172a;
        }
        .content-block {
          background: rgba(255,255,255,0.82);
          border: 1px solid rgba(226,232,240,0.85);
          border-radius: 14px;
          padding: 10px 11px;
          margin-top: 8px;
        }
        .thumb-wrap img {
          width: min(100%, 240px);
          max-height: 164px;
          object-fit: cover;
          border-radius: 16px;
          display: block;
          box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
          margin-bottom: 8px;
        }
        .original-expander {
          margin-top: 10px;
        }
        @media (max-width: 768px) {
          .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 0.8rem;
          }
          .article-divider {
            gap: 8px;
            margin: 18px 0 12px 0;
          }
          .article-score-circle {
            width: 66px;
            height: 66px;
          }
          .article-score-circle small {
            font-size: 0.64rem;
          }
          .article-score-circle strong {
            font-size: 1rem;
          }
          .thumb-wrap img {
            width: min(100%, 188px);
            max-height: 134px;
          }
          .content-block {
            padding: 9px 10px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_copy_button(text: str, key: str) -> None:
    element_id = f"copy-btn-{key}-{uuid.uuid4().hex}"
    safe_text = json.dumps(text or "", ensure_ascii=False)
    st.html(
        f"""
        <button type="button" id="{element_id}" style="
          border:none;
          background:#16a34a;
          color:#ffffff;
          border-radius:999px;
          padding:6px 11px;
          font-size:12px;
          font-weight:700;
          cursor:pointer;
          line-height:1;
          white-space:nowrap;">
          复制
        </button>
        <script>
          const btn = document.getElementById("{element_id}");
          async function copyText(text) {{
            if (navigator.clipboard && window.isSecureContext) {{
              await navigator.clipboard.writeText(text);
              return true;
            }}

            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.setAttribute("readonly", "");
            textArea.style.position = "fixed";
            textArea.style.opacity = "0";
            textArea.style.pointerEvents = "none";
            textArea.style.top = "0";
            textArea.style.left = "0";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            textArea.setSelectionRange(0, text.length);
            let copied = false;
            try {{
              copied = document.execCommand("copy");
            }} finally {{
              document.body.removeChild(textArea);
            }}
            if (!copied) {{
              throw new Error("copy failed");
            }}
            return true;
          }}
          if (btn) {{
            btn.addEventListener("click", async () => {{
              try {{
                await copyText({safe_text});
                const original = btn.innerText;
                btn.innerText = "已复制";
                setTimeout(() => btn.innerText = original, 1200);
              }} catch (e) {{
                btn.innerText = "失败";
                setTimeout(() => btn.innerText = "复制", 1200);
              }}
            }});
          }}
        </script>
        """
    )


def _safe_block(text: str) -> str:
    return html.escape(text or "").replace("\n", "<br>")


def _render_meta(row) -> None:
    st.markdown(
        f"""
        <div class="meta-row">
          <span class="meta-pill"><strong>编号</strong>NC-{int(row["id"]):06d}</span>
          <span class="meta-pill"><strong>来源</strong>{row["source_name"]}</span>
          <span class="meta-pill"><strong>地区</strong>{_region_label(row["source_region"])}</span>
          <span class="meta-pill"><strong>发布时间</strong>{row["published"] or "未知"}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_keywords(row) -> None:
    badges = _keyword_badges(row["matched_keywords"])
    if not badges:
        return
    chips = "".join(f'<span class="keyword-chip">{badge}</span>' for badge in badges)
    st.markdown(
        f"""
        <div class="section-title">关键词</div>
        <div class="keyword-row">{chips}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_status(row) -> None:
    translate_status = (
        '<span class="status-pill status-ok">翻译完成</span>'
        if row["translated_content"]
        else '<span class="status-pill status-warn">待翻译</span>'
    )
    rewrite_status = (
        '<span class="status-pill status-ok">改写完成</span>'
        if row["rewritten_summary"]
        else '<span class="status-pill status-warn">待改写</span>'
    )
    st.markdown(
        f'<div class="status-row">{translate_status}{rewrite_status}</div>',
        unsafe_allow_html=True,
    )


def _render_section_header(title: str, copy_text: str | None, key: str) -> None:
    cols = st.columns([8.5, 1.5], vertical_alignment="center")
    with cols[0]:
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    with cols[1]:
        if copy_text:
            _render_copy_button(copy_text, key)


def _sync_visible_count(target_count: int, result_count: int) -> None:
    if "visible_article_count" not in st.session_state:
        st.session_state.visible_article_count = min(10, max(result_count, 1))

    filter_signature = (target_count, result_count)
    if st.session_state.get("visible_filter_signature") != filter_signature:
        st.session_state.visible_filter_signature = filter_signature
        st.session_state.visible_article_count = min(10, max(result_count, 1))


def main() -> None:
    st.set_page_config(page_title="华人新闻", page_icon="📰", layout="wide")
    _inject_styles()

    st.markdown('<div class="header-card">', unsafe_allow_html=True)
    st.title("华人新闻")
    st.markdown(
        '<div class="app-subtitle">聚合意大利官方和主流媒体 RSS，重点筛选与华人群体、执法、犯罪、移民和社会事件相关的内容。</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.sidebar:
        st.header("控制面板")
        st.markdown(
            '<div class="sidebar-tip">当前版本以 RSS 抓取为主，刷新时会自动跳过本地已存在链接，并补齐未完成的翻译和热门改写。</div>',
            unsafe_allow_html=True,
        )
        enrich_articles = st.toggle("补充正文和图片", value=True)
        max_enriched_articles = st.slider(
            "单次深抓上限",
            min_value=0,
            max_value=300,
            value=40,
            step=10,
            disabled=not enrich_articles,
        )
        relevant_only = st.toggle("只看核心结果", value=True)
        min_score = st.slider("相关度下限", min_value=0, max_value=60, value=18, step=1)
        sort_label = st.selectbox("排序方式", ["最新优先", "相关度优先"], index=0)
        target_count = st.slider("目标文章数", min_value=5, max_value=100, value=20, step=5)
        rewrite_length = st.slider("改写字数", min_value=40, max_value=600, value=150, step=10)
        keyword = st.text_input("站内搜索", placeholder="税务 / immigrazione / rapina ...")

        if st.button("刷新 RSS", type="primary", width="stretch"):
            with st.spinner("正在抓取 RSS、补齐翻译和热门改写..."):
                result = refresh_articles(
                    enrich_articles=enrich_articles,
                    max_enriched_articles=max_enriched_articles,
                    auto_translate=True,
                    rewrite_target_length=rewrite_length,
                )
            st.success(
                f"本次新增抓取 {result.total_count} 条，写入 {result.inserted_or_updated} 条，"
                f"新命中 {result.relevant_count} 条，自动翻译 {result.translated_count} 条，"
                f"自动改写 {result.rewritten_count} 条。已自动跳过 {result.skipped_existing} 条本地已存在链接。"
            )

        st.divider()
        st.subheader("AI 功能")
        if has_translation_api_key():
            st.caption("已连接 DeepSeek，刷新时会自动补齐原文翻译和热门改写。")
        else:
            st.warning("未检测到 DeepSeek API 密钥，暂时不能自动翻译或生成热门改写。")

        st.divider()
        st.markdown('<div class="sidebar-keywords">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-keywords-title">监控关键词</div>', unsafe_allow_html=True)
        for group_name, keywords in KEYWORD_GROUPS.items():
            st.markdown(
                f'<div class="sidebar-keywords-group">{group_name}</div>',
                unsafe_allow_html=True,
            )
            bilingual = [KEYWORD_TRANSLATIONS.get(keyword, keyword) for keyword in keywords]
            st.markdown(
                f'<div class="sidebar-keywords-text">{"、".join(bilingual)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    connection = get_connection()
    try:
        if "visible_article_count" not in st.session_state:
            st.session_state.visible_article_count = 10
        regions = ["全部"] + get_regions(connection)
        region_options = {("全部" if region == "全部" else _region_label(region)): region for region in regions}
        selected_region_label = st.selectbox("地区", list(region_options.keys()), index=0)
        selected_region = region_options[selected_region_label]
        selected_region_value = "All" if selected_region == "全部" else selected_region
        monitor_stats = get_monitor_stats(
            connection,
            min_score=min_score,
            relevant_only=relevant_only,
            source_region=selected_region_value,
        )
        rows = list_articles(
            connection,
            relevant_only=relevant_only,
            min_score=min_score,
            source_region=selected_region_value,
            keyword=keyword,
            sort_mode="score" if sort_label == "相关度优先" else "newest",
            limit=max(300, st.session_state.visible_article_count),
        )
    finally:
        connection.close()

    _sync_visible_count(target_count=target_count, result_count=len(rows))
    shortage = max(target_count - monitor_stats["count"], 0)
    if shortage == 0:
        st.markdown(
            f'<div class="status-box"><strong>自检查</strong><br>当前条件下本地已累计 {monitor_stats["count"]} 条相关文章，已达到你设定的目标数量 {target_count}。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            (
                f'<div class="status-box"><strong>自检查</strong><br>'
                f'当前条件下本地只有 {monitor_stats["count"]} 条相关文章，距离目标数量 {target_count} 还差 {shortage} 条。'
                "这通常不是程序漏抓，而是当前各 RSS 源在可见窗口内就只有这么多匹配项。"
                "程序会持续本地累计，并自动跳过已经抓过的链接。</div>"
            ),
            unsafe_allow_html=True,
        )
    if monitor_stats["newest"] or monitor_stats["oldest"]:
        st.caption(
            f"当前结果时间跨度：{monitor_stats['oldest'] or '未知'} 到 {monitor_stats['newest'] or '未知'}"
        )
        st.caption(f"当前排序：{sort_label}")

    visible_rows = rows[: st.session_state.visible_article_count]
    st.subheader(f"文章列表（显示 {len(visible_rows)} / {len(rows)}）")
    if not visible_rows:
        st.info("当前没有符合条件的文章，可以先刷新 RSS 或降低最低分数。")
        return

    for row in visible_rows:
        st.markdown(
            f"""
            <div class="article-divider">
              <div class="article-divider-line"></div>
              <div class="article-score-circle"><small>相关度</small><strong>{row["score"]}</strong></div>
              <div class="article-divider-line"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if row["image_url"]:
            st.markdown(
                f'<div class="thumb-wrap"><img src="{row["image_url"]}" alt="article image"></div>',
                unsafe_allow_html=True,
            )

        title_cols = st.columns([8.5, 1.5], vertical_alignment="center")
        with title_cols[0]:
            st.markdown(f"### [{row['title']}]({row['link']})")
        with title_cols[1]:
            _render_copy_button(row["title"], f"orig-title-{row['id']}")

        _render_meta(row)

        if row["summary"] or row["content_text"]:
            with st.expander("原文摘录", expanded=False):
                if row["summary"]:
                    st.write(row["summary"])
                if row["content_text"]:
                    st.caption(row["content_text"])

        _render_keywords(row)
        _render_status(row)

        if row["rewritten_title"] or row["rewritten_summary"]:
            with st.container(border=True):
                st.markdown('<div class="rewrite-shell"></div>', unsafe_allow_html=True)
                st.markdown('<div class="section-kicker">热门改写</div>', unsafe_allow_html=True)
                if row["rewritten_title"]:
                    _render_section_header("热门标题", row["rewritten_title"], f"rewrite-title-{row['id']}")
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["rewritten_title"])}</div>',
                        unsafe_allow_html=True,
                    )
                if row["rewritten_summary"]:
                    _render_section_header("热门文案", row["rewritten_summary"], f"rewrite-summary-{row['id']}")
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["rewritten_summary"])}</div>',
                        unsafe_allow_html=True,
                    )
                if has_translation_api_key():
                    action_cols = st.columns([1.2, 7.8])
                    with action_cols[0]:
                        if st.button("重写", key=f"rewrite-again-{row['id']}", width="stretch"):
                            with st.spinner("正在重新生成热门稿..."):
                                try:
                                    rewrite_article(row, target_length=rewrite_length)
                                except Exception as exc:
                                    st.error(f"重写失败：{exc}")
                                else:
                                    st.success("热门稿已更新。")
                                    st.rerun()

        if row["translated_title"] or row["translated_summary"] or row["translated_content"]:
            with st.container(border=True):
                st.markdown('<div class="section-kicker">原文翻译</div>', unsafe_allow_html=True)
                if row["translated_title"]:
                    _render_section_header("中文标题", row["translated_title"], f"translated-title-{row['id']}")
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["translated_title"])}</div>',
                        unsafe_allow_html=True,
                    )
                if row["translated_published"]:
                    st.markdown('<div class="section-title" style="margin-top:8px;">中文时间</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["translated_published"])}</div>',
                        unsafe_allow_html=True,
                    )
                if row["translated_summary"]:
                    _render_section_header("中文摘要", row["translated_summary"], f"translated-summary-{row['id']}")
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["translated_summary"])}</div>',
                        unsafe_allow_html=True,
                    )
                if row["translated_content"]:
                    _render_section_header("中文正文", row["translated_content"], f"translated-content-{row['id']}")
                    st.markdown(
                        f'<div class="content-block">{_safe_block(row["translated_content"])}</div>',
                        unsafe_allow_html=True,
                    )

    if len(rows) > st.session_state.visible_article_count:
        st.caption(f"还有 {len(rows) - st.session_state.visible_article_count} 篇可继续加载")
        if st.button("点击查看更多", width="stretch"):
            st.session_state.visible_article_count += 20
            st.rerun()
