#!/usr/bin/env python3
"""
1688 Domestic Supplier Guide - Flask Web App
国内采购导航工具（1688.com / 人民币结算）
"""
import os, json, subprocess, sys
from pathlib import Path
from flask import Flask, render_template, jsonify

app = Flask(__name__)
BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

PRODUCTS = [
    {
        "key": "claw_hammer",
        "icon": "🔨",
        "name_cn": "羊角榔头（带吸铁石）",
        "name_en": "Magnetic Claw Hammer",
        "color": "#1d4ed8",
        "price_range": "¥18 – ¥75 / 把",
        "moq": "通常 10–50 把起批",
        "note": "重点确认：锤头是否带磁铁/吸铁石、锤头材质（锻造合金钢优先）、手柄类型",
        "links": [
            {
                "label": "🔍 带磁羊角锤 · 批发搜索",
                "url": "https://s.1688.com/kq/-B4F8B4C5D1F2BDC7B4B8.html",
                "type": "primary",
                "desc": "1688 主搜索页，可按销量/价格/信用筛选"
            },
            {
                "label": "📊 羊角锤 · 市场行情",
                "url": "https://www.1688.com/market/-D1F2BDC7B4B8.html",
                "type": "secondary",
                "desc": "实时行情、价格趋势、热销款式对比"
            },
            {
                "label": "💰 带磁羊角锤 · 报价大全",
                "url": "https://m.1688.com/jiage/-B4F8B4C5D1F2BDC7B4B8.html",
                "type": "secondary",
                "desc": "各规格最新批发报价汇总"
            },
            {
                "label": "🏭 五金工具厂家频道",
                "url": "https://industry.1688.com/wjgj/index.html",
                "type": "tertiary",
                "desc": "按品类浏览五金工具生产厂家"
            },
        ],
        "keywords": [
            "带磁羊角锤 厂家",
            "磁铁起钉锤 批发",
            "V型羊角锤 带磁铁",
            "合金钢羊角锤 玻璃纤维柄",
            "16oz羊角锤 带吸铁石",
        ],
        "specs": [
            {"label": "锤头材质", "value": "锻造合金钢 / 45#钢，硬度 HRC 42–52", "key": True},
            {"label": "磁铁功能", "value": "锤头端面嵌入磁铁，可吸附钉子单手操作", "key": True},
            {"label": "手柄材质", "value": "玻璃纤维柄 > 橡胶包覆钢柄 > 木柄", "key": False},
            {"label": "常见规格", "value": "8oz(230g) / 16oz(450g) / 20oz(560g)", "key": False},
            {"label": "羊角设计", "value": "V型开口，起钉省力，建议开口宽度 ≥12mm", "key": False},
        ],
        "tips": [
            "索要样品测试磁力强度，吸住普通钉子不脱落即合格",
            "确认锤头与柄的连接方式（楔形铆接 > 螺栓连接）",
            "规避镀铬外观件冒充锻造钢，可让厂家出材质报告",
            "询问是否可 OEM 打 Logo（通常 500 把以上可谈）",
        ],
    },
    {
        "key": "caulking_gun",
        "icon": "🔫",
        "name_cn": "硅胶枪（打胶器）",
        "name_en": "Caulking / Silicone Gun",
        "color": "#059669",
        "price_range": "¥8 – ¥35 / 把",
        "moq": "通常 50–200 把起批",
        "note": "重点确认：枪架是否全钢、有无止流/防滴漏机构、适配管径（300ml 标准管）",
        "links": [
            {
                "label": "🔍 硅胶枪 · 批发搜索",
                "url": "https://s.1688.com/kq/-B9E8BDBAC7B9.html",
                "type": "primary",
                "desc": "1688 主搜索页，22,000+ 供应商"
            },
            {
                "label": "🔍 打胶器 · 批发搜索",
                "url": "https://s.1688.com/kq/-B4F2BDBACEEDAl.html",
                "type": "primary",
                "desc": "「打胶器」关键词，更多厂家直供结果"
            },
            {
                "label": "📊 硅胶枪 · 市场行情",
                "url": "https://www.1688.com/market/-B9E8BDBAC7B9.html",
                "type": "secondary",
                "desc": "市场价格走势与热销款对比"
            },
            {
                "label": "💰 打胶器 · 报价大全",
                "url": "https://s.1688.com/kq/-B9E3D6DDBBAFD7B1C6B7C5E7CEEDC6BFC9FAB2FAB3A7BCD2.html",
                "type": "secondary",
                "desc": "含止流功能款式报价汇总"
            },
        ],
        "keywords": [
            "全钢硅胶枪 止流 批发",
            "打胶器 300ml 防滴漏 厂家",
            "玻璃胶枪 钢架 厂家直销",
            "硅胶枪 300/310ml 通用型",
            "打胶枪 自动止流 批发",
        ],
        "specs": [
            {"label": "枪架材质", "value": "全钢冲压架（不接受塑料架）", "key": True},
            {"label": "止流机构", "value": "推杆带回弹片，松手自动泄压防滴漏", "key": True},
            {"label": "适配规格", "value": "300ml / 310ml 标准圆管，通用型优先", "key": True},
            {"label": "推杆设计", "value": "带齿推杆防滑，行程顺滑无卡顿", "key": False},
            {"label": "枪嘴角度", "value": "可旋转枪嘴方便角落打胶", "key": False},
        ],
        "tips": [
            "要求厂家实拍止流演示视频，辨别是否真有回弹泄压功能",
            "测试枪架承重：装满 300ml 管单手握持无形变",
            "询问是否备货「骨架型」（镂空骨架轻便）和「全封闭型」两款",
            "问清楚标准包装（散装/挂卡/彩盒）及每款最低起订量",
        ],
    },
    {
        "key": "triangle_scraper",
        "icon": "🔧",
        "name_cn": "三角刮刀",
        "name_en": "Triangle Scraper",
        "color": "#7c3aed",
        "price_range": "¥3 – ¥28 / 把",
        "moq": "通常 100–500 把起批",
        "note": "重点确认：刀片材质（SK5/65Mn高碳钢）、手柄防滑性、是否适合刮硅胶/腻子",
        "links": [
            {
                "label": "🔍 三角刮刀 · 批发搜索",
                "url": "https://www.1688.com/chanpin/-C8FDBDC7B9CEB5B6.html",
                "type": "primary",
                "desc": "1688 产品频道，含厂家联系方式"
            },
            {
                "label": "📊 三角刮刀 · 市场行情",
                "url": "https://www.1688.com/market/-C8FDBDC7B9CEB5B6.html",
                "type": "secondary",
                "desc": "行情价格、热销款式排行"
            },
            {
                "label": "💰 三角刮刀 · 报价大全",
                "url": "https://www.1688.com/jiage/-B9CEB5B6.html",
                "type": "secondary",
                "desc": "各规格批发报价汇总"
            },
            {
                "label": "🔍 SK5刀片 · 厂家搜索",
                "url": "https://www.1688.com/brand/-736B35B5B6C6AC.html",
                "type": "tertiary",
                "desc": "专门搜索 SK5 材质刮刀品牌"
            },
        ],
        "keywords": [
            "三角刮刀 SK5 厂家",
            "三角刮刀 硅胶刮 批发",
            "三角刮刀 65Mn 高碳钢",
            "腻子刮刀 三角 TPR手柄",
            "三角刮刀 多功能 开缝",
        ],
        "specs": [
            {"label": "刀片材质", "value": "SK5 / 65Mn 高碳钢，硬度 HRC 58–62", "key": True},
            {"label": "手柄材质", "value": "橡胶/TPR 双色防滑柄（不要纯 PP 硬柄）", "key": True},
            {"label": "刀片厚度", "value": "0.8–1.2mm（太薄易断，太厚刮不入缝）", "key": False},
            {"label": "刀片数量", "value": "单片固定式 / 可换刀片式（可换更耐用）", "key": False},
            {"label": "适用场景", "value": "刮旧硅胶 / 刮腻子 / 开胶缝 / 去漆面", "key": False},
        ],
        "tips": [
            "要求厂家提供刀片硬度检测报告（确认 SK5 非普钢冒充）",
            "样品测试：用刀片刮瓷砖缝隙旧硅胶，看是否弯折/崩口",
            "询问是否有可替换刀片款（零售更好卖）",
            "了解包装选项：散装/挂卡/礼盒，针对不同渠道",
        ],
    },
]

