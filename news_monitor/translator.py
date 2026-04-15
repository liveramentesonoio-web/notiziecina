from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import requests


DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEFAULT_MODEL = os.getenv("DEEPSEEK_TRANSLATION_MODEL", "deepseek-chat")
FOLLOW_TEXT = "关注了解更多后续。"


@dataclass
class TranslationResult:
    translated_title: str
    translated_published: str
    translated_summary: str
    translated_content: str
    model: str


@dataclass
class RewriteResult:
    rewritten_title: str
    rewritten_summary: str
    model: str


def has_translation_api_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def translate_article_to_chinese(
    *,
    title: str,
    published: str,
    summary: str,
    content_text: str,
) -> TranslationResult:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")

    payload = {
        "model": DEFAULT_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是专业新闻翻译助手。请把意大利语新闻翻译成简体中文。"
                    "保持事实准确，不要添加原文没有的信息。"
                    "输出必须是 JSON，对象中只允许有以下字段："
                    "translated_title, translated_published, translated_summary, translated_content。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请翻译以下新闻内容。\n\n"
                    f"标题：{title}\n"
                    f"发布时间：{published or '未知'}\n"
                    f"摘要：{summary or '无'}\n"
                    f"正文：{content_text[:5000] or summary or title}\n\n"
                    "要求：\n"
                    "1. translated_title：适合中文阅读的新闻标题\n"
                    "2. translated_published：中文表达的发布时间，原文无则写“未知”\n"
                    "3. translated_summary：1到3句中文摘要\n"
                    "4. translated_content：通顺的中文正文翻译"
                ),
            },
        ],
    }

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = _extract_output_text(data)
    parsed = _parse_json_response(text)

    return TranslationResult(
        translated_title=parsed.get("translated_title", "").strip(),
        translated_published=parsed.get("translated_published", "").strip(),
        translated_summary=parsed.get("translated_summary", "").strip(),
        translated_content=parsed.get("translated_content", "").strip(),
        model=data.get("model", DEFAULT_MODEL),
    )


def rewrite_article_for_engagement(
    *,
    title: str,
    published: str,
    summary: str,
    content_text: str,
    translated_title: str = "",
    translated_summary: str = "",
    translated_content: str = "",
    target_length: int = 90,
) -> RewriteResult:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")

    payload = {
        "model": DEFAULT_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是中文新闻新媒体编辑。你的任务是基于新闻事实，输出更抓人但不过度夸张的中文热门稿。"
                    "必须忠于原始事实，不得捏造，不得加入原文没有的情节。"
                    "输出必须是 JSON，对象中只允许有以下字段：rewritten_title, rewritten_summary。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于以下意大利新闻原文，生成适合中文平台传播的内容。\n\n"
                    f"意大利语标题：{title}\n"
                    f"发布时间：{published or '未知'}\n"
                    f"意大利语摘要：{summary or '无'}\n"
                    f"意大利语正文：{content_text[:5000] or summary or title}\n\n"
                    f"已有中文标题参考：{translated_title or '无'}\n"
                    f"已有中文摘要参考：{translated_summary or '无'}\n"
                    f"已有中文正文参考：{translated_content[:1200] or '无'}\n\n"
                    "要求：\n"
                    "1. rewritten_title：写一个吸引人的中文标题，适合大众阅读，但不能脱离事实。\n"
                    f"2. rewritten_summary：写一段大约 {target_length} 字的中文热门导语，"
                    "整体控制在 60 到 120 字之间，要有吸引力，且必须以“关注了解更多后续。”结尾。\n"
                    "3. 不要输出任何 JSON 之外的文字。"
                ),
            },
        ],
    }

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = _extract_output_text(data)
    parsed = _parse_json_response(text)

    return RewriteResult(
        rewritten_title=parsed.get("rewritten_title", "").strip(),
        rewritten_summary=_normalize_rewrite_summary(
            parsed.get("rewritten_summary", "").strip(),
            target_length=target_length,
        ),
        model=data.get("model", DEFAULT_MODEL),
    )


def _extract_output_text(data: dict) -> str:
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("No choices returned from translation API")
    message = choices[0].get("message", {})
    text = (message.get("content") or "").strip()
    if not text:
        raise RuntimeError("No text returned from translation API")
    return text


def _parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError("Model did not return valid JSON")

    candidate = match.group(0)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        candidate = re.sub(r"[\x00-\x1f]", " ", candidate)
        candidate = re.sub(r",\s*}", "}", candidate)
        return json.loads(candidate)


def _normalize_rewrite_summary(text: str, *, target_length: int = 90) -> str:
    summary = " ".join((text or "").split())
    if not summary:
        return FOLLOW_TEXT

    if summary.endswith("关注了解更多后续"):
        summary += "。"
    elif not summary.endswith(FOLLOW_TEXT):
        summary = summary.rstrip("。！! ") + FOLLOW_TEXT

    if 60 <= len(summary) <= 120:
        return summary

    max_len = min(120, max(60, target_length + 15))
    body_limit = max(20, max_len - len(FOLLOW_TEXT))
    body = summary.replace(FOLLOW_TEXT, "").strip().rstrip("。！! ")
    trimmed = body[:body_limit].rstrip("，,；;：: ")
    cut_points = "，。；！？,.!?"
    for index in range(len(trimmed) - 1, 9, -1):
        if trimmed[index] in cut_points:
            trimmed = trimmed[:index].rstrip("，,；;：: ")
            break
    if trimmed and trimmed[-1] not in cut_points:
        trimmed = trimmed.rstrip("，,；;：: ") + "，"
    return trimmed + FOLLOW_TEXT
