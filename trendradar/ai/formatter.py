# coding=utf-8
"""
AI 分析结果格式化模块

将 AI 分析结果格式化为各推送渠道的样式
"""

import html as html_lib
import re
from .analyzer import AIAnalysisResult


def _clean_markdown_code(text: str) -> str:
    """清理 markdown 代码标记和 HTML 标签（用于飞书 text 消息）

    清理规则：
    - 去除 HTML <font> 标签（保留内容）
    - 去除 markdown 代码块（```...```）及语言标识
    - 去除行内代码标记（`...`）但保留内容
    - 去除多余的空行
    """
    if not text:
        return text

    # 1. 去除 HTML <font> 标签（保留内容）
    text = re.sub(r"<font[^>]*>(.*?)</font>", r"\1", text, flags=re.DOTALL)

    # 2. 去除 markdown 代码块
    text = re.sub(r"```[\w]*\n(.*?)\n```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"```(.*?)```", r"\1", text, flags=re.DOTALL)

    # 3. 去除行内代码标记
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 4. 去除多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符，防止 XSS 攻击"""
    return html_lib.escape(text) if text else ""


def render_ai_analysis_markdown(result: AIAnalysisResult) -> str:
    """渲染为通用 Markdown 格式（Telegram、企业微信、ntfy、Bark、Slack）"""
    if not result.success:
        return f"⚠️ AI 分析失败: {result.error}"

    lines = ["**✨ AI 热点分析**", ""]

    if result.summary:
        lines.extend(["**趋势概述**", result.summary, ""])

    if result.keyword_analysis:
        lines.extend(["**热度走势**", result.keyword_analysis, ""])

    if result.sentiment:
        lines.extend(["**情感倾向**", result.sentiment, ""])

    if result.cross_platform:
        lines.extend(["**跨平台关联**", result.cross_platform, ""])

    if result.impact:
        lines.extend(["**潜在影响**", result.impact, ""])

    if result.signals:
        lines.extend(["**值得关注**", result.signals, ""])

    if result.conclusion:
        lines.extend(["**总结建议**", result.conclusion])

    return "\n".join(lines)


def render_ai_analysis_feishu(result: AIAnalysisResult) -> str:
    """渲染为飞书卡片 Markdown 格式"""
    if not result.success:
        return f"⚠️ AI 分析失败: {result.error}"

    lines = ["**✨ AI 热点分析**", ""]

    if result.summary:
        lines.extend(["**趋势概述**", _clean_markdown_code(result.summary), ""])

    if result.keyword_analysis:
        lines.extend(["**热度走势**", _clean_markdown_code(result.keyword_analysis), ""])

    if result.sentiment:
        lines.extend(["**情感倾向**", _clean_markdown_code(result.sentiment), ""])

    if result.cross_platform:
        lines.extend(["**跨平台关联**", _clean_markdown_code(result.cross_platform), ""])

    if result.impact:
        lines.extend(["**潜在影响**", _clean_markdown_code(result.impact), ""])

    if result.signals:
        lines.extend(["**值得关注**", _clean_markdown_code(result.signals), ""])

    if result.conclusion:
        lines.extend(["**总结建议**", _clean_markdown_code(result.conclusion)])

    return "\n".join(lines)


def render_ai_analysis_dingtalk(result: AIAnalysisResult) -> str:
    """渲染为钉钉 Markdown 格式"""
    if not result.success:
        return f"⚠️ AI 分析失败: {result.error}"

    lines = ["### ✨ AI 热点分析", ""]

    if result.summary:
        lines.extend(["#### 趋势概述", result.summary, ""])

    if result.keyword_analysis:
        lines.extend(["#### 热度走势", result.keyword_analysis, ""])

    if result.sentiment:
        lines.extend(["#### 情感倾向", result.sentiment, ""])

    if result.cross_platform:
        lines.extend(["#### 跨平台关联", result.cross_platform, ""])

    if result.impact:
        lines.extend(["#### 潜在影响", result.impact, ""])

    if result.signals:
        lines.extend(["#### 值得关注", result.signals, ""])

    if result.conclusion:
        lines.extend(["#### 总结建议", result.conclusion])

    return "\n".join(lines)


def render_ai_analysis_html(result: AIAnalysisResult) -> str:
    """渲染为 HTML 格式（邮件）"""
    if not result.success:
        return f'<div class="ai-error">⚠️ AI 分析失败: {_escape_html(result.error)}</div>'

    html_parts = ['<div class="ai-analysis">', '<h3>✨ AI 热点分析</h3>']

    if result.summary:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>趋势概述</h4>',
            f'<p>{_escape_html(result.summary)}</p>',
            '</div>'
        ])

    if result.keyword_analysis:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>热度走势</h4>',
            f'<p>{_escape_html(result.keyword_analysis)}</p>',
            '</div>'
        ])

    if result.sentiment:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>情感倾向</h4>',
            f'<p>{_escape_html(result.sentiment)}</p>',
            '</div>'
        ])

    if result.cross_platform:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>跨平台关联</h4>',
            f'<p>{_escape_html(result.cross_platform)}</p>',
            '</div>'
        ])

    if result.impact:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>潜在影响</h4>',
            f'<p>{_escape_html(result.impact)}</p>',
            '</div>'
        ])

    if result.signals:
        html_parts.extend([
            '<div class="ai-section">',
            '<h4>值得关注</h4>',
            f'<p>{_escape_html(result.signals)}</p>',
            '</div>'
        ])

    if result.conclusion:
        html_parts.extend([
            '<div class="ai-section ai-conclusion">',
            '<h4>总结建议</h4>',
            f'<p>{_escape_html(result.conclusion)}</p>',
            '</div>'
        ])

    html_parts.append('</div>')
    return "\n".join(html_parts)


def render_ai_analysis_plain(result: AIAnalysisResult) -> str:
    """渲染为纯文本格式"""
    if not result.success:
        return f"AI 分析失败: {result.error}"

    lines = ["【AI 热点分析】", ""]

    if result.summary:
        lines.extend(["[趋势概述]", _clean_markdown_code(result.summary), ""])

    if result.keyword_analysis:
        lines.extend(["[热度走势]", _clean_markdown_code(result.keyword_analysis), ""])

    if result.sentiment:
        lines.extend(["[情感倾向]", _clean_markdown_code(result.sentiment), ""])

    if result.cross_platform:
        lines.extend(["[跨平台关联]", _clean_markdown_code(result.cross_platform), ""])

    if result.impact:
        lines.extend(["[潜在影响]", _clean_markdown_code(result.impact), ""])

    if result.signals:
        lines.extend(["[值得关注]", _clean_markdown_code(result.signals), ""])

    if result.conclusion:
        lines.extend(["[总结建议]", _clean_markdown_code(result.conclusion)])

    return "\n".join(lines)


def get_ai_analysis_renderer(channel: str):
    """根据渠道获取对应的渲染函数"""
    renderers = {
        "feishu": render_ai_analysis_feishu,
        "dingtalk": render_ai_analysis_dingtalk,
        "wework": render_ai_analysis_markdown,
        "telegram": render_ai_analysis_markdown,
        "email": render_ai_analysis_html,
        "ntfy": render_ai_analysis_markdown,
        "bark": render_ai_analysis_plain,
        "slack": render_ai_analysis_markdown,
    }
    return renderers.get(channel, render_ai_analysis_markdown)
