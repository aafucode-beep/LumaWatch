"""提取用的提示词与 JSON Schema。"""
from __future__ import annotations

# 期望大模型输出的 JSON 结构（同时用于 prompt 说明与 Pydantic 校验）
EXTRACTION_SCHEMA_HINT = """
{
  "company": {
    "name": "企业英文/官方名称",
    "name_cn": "中文名（如有，否则 null）",
    "hq_country": "总部所在国家",
    "hq_city": "总部所在城市",
    "founded_year": 1990,
    "history": "企业历史沿革（可多句）",
    "philosophy": "企业哲学/理念/使命愿景",
    "summary": "一句话到一段话的企业概述"
  },
  "offices": [
    {"region": "地区如 Europe/Asia", "country": "国家", "city": "城市",
     "office_type": "branch|distributor|showroom|office|other", "note": "补充说明"}
  ],
  "product_lines": [
    {"name": "产品线/品类名", "category": "上级归类如 室内/室外/轨道",
     "description": "简述", "children": [{"name": "子类", "description": ""}]}
  ],
  "tags": [
    {"name": "标签名如 天花嵌入式灯具", "dimension": "产品类型|应用场景|地区|企业属性"}
  ],
  "downloads": [
    {"title": "资源标题", "url": "下载链接（必须是页面中真实出现的绝对URL）",
     "resource_type": "catalog|ies|datasheet|bim|certificate|manual|other"}
  ],
  "news": [
    {"title": "新闻标题", "url": "新闻链接", "published_date": "YYYY-MM-DD 或 null",
     "summary": "简述或 null"}
  ]
}
"""

SYSTEM_PROMPT = """你是建筑照明行业的资料分析专家。你的任务是从抓取到的企业官网内容中，\
提取结构化的企业情报。要求：
1. 只依据提供的网页文本，严禁编造。信息缺失就填 null 或空数组。
2. 产品线要体现照明行业的品类结构（如天花嵌入式、轨道灯、线性灯、洗墙灯、办公吊灯、\
庭院灯、投光灯等），可用层级 children 表达。
3. tags 用于检索：产品类型维度尽量拆成具体品类；应用场景维度如 办公/商业/酒店/景观/\
工业；企业属性维度如 高端/工程渠道/OEM 等；地区维度可放总部所在大区。
4. downloads 和 news 的 url 必须来自我在“可下载链接候选/新闻链接候选”中提供的真实链接，\
不要臆造 URL；从候选中筛选并补充合理标题与类型。
5. 严格输出与给定 JSON 结构一致的合法 JSON，不要输出任何多余文字或 markdown 代码块。"""


def build_user_prompt(
    site_text: str, download_candidates: list[dict], news_candidates: list[dict]
) -> str:
    def fmt(items: list[dict], keys: list[str]) -> str:
        lines = []
        for it in items[:60]:
            parts = [f"{k}={it.get(k)}" for k in keys if it.get(k)]
            lines.append("- " + "; ".join(parts))
        return "\n".join(lines) if lines else "（无）"

    dl = fmt(download_candidates, ["title", "url", "resource_type", "file_ext"])
    nw = fmt(news_candidates, ["title", "url"])
    return f"""请按下面的 JSON 结构提取信息：
{EXTRACTION_SCHEMA_HINT}

====== 网页正文内容 ======
{site_text}

====== 可下载链接候选（url 必须从这里选） ======
{dl}

====== 新闻链接候选（url 必须从这里选） ======
{nw}

现在只输出合法 JSON。"""
