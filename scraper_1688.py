#!/usr/bin/env python3
"""
1688.com Supplier Scraper  (需要中国 IP 或 VPN 中国节点)
用法: python scraper_1688.py
输出: results/1688_YYYY-MM-DD.json
"""

import asyncio, json, re, sys, time, logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "scraper_1688.log", encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)),
    ],
)
log = logging.getLogger(__name__)

# ─── 产品配置 ──────────────────────────────────────────────────────────────
PRODUCTS = {
    "claw_hammer": {
        "name_cn": "羊角榔头（带吸铁石）",
        "keywords": ["带磁羊角锤", "磁铁羊角锤", "带吸铁石锤子"],
        "price_min": 5,   # RMB 合理最低价
        "price_max": 150, # RMB 合理最高价
        # 加分关键词
        "bonus_kw": ["带磁", "磁铁", "吸铁石", "吸钉", "合金钢", "锻造", "玻璃纤维"],
        # 扣分关键词（不相关）
        "penalty_kw": ["橡皮锤", "铜锤", "尼龙锤", "塑料"],
        # 优质产地加分
        "good_regions": ["山东", "浙江", "河北", "江苏", "广东", "永康", "临沂"],
    },
    "caulking_gun": {
        "name_cn": "硅胶枪（打胶器）",
        "keywords": ["全钢硅胶枪 止流", "打胶器 防滴漏", "玻璃胶枪 钢架"],
        "price_min": 3,
        "price_max": 80,
        "bonus_kw": ["全钢", "钢架", "止流", "防滴漏", "泄压", "300ml", "310ml", "通用"],
        "penalty_kw": ["塑料枪", "双组份", "气动", "电动"],
        "good_regions": ["浙江", "江苏", "广东", "上海", "乐清", "温州", "宁波"],
    },
    "triangle_scraper": {
        "name_cn": "三角刮刀",
        "keywords": ["三角刮刀 SK5", "三角刮刀 高碳钢", "刮胶刀 三角形"],
        "price_min": 1,
        "price_max": 50,
        "bonus_kw": ["SK5", "SK2", "65Mn", "高碳钢", "锰钢", "弹簧钢", "橡胶柄", "防滑", "TPR"],
        "penalty_kw": ["塑料刀", "美工刀", "剪刀"],
        "good_regions": ["浙江", "江苏", "广东", "河北", "义乌", "宁波", "温州"],
    },
}

