"""提取用的提示词与 JSON Schema。"""
from __future__ import annotations

EXTRACTION_SCHEMA_HINT = """
{
  "company": {
    "name": "企业官方名称",
    "name_cn": "常用中文名；没有可靠来源时可做准确翻译",
    "hq_country": "总部国家（中文）",
    "hq_city": "总部城市",
    "founded_year": 1990,
    "history": "中文历史摘要，包含有来源支持的关键年份",
    "philosophy": "中文概括企业理念、使命或可持续战略",
    "summary": "中文情报摘要：定位、规模、技术重点、市场覆盖"
  },
  "offices": [
    {"region": "地区", "country": "国家", "city": "城市",
     "office_type": "branch|distributor|showroom|office|other", "note": "中文说明"}
  ],
  "product_lines": [
    {"name": "官网产品系列或具体品类名称", "category": "室内|室外|控制系统|其他",
     "description": "中文说明：形态、光学/控制特点、安装方式、典型应用",
     "source_url": "来源页面 URL", "source_snippet": "来源原文短句",
     "children": [{"name": "子系列或具体品类", "description": "中文说明",
                    "source_url": "来源页面 URL", "source_snippet": "来源原文短句"}]}
  ],
  "projects": [
    {"name": "项目名称", "location": "地点", "country": "国家",
     "application": "博物馆|零售|办公|酒店|公共空间|户外等",
     "architect": "建筑师或事务所", "lighting_designer": "照明设计方",
     "completion_year": 2024, "products": "明确提到的产品或系列",
     "summary": "中文案例摘要", "source_url": "项目页面 URL"}
  ],
  "insights": [
    {"category": "产品|技术|市场|渠道|项目|可持续|其他",
     "title": "简短中文标题", "summary": "有事实支撑的中文洞察",
     "relevance": "它对选型、竞品或市场研究为什么重要",
     "source_url": "来源页面 URL"}
  ],
  "tags": [
    {"name": "具体中文标签", "dimension": "产品类型|应用场景|地区|企业属性|技术能力"}
  ],
  "downloads": [
    {"title": "资源标题", "url": "候选中真实出现的绝对 URL",
     "resource_type": "catalog|ies|datasheet|bim|certificate|manual|other",
     "note": "中文说明该资源用途"}
  ],
  "news": [
    {"title": "真实文章标题", "url": "真实文章链接", "published_date": "YYYY-MM-DD 或 null",
     "summary": "中文摘要或 null"}
  ],
  "evidence": [
    {"field": "company.summary 等字段路径", "source_url": "抓取页面 URL",
     "snippet": "来源页面中的原文短句，不要翻译"}
  ]
}
"""

SYSTEM_PROMPT = """你是建筑照明行业的资深研究分析师。你的任务不是制作宣传摘要，而是从企业官网内容中提取可支持产品选型、竞品分析和市场研究的结构化情报。

必须遵守：
1. 只依据提供的网页正文和候选链接，严禁编造。缺失就填 null 或空数组。
2. 除官方名称、产品系列名、项目名和原文证据外，summary、history、philosophy、description、insights、news.summary 等解释性文字全部用简体中文。
3. 产品线必须优先提取官网明确出现的系列、灯具品类和技术能力。不要只返回“Indoor/Outdoor”这种一级导航；至少继续拆分到轨道灯、筒灯、洗墙灯、线性灯、投光灯、控制系统或官网具体系列。若正文不支持，不要臆造。
4. 项目案例只收录正文明确出现的真实项目；建筑师、照明设计师、年份和产品缺失时填 null。
5. 新闻必须是具体文章或公告，并且能从正文提取中文摘要或明确发布日期；不能只复制候选标题。Press、News、Seminars and events、Subscribe、Newsletter 等栏目入口或订阅入口不算新闻。
6. downloads 和 news 的 URL 必须来自候选；projects、insights 和 evidence 的 source_url 必须来自所提供页面的 URL。
7. evidence.snippet 必须复制来源页面中的短句原文（最多 300 字符），不能把模型总结伪装成引用。
8. insights 应提炼“为什么值得关注”，但每条都必须有来源支撑，不得进行无证据的市场份额、性能或质量判断。
9. 标签要具体、可检索、使用中文；避免“优秀、领先、创新”等空泛标签。
10. 控制输出规模：顶层产品线最多15项、每项children最多5项、项目最多8项、洞察最多8项、证据最多20项、新闻最多8项、下载最多20项。优先质量和具体性，不要重复。
11. 严格输出与给定 JSON 结构一致的合法 JSON，不要输出 markdown 或额外说明。"""


def build_user_prompt(
    site_text: str, download_candidates: list[dict], news_candidates: list[dict]
) -> str:
    def fmt(items: list[dict], keys: list[str]) -> str:
        lines = []
        for it in items[:80]:
            parts = [f"{k}={it.get(k)}" for k in keys if it.get(k)]
            lines.append("- " + "; ".join(parts))
        return "\n".join(lines) if lines else "（无）"

    dl = fmt(download_candidates, ["title", "url", "resource_type", "file_ext"])
    nw = fmt(news_candidates, ["title", "url"])
    return f"""请按下面的 JSON 结构提取信息：
{EXTRACTION_SCHEMA_HINT}

====== 已抓取页面正文（每段都标有来源 URL） ======
{site_text}

====== 可下载链接候选（URL 必须从这里选） ======
{dl}

====== 新闻文章候选（URL 必须从这里选） ======
{nw}

质量要求：优先输出具体产品系列、项目案例、技术特点、可下载资料和有证据的关键洞察；若只有公司宣传语，不要扩写成空泛结论。
现在只输出合法 JSON。"""