PRODUCT_MAP = {p["key"]: p for p in PRODUCTS}


def load_latest_results() -> dict:
    """Load the most recent 1688_*.json from results/. Returns {} if none found."""
    files = sorted(RESULTS_DIR.glob("1688_*.json"), reverse=True)
    if not files:
        return {}
    try:
        with open(files[0], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@app.route("/")
def index():
    ranked = load_latest_results()
    # Attach ranked supplier list to each product
    for p in PRODUCTS:
        p["suppliers"] = ranked.get(p["key"], [])
    return render_template("index.html", products=PRODUCTS)


@app.route("/api/run", methods=["POST"])
def api_run():
    """Trigger scraper_1688.py as a subprocess (requires Chinese IP)."""
    scraper = BASE_DIR / "scraper_1688.py"
    if not scraper.exists():
        return jsonify({"ok": False, "msg": "scraper_1688.py not found"}), 404
    try:
        proc = subprocess.Popen(
            [sys.executable, str(scraper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out, _ = proc.communicate(timeout=300)
        return jsonify({"ok": proc.returncode == 0, "log": out[-4000:]})
    except subprocess.TimeoutExpired:
        proc.kill()
        return jsonify({"ok": False, "msg": "超时（5分钟）"}), 504
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/results")
def api_results():
    return jsonify(load_latest_results())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting... http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
