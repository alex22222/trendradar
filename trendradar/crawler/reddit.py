# coding=utf-8
"""
Reddit 数据源模块

从 Reddit RSS feed 获取热门帖子数据，支持：
- 任意 subreddit 的 RSS feed
- 无需 OAuth 认证（使用公开 RSS）
- 自动重试机制
- 代理支持
- AI 批量翻译（中英文双语显示）
"""

import json
import os
import random
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional

import requests


class RedditFetcher:
    """Reddit 数据获取器（基于 RSS feed）"""

    # Reddit RSS feed 地址模板
    RSS_URL_TEMPLATE = "https://www.reddit.com/r/{subreddit}/hot/.rss"

    # Atom 命名空间
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    # 默认请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/atom+xml,application/xml,text/xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        subreddit: Optional[str] = None,
        limit: int = 25,
        translate: bool = False,
        ai_config: Optional[Dict] = None,
    ):
        """
        初始化 Reddit 数据获取器

        Args:
            proxy_url: 代理服务器 URL（可选）
            subreddit: 指定的 subreddit 名称（可选，默认 popular）
            limit: 获取帖子数量（默认 25）
            translate: 是否启用 AI 翻译（默认 False）
            ai_config: AI 翻译配置（可选，默认从环境变量读取）
        """
        self.proxy_url = proxy_url
        self.subreddit = subreddit or "popular"
        self.limit = min(limit, 100)
        self.rss_url = f"{self.RSS_URL_TEMPLATE.format(subreddit=self.subreddit)}?limit={self.limit}"
        self.translate = translate
        self.ai_config = ai_config or {}

    def fetch_data(
        self,
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str]:
        """
        获取 Reddit RSS feed 数据，支持重试

        Args:
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间（秒）
            max_retry_wait: 最大重试等待时间（秒）

        Returns:
            (响应文本, 平台ID) 元组，失败时响应文本为 None
        """
        platform_id = f"reddit-{self.subreddit}"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    self.rss_url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=15,
                )
                response.raise_for_status()

                # 验证是有效的 XML
                ET.fromstring(response.content)

                print(f"获取 reddit-{self.subreddit} RSS feed 成功")
                return response.text, platform_id

            except ET.ParseError as e:
                # XML 解析错误，不重试
                print(f"解析 reddit-{self.subreddit} RSS XML 失败: {e}")
                return None, platform_id
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"请求 reddit-{self.subreddit} 失败: {e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求 reddit-{self.subreddit} 失败: {e}")
                    return None, platform_id

        return None, platform_id

    def parse_data(self, response_text: str) -> Dict:
        """
        解析 Reddit RSS feed，转换为项目内部格式
        """
        results = {}
        root = ET.fromstring(response_text.encode("utf-8"))

        entries = root.findall(".//atom:entry", self.ATOM_NS)

        for index, entry in enumerate(entries[:self.limit], 1):
            # 获取标题
            title_elem = entry.find("atom:title", self.ATOM_NS)
            if title_elem is None or not title_elem.text:
                continue

            title_en = str(title_elem.text).strip()

            # 获取链接（Reddit 帖子页面）
            link_elem = entry.find("atom:link", self.ATOM_NS)
            url = ""
            if link_elem is not None:
                url = link_elem.get("href", "")

            # 使用 Reddit 帖子页面作为 mobileUrl
            mobile_url = url

            # 使用英文标题作为 key（如果启用了翻译，后续会替换为中文）
            title = title_en

            if title in results:
                results[title]["ranks"].append(index)
            else:
                results[title] = {
                    "ranks": [index],
                    "url": url,
                    "mobileUrl": mobile_url,
                    "title_en": title_en,
                }

        return results

    def translate_titles(self, results: Dict) -> Dict:
        """
        批量翻译 Reddit 标题（英文 → 中文）

        使用 AI API 进行批量翻译。如果未配置 API，则保留英文原文。

        Args:
            results: parse_data 返回的结果字典

        Returns:
            翻译后的结果字典（title 为中文翻译，title_en 保留英文原文）
        """
        if not results:
            return results

        # 从配置或环境变量获取 API Key
        api_key = self.ai_config.get("API_KEY") or os.environ.get("AI_API_KEY", "")
        if not api_key:
            print("[Reddit] 未配置 AI API Key，跳过翻译（保留英文原文）")
            return results

        provider = self.ai_config.get("PROVIDER", "openai")
        model = self.ai_config.get("MODEL", "gpt-4o-mini")
        base_url = self.ai_config.get("BASE_URL", "")
        timeout = self.ai_config.get("TIMEOUT", 60)

        # 准备待翻译的标题
        titles_to_translate = []
        title_keys = []
        for title_key, data in results.items():
            title_en = data.get("title_en", title_key)
            titles_to_translate.append(title_en)
            title_keys.append(title_key)

        if not titles_to_translate:
            return results

        # 构建批量翻译提示词
        titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles_to_translate)])
        prompt = f"""请将以下 Reddit 帖子标题翻译成中文。要求：
1. 保留原文含义，使用自然流畅的中文
2. 保留专有名词（人名、公司名、产品名等）的英文原文
3. 只返回翻译结果，不要解释
4. 保持编号顺序，每行一条

{titles_text}

翻译结果（每行一条）："""

        try:
            print(f"[Reddit] 正在翻译 {len(titles_to_translate)} 个标题...")

            # 调用 AI API
            if provider == "gemini":
                translations = self._call_gemini_translate(prompt, api_key, model, timeout)
            else:
                translations = self._call_openai_translate(prompt, api_key, model, base_url, timeout)

            if translations and len(translations) == len(titles_to_translate):
                # 更新结果字典：用中文标题作为 key，保留 title_en
                translated_results = {}
                for i, (old_key, data) in enumerate(results.items()):
                    cn_title = translations[i].strip()
                    if not cn_title:
                        cn_title = old_key  # 翻译失败，保留原文

                    data_copy = data.copy()
                    data_copy["title_en"] = data.get("title_en", old_key)
                    translated_results[cn_title] = data_copy

                print(f"[Reddit] 翻译完成，{len(translations)} 个标题")
                return translated_results
            else:
                print(f"[Reddit] 翻译结果数量不匹配，保留英文原文")
                return results

        except Exception as e:
            print(f"[Reddit] 翻译失败: {e}")
            return results

    def _call_openai_translate(
        self, prompt: str, api_key: str, model: str, base_url: str, timeout: int
    ) -> List[str]:
        """调用 OpenAI 兼容接口进行翻译"""
        # 验证 API key 有效性
        if '…' in api_key or len(api_key) < 10:
            raise ValueError("API Key 无效（可能是脱敏/占位符），请在 config.yaml 中配置真实的 AI_API_KEY")

        # 预设完整端点
        urls = {
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }
        url = base_url or urls.get("deepseek", "https://api.deepseek.com/v1/chat/completions")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # 解析翻译结果（按行分割）
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        # 移除编号前缀（如 "1. "、"1." 等）
        translations = []
        for line in lines:
            # 移除开头的编号
            if ". " in line[:5]:
                parts = line.split(". ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    translations.append(parts[1])
                    continue
            translations.append(line)

        return translations

    def _call_gemini_translate(
        self, prompt: str, api_key: str, model: str, timeout: int
    ) -> List[str]:
        """调用 Google Gemini API 进行翻译"""
        model = model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
        }

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]

        # 解析翻译结果
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        translations = []
        for line in lines:
            if ". " in line[:5]:
                parts = line.split(". ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    translations.append(parts[1])
                    continue
            translations.append(line)

        return translations

    def crawl(
        self,
        request_interval: int = 100,
    ) -> Tuple[Dict, str, Optional[str]]:
        """
        爬取 Reddit 数据

        Args:
            request_interval: 请求间隔（毫秒）

        Returns:
            (结果字典, 平台ID, 失败ID) 元组
        """
        platform_id = f"reddit-{self.subreddit}"
        response, _ = self.fetch_data()

        if response:
            try:
                results = self.parse_data(response)
                print(f"[Reddit] r/{self.subreddit} 解析成功，{len(results)} 条帖子")

                # 如果启用翻译，批量翻译标题
                if self.translate and results:
                    results = self.translate_titles(results)

                return results, platform_id, None
            except ET.ParseError:
                print(f"[Reddit] r/{self.subreddit} RSS XML 解析失败")
                return {}, platform_id, platform_id
            except Exception as e:
                print(f"[Reddit] r/{self.subreddit} 数据处理出错: {e}")
                return {}, platform_id, platform_id
        else:
            return {}, platform_id, platform_id

    @staticmethod
    def is_reddit_platform(platform_id: str) -> bool:
        """判断平台 ID 是否为 Reddit 平台"""
        return platform_id.startswith("reddit-")

    @staticmethod
    def extract_subreddit(platform_id: str) -> str:
        """从平台 ID 提取 subreddit 名称"""
        return platform_id.replace("reddit-", "")
