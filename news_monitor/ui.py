import json
import uuid

import streamlit as st
import streamlit.components.v1 as components

from news_monitor.database import get_connection, get_monitor_stats, get_regions, list_articles
from news_monitor.service import refresh_articles, rewrite_article, translate_article
from news_monitor.translator import has_translation_api_key


REGION_LABELS = {
    "Prato": "Prato / 普拉托",
    "Milano": "Milano / 米兰",
    "Roma": "Roma / 罗马",
    "Toscana": "Toscana / 托斯卡纳",
    "Lombardia": "Lombardia / 伦巴第",
    "China": "China / 中国",
}


def _badge_list(values: str) -> str:
    try:
        items = json.loads(values or "[]")
    except json.JSONDecodeError:
        items = []
    return " | ".join(items)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        html, body, [class*="css"]  {
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
          background: linear-gradient(135deg, #fffaf2 0%, #ffffff 60%, #f8fafc 100%);
          border: 1px solid #fde6c8;
          border-radius: 20px;
          padding: 16px 18px 12px 18px;
          margin-bottom: 12px;
        }
        .app-subtitle {
          color: #475569;
          font-size: 0.97rem;
          margin-bottom: 0;
        }
        .status-box {
          background: linear-gradient(180deg, #fffdf8 0%, #ffffff 100%);
          border: 1px solid #f5e7c8;
          border-radius: 14px;
          padding: 12px 14px;
          margin: 8px 0 16px 0;
        }
        .article-meta {
          color: #64748b;
          font-size: 0.88rem;
          line-height: 1.5;
        }
        .label-chip {
          display: inline-block;
          padding: 4px 9px;
          border-radius: 999px;
          background: #f1f5f9;
          color: #475569;
          font-size: 0.79rem;
          margin: 4px 6px 0 0;
        }
        .article-section-title {
          font-weight: 700;
          font-size: 0.92rem;
          margin-top: 10px;
          margin-bottom: 4px;
        }
        .translated-box {
          background: #f8fafc;
          border-radius: 12px;
          padding: 10px 12px;
          margin-top: 10px;
          border: 1px solid #e8eef5;
        }
        .rewrite-box {
          background: linear-gradient(180deg, #fff8f1 0%, #ffffff 100%);
          border-radius: 12px;
          padding: 10px 12px;
          margin-top: 10px;
          border: 1px solid #fedec1;
        }
        .thumb-wrap {
          margin: 0 0 10px 0;
        }
        .thumb-wrap img {
          width: min(100%, 168px);
          max-height: 118px;
          object-fit: cover;
          border-radius: 14px;
          display: block;
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
        }
        .compact-title {
          margin-bottom: 0.05rem;
        }
        .article-card {
          background: #ffffff;
          border: 1px solid #edf2f7;
          border-radius: 18px;
          padding: 14px 14px 12px 14px;
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.035);
          margin-bottom: 12px;
        }
        .tool-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: 9px;
          border: 1px solid #dbe2ea;
          background: #ffffff;
          color: #0f172a;
          font-size: 13px;
          line-height: 1;
        }
        .tool-row {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        @media (max-width: 768px) {
          .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
            padding-top: 0.8rem;
          }
          h1 {
            font-size: 1.7rem !important;
            line-height: 1.25 !important;
          }
          .article-meta {
            font-size: 0.86rem;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _region_label(region: str) -> str:
    return REGION_LABELS.get(region, region)


def _render_copy_button(text: str, label: str, key: str) -> None:
    safe_text = json.dumps(text or "", ensure_ascii=False)
    element_id = f"copy-{key}-{uuid.uuid4().hex}"
    components.html(
        f"""
        <div style="margin: 6px 0 8px 0;">
          <button id="{element_id}" style="
            width: 100%;
            border: 1px solid #d4d4d8;
            background: #ffffff;
            color: #111827;
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 14px;
            cursor: pointer;">
            {label}
          </button>
        </div>
        <script>
          const btn = document.getElementById("{element_id}");
          if (btn) {{
            btn.addEventListener("click", async () => {{
              try {{
                await navigator.clipboard.writeText({safe_text});
                btn.innerText = "已复制";
                setTimeout(() => btn.innerText = "{label}", 1200);
              }} catch (e) {{
                btn.innerText = "复制失败";
                setTimeout(() => btn.innerText = "{label}", 1200);
              }}
            }});
          }}
        </script>
        """,
        height=48,
    )


def _render_small_button(text: str, label: str, key: str) -> None:
    safe_text = json.dumps(text or "", ensure_ascii=False)
    element_id = f"copy-icon-{key}-{uuid.uuid4().hex}"
    components.html(
        f"""
        <div style="display:flex;justify-content:flex-end;">
          <button id="{element_id}" class="tool-btn" style="
            cursor:pointer;
            width:auto;
            min-width:58px;
            padding:0 10px;
            font-size:12px;">
            {label}
          </button>
        </div>
        <script>
          const btn = document.getElementById("{element_id}");
          if (btn) {{
            btn.addEventListener("click", async () => {{
              try {{
                await navigator.clipboard.writeText({safe_text});
                btn.innerText = "已复制";
                setTimeout(() => btn.innerText = "{label}", 1000);
              }} catch (e) {{
                btn.innerText = "失败";
                setTimeout(() => btn.innerText = "{label}", 1000);
              }}
            }});
          }}
        </script>
        """,
        height=32,
    )


def _sync_visible_count(target_count: int, result_count: int) -> None:
    if "visible_article_count" not in st.session_state:
        st.session_state.visible_article_count = min(10, max(result_count, 1))

    filter_signature = (
        target_count,
        result_count,
    )
    if st.session_state.get("visible_filter_signature") != filter_signature:
        st.session_state.visible_filter_signature = filter_signature
        st.session_state.visible_article_count = min(10, max(result_count, 1))


def main() -> None:
    st.set_page_config(
        page_title="华人新闻",
        page_icon="📰",
        layout="wide",
    )
    _inject_styles()

    st.markdown('<div class="header-card">', unsafe_allow_html=True)
    st.title("华人新闻")
    st.markdown(
        '<div class="app-subtitle">聚合意大利 RSS 新闻，重点筛选与华人群体、执法、犯罪、移民和社会事件相关的内容。</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("控制面板")
        enrich_articles = st.toggle("抓取文章详情页，用于补充图片和正文", value=True)
        max_enriched_articles = st.slider(
            "每次刷新最多深度抓取的文章数",
            min_value=0,
            max_value=300,
            value=40,
            step=10,
            disabled=not enrich_articles,
        )
        relevant_only = st.toggle("只显示命中核心规则的结果", value=True)
        min_score = st.slider("最低分数", min_value=0, max_value=60, value=18, step=1)
        target_count = st.slider("希望至少保留的相关文章数量", min_value=5, max_value=100, value=20, step=5)
        rewrite_length = st.slider("热门改写字数", min_value=40, max_value=600, value=150, step=10)
        keyword = st.text_input("关键词搜索", placeholder="税务 / immigrazione / rapina ...")

        if st.button("刷新 RSS", type="primary", width="stretch"):
            with st.spinner("正在抓取 RSS 和文章详情页..."):
                result = refresh_articles(
                    enrich_articles=enrich_articles,
                    max_enriched_articles=max_enriched_articles,
                )
            st.success(
                f"本次新增抓取 {result.total_count} 条，写入 {result.inserted_or_updated} 条，"
                f"新命中 {result.relevant_count} 条。已自动跳过 {result.skipped_existing} 条本地已存在链接。"
            )

        st.divider()
        st.subheader("中文翻译")
        if has_translation_api_key():
            st.caption("已检测到 DeepSeek API 密钥，可直接在当前页面翻译并缓存当前文章。")
        else:
            st.warning("未检测到 DeepSeek API 密钥，暂时不能在页面内翻译文章。")

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

    visible_rows = rows[: st.session_state.visible_article_count]
    st.subheader(f"文章列表（显示 {len(visible_rows)} / {len(rows)}）")
    if not visible_rows:
        st.info("当前没有符合条件的文章，可以先刷新 RSS 或降低最低分数。")
        return

    for row in visible_rows:
        st.markdown('<div class="article-card">', unsafe_allow_html=True)
        with st.container():
            if row["image_url"]:
                st.markdown(
                    f'<div class="thumb-wrap"><img src="{row["image_url"]}" alt="article image"></div>',
                    unsafe_allow_html=True,
                )

            title_cols = st.columns([12, 1.2, 1.2, 1.2], vertical_alignment="center")
            with title_cols[0]:
                st.markdown(f'<div class="compact-title">### [{row["title"]}]({row["link"]})</div>', unsafe_allow_html=True)
            with title_cols[1]:
                if not row["translated_content"] and has_translation_api_key():
                    if st.button("译", key=f"translate-{row['id']}", help="翻译当前文章", width="stretch"):
                        with st.spinner("正在翻译并写入本地..."):
                            try:
                                translate_article(row)
                            except Exception as exc:
                                st.error(f"翻译失败：{exc}")
                            else:
                                st.success("翻译完成。")
                                st.rerun()
            with title_cols[2]:
                if not row["rewritten_summary"] and has_translation_api_key():
                    if st.button("生成", key=f"rewrite-{row['id']}", help="生成热门改写", width="stretch"):
                        with st.spinner("正在生成热门稿..."):
                            try:
                                rewrite_article(row, target_length=rewrite_length)
                            except Exception as exc:
                                st.error(f"生成失败：{exc}")
                            else:
                                st.success("热门稿生成完成。")
                                st.rerun()

            st.markdown(
                f'<div class="article-meta">来源：{row["source_name"]} | 地区：{_region_label(row["source_region"])} | '
                f'相关度：{row["score"]} | 发布时间：{row["published"] or "未知"}</div>',
                unsafe_allow_html=True,
            )
            if row["summary"]:
                st.write(row["summary"])
            if row["content_text"]:
                st.caption(row["content_text"][:600] + ("..." if len(row["content_text"]) > 600 else ""))

            badges = _badge_list(row["matched_keywords"])
            if badges:
                st.markdown(
                    f'<div class="article-section-title">关键词</div><div class="label-chip">{badges}</div>',
                    unsafe_allow_html=True,
                )

            if row["rewritten_title"] or row["rewritten_summary"]:
                st.markdown('<div class="rewrite-box"><strong>热门改写</strong></div>', unsafe_allow_html=True)
                if row["rewritten_title"]:
                    section_cols = st.columns([12, 1.1], vertical_alignment="center")
                    with section_cols[0]:
                        st.markdown('<div class="article-section-title">热门标题</div>', unsafe_allow_html=True)
                    with section_cols[1]:
                        _render_small_button(row["rewritten_title"], "复制", f"rewrite-title-{row['id']}")
                    st.write(row["rewritten_title"])
                if row["rewritten_summary"]:
                    section_cols = st.columns([12, 1.1], vertical_alignment="center")
                    with section_cols[0]:
                        st.markdown('<div class="article-section-title">热门文案</div>', unsafe_allow_html=True)
                    with section_cols[1]:
                        _render_small_button(row["rewritten_summary"], "复制", f"rewrite-summary-{row['id']}")
                    st.write(row["rewritten_summary"])
                if has_translation_api_key():
                    rewrite_action_cols = st.columns([1, 6])
                    with rewrite_action_cols[0]:
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
                st.markdown('<div class="translated-box"><strong>原文翻译</strong></div>', unsafe_allow_html=True)
                if row["translated_title"]:
                    section_cols = st.columns([12, 1.1], vertical_alignment="center")
                    with section_cols[0]:
                        st.markdown('<div class="article-section-title">中文标题</div>', unsafe_allow_html=True)
                    with section_cols[1]:
                        _render_small_button(row["translated_title"], "复制", f"translated-title-{row['id']}")
                    st.write(row["translated_title"])
                if row["translated_published"]:
                    st.markdown('<div class="article-section-title">中文时间</div>', unsafe_allow_html=True)
                    st.write(row["translated_published"])
                if row["translated_summary"]:
                    section_cols = st.columns([12, 1.1], vertical_alignment="center")
                    with section_cols[0]:
                        st.markdown('<div class="article-section-title">中文摘要</div>', unsafe_allow_html=True)
                    with section_cols[1]:
                        _render_small_button(row["translated_summary"], "复制", f"translated-summary-{row['id']}")
                    st.write(row["translated_summary"])
                if row["translated_content"]:
                    section_cols = st.columns([12, 1.1], vertical_alignment="center")
                    with section_cols[0]:
                        st.markdown('<div class="article-section-title">中文正文</div>', unsafe_allow_html=True)
                    with section_cols[1]:
                        _render_small_button(row["translated_content"], "复制", f"translated-content-{row['id']}")
                    st.write(row["translated_content"])
        st.markdown('</div>', unsafe_allow_html=True)

    if len(rows) > st.session_state.visible_article_count:
        st.caption(f"还有 {len(rows) - st.session_state.visible_article_count} 篇可继续加载")
        if st.button("点击查看更多", width="stretch"):
            st.session_state.visible_article_count += 20
            st.rerun()