# ─── Playwright 初始化 ────────────────────────────────────────────────────
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
window.chrome = {runtime: {}};
"""

async def make_context(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    ctx = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="zh-CN",
        viewport={"width": 1366, "height": 768},
        extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
    )
    await ctx.add_init_script(STEALTH_SCRIPT)
    return browser, ctx

# ─── 页面解析 ─────────────────────────────────────────────────────────────
async def parse_offer_cards(page) -> list[dict]:
    """从搜索结果页提取商品/商家卡片。"""
    items = []
    try:
        # 等待产品列表加载
        await page.wait_for_selector(
            ".offer-list-row, .sm-offer-list, [class*='offer'], [data-offer-id]",
            timeout=12000
        )
    except PWTimeout:
        log.warning("等待产品列表超时")
        return items

    # 提取所有卡片数据（JS 执行效率最高）
    raw = await page.evaluate("""() => {
        const results = [];
        // 尝试多种 selector 兼容不同版本的 1688 页面
        const selectors = [
            '.offer-list-row .offer-list-item',
            '.sm-offer-list .sm-offer-item',
            '[data-offer-id]',
            '.J_offerItem',
        ];
        let cards = [];
        for (const sel of selectors) {
            cards = document.querySelectorAll(sel);
            if (cards.length > 0) break;
        }

        cards.forEach(card => {
            try {
                // 商品名
                const titleEl = card.querySelector(
                    '.title, .sm-offer-title, [class*="title"], h4, h3'
                );
                // 价格
                const priceEl = card.querySelector(
                    '.price, .sm-offer-price, [class*="price"] b, [class*="price"] em'
                );
                // 成交量（销量）
                const saleEl = card.querySelector(
                    '.sale-num, .sm-offer-counter-trader, [class*="sale"], [class*="trade"]'
                );
                // 商家名
                const companyEl = card.querySelector(
                    '.company-name, .sm-company-name, [class*="company"]'
                );
                // 发货地
                const locEl = card.querySelector(
                    '.location, .sm-company-location, [class*="location"]'
                );
                // 认证标签
                const authEls = card.querySelectorAll(
                    '.auth-tag, [class*="auth"], [class*="badge"], [class*="tag"]'
                );
                // 链接
                const linkEl = card.querySelector('a[href*="1688.com"], a[href*="detail"]');

                const title   = titleEl   ? titleEl.innerText.trim()   : '';
                const price   = priceEl   ? priceEl.innerText.trim()   : '';
                const sales   = saleEl    ? saleEl.innerText.trim()    : '';
                const company = companyEl ? companyEl.innerText.trim() : '';
                const loc     = locEl     ? locEl.innerText.trim()     : '';
                const href    = linkEl    ? linkEl.href                : '';
                const tags    = [...authEls].map(el => el.innerText.trim()).filter(Boolean).join(' ');
                const fullText = card.innerText;

                if (title || company) {
                    results.push({ title, price, sales, company, location: loc, url: href, tags, fullText });
                }
            } catch(e) {}
        });
        return results;
    }""")

    items = raw if isinstance(raw, list) else []
    return items

# ─── 评分 ─────────────────────────────────────────────────────────────────
def _parse_price(price_str: str) -> float:
    nums = re.findall(r"[\d.]+", price_str.replace(",", ""))
    return float(nums[0]) if nums else 0.0

def _parse_sales(sales_str: str) -> int:
    nums = re.findall(r"\d+", sales_str.replace(",", ""))
    val  = int(nums[0]) if nums else 0
    if "万" in sales_str:
        val *= 10000
    return val

def score_item(item: dict, product_key: str) -> dict:
    cfg    = PRODUCTS[product_key]
    text   = (item.get("title","") + " " + item.get("fullText","")).lower()
    score  = 0
    detail = {}

    # 1) 成交量（满 40 分）
    sales = _parse_sales(item.get("sales",""))
    if   sales >= 10000: sv = 40
    elif sales >= 5000:  sv = 34
    elif sales >= 1000:  sv = 26
    elif sales >= 500:   sv = 20
    elif sales >= 100:   sv = 14
    elif sales >= 10:    sv = 8
    else:                sv = 2
    score += sv
    detail["成交量"] = f"{sv}/40 ({sales}笔)"

    # 2) 关键词匹配（满 30 分）
    bonus_hit   = [kw for kw in cfg["bonus_kw"]   if kw.lower() in text]
    penalty_hit = [kw for kw in cfg.get("penalty_kw",[]) if kw.lower() in text]
    kw_score = min(len(bonus_hit) * 6, 30) - len(penalty_hit) * 8
    kw_score = max(kw_score, 0)
    score += kw_score
    detail["关键词"] = f"{kw_score}/30 (匹配:{','.join(bonus_hit) or '无'})"

    # 3) 价格合理性（满 15 分）
    price_val = _parse_price(item.get("price",""))
    if price_val > 0:
        if cfg["price_min"] <= price_val <= cfg["price_max"]:
            ps = 15
        elif price_val < cfg["price_min"]:
            ps = 5   # 太便宜可能品质差
        else:
            ps = 8   # 偏贵但可接受
    else:
        ps = 0
    score += ps
    detail["价格"] = f"{ps}/15 (¥{price_val:.1f})"

    # 4) 产地（满 10 分）
    loc = item.get("location","")
    loc_score = 10 if any(r in loc for r in cfg["good_regions"]) else 4
    score += loc_score
    detail["产地"] = f"{loc_score}/10 ({loc or '未知'})"

    # 5) 认证标签（满 5 分）
    tags = item.get("tags","")
    auth_score = 5 if tags else 0
    score += auth_score
    detail["认证"] = f"{auth_score}/5"

    item["score"]   = min(score, 100)
    item["detail"]  = detail
    item["sales_n"] = sales
    item["price_n"] = price_val
    return item

# ─── 搜索一个关键词 ───────────────────────────────────────────────────────
async def search_keyword(ctx, keyword: str) -> list[dict]:
    page = await ctx.new_page()
    results = []
    try:
        from urllib.parse import quote
        url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={quote(keyword)}&n=y"
        log.info(f"  搜索: {keyword}")
        await page.goto(url, wait_until="networkidle", timeout=25000)
        await page.wait_for_timeout(3000)

        if "captcha" in (await page.content()).lower():
            log.warning(f"  遇到验证码，跳过: {keyword}")
        else:
            items = await parse_offer_cards(page)
            log.info(f"  → {len(items)} 条结果")
            results = items
    except Exception as e:
        log.warning(f"  搜索失败 '{keyword}': {e}")
    finally:
        await page.close()
    return results

# ─── 主流程 ──────────────────────────────────────────────────────────────
async def run():
    log.info("=" * 60)
    log.info(f"1688 Scraper 启动  {datetime.now():%Y-%m-%d %H:%M}")

    all_results = {}

    async with async_playwright() as pw:
        # 先访问首页建立 session
        browser, ctx = await make_context(pw)
        log.info("预热: 访问 1688 首页...")
        page0 = await ctx.new_page()
        await page0.goto("https://www.1688.com", timeout=20000)
        await page0.wait_for_timeout(3000)
        await page0.close()

        for product_key, cfg in PRODUCTS.items():
            log.info(f"\n── {cfg['name_cn']} ──")
            raw_items: list[dict] = []

            for kw in cfg["keywords"]:
                items = await search_keyword(ctx, kw)
                raw_items.extend(items)
                await asyncio.sleep(2)  # 礼貌延迟

            log.info(f"原始数据: {len(raw_items)} 条")

            # 评分
            for item in raw_items:
                score_item(item, product_key)

            # 去重（按商家名）
            seen, unique = {}, []
            for item in raw_items:
                key = re.sub(r"\s+", "", item.get("company","")).lower()[:20] or item.get("title","")[:20]
                if key and (key not in seen or item["score"] > seen[key]["score"]):
                    seen[key] = item
            # 主排序：成交量，次排序：综合评分
            unique = sorted(seen.values(), key=lambda x: (x["sales_n"], x["score"]), reverse=True)[:20]

            log.info(f"去重排名后: {len(unique)} 家")
            all_results[product_key] = unique

        await browser.close()

    # 保存 JSON
    today = datetime.now().strftime("%Y-%m-%d")
    out   = RESULTS_DIR / f"1688_{today}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    log.info(f"\nJSON 存档: {out}")
    log.info("完成 ✓")
    return all_results


if __name__ == "__main__":
    asyncio.run(run())
