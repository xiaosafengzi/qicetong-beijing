"""Build transparent demo data; all company records are synthetic, all policy links are official."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

SOURCES = [
    {"id": "bj-sme-2026", "title": "关于组织开展北京市2026年度科技型中小企业评价工作的通知", "url": "https://kw.beijing.gov.cn/zwgk/zcwj/202606/t20260608_4690659.html", "published": "2026-06-08", "authority": "北京市科委、中关村管委会"},
    {"id": "bj-sme-2025", "title": "关于组织开展北京市2025年度科技型中小企业评价工作的通知", "url": "https://kw.beijing.gov.cn/zwgk/zwgksbrl/202506/t20250627_4129544.html", "published": "2025-06-27", "authority": "北京市科委、中关村管委会"},
    {"id": "national-sme", "title": "科技型中小企业评价办法（国科发政〔2017〕115号）", "url": "https://most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/gfxwj2017/201705/t20170510_132709.html", "published": "2017-05-03", "authority": "科技部、财政部、国家税务总局"},
    {"id": "bj-hnte-2026", "title": "关于启动2026年度北京市高新技术企业认定管理工作的通知", "url": "https://kw.beijing.gov.cn/zwgk/zcwj/202604/t20260428_4620918.html", "published": "2026-04-28", "authority": "北京市科委、中关村管委会等"},
    {"id": "national-hnte", "title": "高新技术企业认定管理办法（国科发火〔2016〕32号）", "url": "https://www.beijing.gov.cn/zhengce/zhengcefagui/202202/t20220222_2614690.html", "published": "2016-01-29", "authority": "科技部、财政部、国家税务总局；北京市政府转载"},
]
source_by_id = {x["id"]: x for x in SOURCES}


def rule(rid, title, fields, op, source, clause, quote, **extra):
    return {"id": rid, "title": title, "fields": fields, "op": op,
            "source": source_by_id[source], "clause": clause, "quote": quote, **extra}


def sme(year):
    prev = year - 1
    return {
        "id": f"sme-bj-{year}", "family": "sme", "name": "科技型中小企业评价", "region": "北京市",
        "year": year, "version": f"北京申报季 {year}", "state": "current" if year == 2026 else "historical",
        "description": "规模条件、创新积分与直通车条件预核查",
        "published": "2026-06-08" if year == 2026 else "2025-06-27",
        "start": f"{year}-06-01" if year == 2026 else f"{year}-06-30",
        "deadlines": [f"{year}-08-31" if year == 2026 else f"{year}-09-30"],
        "source": source_by_id[f"bj-sme-{year}"],
        "scope_note": "实现基础规模、属地和第七/八条评分路径；会计核算、行业分类、信用核查、现场核验及材料真实性仍需业务复核。",
        "manual_checks": ["核实会计核算、查账征收与研发费用归集口径", "核实行业分类、信用及现场核查要求", "由主管部门核验真实性并完成公示入库"],
        "rules": [
            rule("region", "北京属地", ["city"], "eq", f"bj-sme-{year}", "通知适用范围", "北京市科技型中小企业评价工作", expected="北京市"),
            rule("resident", "居民企业身份", ["resident_enterprise"], "eq", "national-sme", "第六条（一）", "在中国境内（不包括港、澳、台地区）注册的居民企业。", expected=True),
            rule("staff", "职工总数不超过 500 人", ["employees"], "lte", "national-sme", "第六条（二）", "职工总数不超过500人、年销售收入不超过2亿元、资产总额不超过2亿元。", threshold=500, unit="人", period=str(prev)),
            rule("sales", "年销售收入不超过 2 亿元", [f"sales_{prev}"], "lte", "national-sme", "第六条（二）", "年销售收入不超过2亿元。", threshold=20000, unit="万元", period=str(prev)),
            rule("assets", "资产总额不超过 2 亿元", [f"assets_{prev}"], "lte", "national-sme", "第六条（二）", "资产总额不超过2亿元。", threshold=20000, unit="万元", period=str(prev)),
            rule("industry", "产品服务行业范围", ["allowed_industry"], "eq", "national-sme", "第六条（三）", "企业提供的产品和服务不属于国家规定的禁止、限制和淘汰类。", expected=True),
            rule("integrity", "上一年度及当年信用与事故条件", ["sme_compliance"], "eq", "national-sme", "第六条（四）", "企业在填报上一年及当年内未发生重大安全、重大质量事故和严重环境违法、科研严重失信行为，且企业未列入经营异常名录和严重违法失信企业名单。", expected=True, period=f"{prev}-{year}"),
            rule("innovation", "创新积分或有效直通车条件", ["employees", "tech_staff", f"rd_{prev}", f"sales_{prev}", f"cost_{prev}", "ip_class1", "ip_class2", "fast_track"], "sme_score", "national-sme", "第六条（五）、第七条、第八条", "综合评价所得分值不低于60分，且科技人员指标得分不得为0分。符合第六条（一）至（四）且满足第八条条件的企业可直接确认。", period=str(prev)),
        ],
    }


hnte = {
    "id": "hnte-bj-2026", "family": "hnte", "name": "高新技术企业认定", "region": "北京市",
    "year": 2026, "version": "北京申报季 2026", "state": "current",
    "description": "人员、研发投入与高新收入的跨年度证据核验",
    "published": "2026-04-28", "start": "2026-04-28", "deadlines": ["2026-05-15", "2026-07-17", "2026-09-24"],
    "source": source_by_id["bj-hnte-2026"],
    "scope_note": "第一版支持完整三个会计年度的数量指标。经营期不足三年转人工；创新能力评分、知识产权核心关联和领域判断不由程序代替专家认定。",
    "manual_checks": ["专家评价创新能力及知识产权对主要产品的核心支持作用", "核验高新技术领域归属、专项审计及告知承诺材料", "核实经营期不足三年、新成立企业和重新认定等特殊情况"],
    "rules": [
        rule("region", "北京属地", ["city"], "eq", "bj-hnte-2026", "二、申报企业范围", "在本市行政区域内注册的居民企业，且符合《认定办法》第十一条有关规定。", expected="北京市"),
        rule("resident", "居民企业身份", ["resident_enterprise"], "eq", "bj-hnte-2026", "二、申报企业范围", "在本市行政区域内注册的居民企业。", expected=True),
        rule("age", "注册成立满一年", ["registration_date"], "age", "national-hnte", "第十一条（一）", "企业申请认定时须注册成立一年以上。"),
        rule("ip", "核心知识产权所有权", ["core_ip"], "eq", "national-hnte", "第十一条（二）", "获得对其主要产品（服务）在技术上发挥核心支持作用的知识产权的所有权。", expected=True),
        rule("domain", "高新技术领域归属", ["supported_domain"], "eq", "national-hnte", "第十一条（三）", "发挥核心支持作用的技术属于《国家重点支持的高新技术领域》规定的范围。", expected=True),
        rule("staff_ratio", "科技人员比例不低于 10%", ["tech_staff", "employees"], "ratio", "national-hnte", "第十一条（四）", "科技人员占企业当年职工总数的比例不低于10%。", threshold=0.1, period="2025", unit="人"),
        rule("rd_ratio", "近三年研发费用比例", ["sales_2023", "sales_2024", "sales_2025", "rd_2023", "rd_2024", "rd_2025", "registration_date"], "rd_ratio", "national-hnte", "第十一条（五）", "近三个会计年度的研发费用总额占同期销售收入总额的比例：最近一年销售收入5000万元（含）以下不低于5%；5000万元至2亿元（含）不低于4%；2亿元以上不低于3%。", unit="万元"),
        rule("domestic", "境内研发费用比例不低于 60%", ["domestic_rd_2023", "domestic_rd_2024", "domestic_rd_2025", "rd_2023", "rd_2024", "rd_2025", "registration_date"], "domestic_ratio", "national-hnte", "第十一条（五）", "企业在中国境内发生的研究开发费用总额占全部研究开发费用总额的比例不低于60%。", unit="万元"),
        rule("hightech", "高新收入比例不低于 60%", ["hightech_income_2025", "total_income_2025"], "ratio", "national-hnte", "第十一条（六）", "近一年高新技术产品（服务）收入占企业同期总收入的比例不低于60%。", threshold=0.6, period="2025", unit="万元"),
        rule("integrity", "申请前一年重大事故条件", ["hnte_compliance"], "eq", "national-hnte", "第十一条（八）", "企业申请认定前一年内未发生重大安全、重大质量事故或严重环境违法行为。", expected=True, period="申请前一年"),
    ],
}


def company(cid, name, note):
    facts = {}
    evidence = []

    def add(key, value, unit="", period="", document="企业资料", status="confirmed"):
        eid = f"{cid}-{key}"
        label = f"{key}：{value} {unit}；所属期间：{period or '基本信息'}"
        evidence.append({"id": eid, "title": f"{document}（模拟）", "locator": f"字段 {key}", "text": f"仅用于系统演示的虚构企业材料。\n{label}"})
        facts[key] = {"value": value, "unit": unit, "period": period, "status": status, "evidence": [eid]}

    for key, value in {"city": "北京市", "resident_enterprise": True, "registration_date": "2020-03-12", "allowed_industry": True, "core_ip": True, "supported_domain": True}.items():
        add(key, value)
    for key, value in {"employees": 80, "tech_staff": 24, "ip_class1": 2, "ip_class2": 3}.items():
        add(key, value, "人" if key in ("employees", "tech_staff") else "项", "2025", "人员与知识产权台账")
    add("fast_track", False, period="2026", document="直通车资质核验")
    add("sme_compliance", True, period="2025-2026", document="信用与事故核查说明")
    add("hnte_compliance", True, period="申请前一年", document="信用与事故核查说明")
    for year, sales, rd in [(2023, 2400, 150), (2024, 3200, 220), (2025, 4200, 300)]:
        for key, value in {"sales": sales, "rd": rd, "domestic_rd": rd * 0.9, "assets": sales * 1.5, "cost": sales * 0.8, "total_income": sales + 200, "hightech_income": sales * 0.82}.items():
            add(f"{key}_{year}", round(value, 2), "万元", str(year), f"{year}年度财务数据表")
    return {"id": cid, "name": name, "district": "海淀区", "industry": "软件和信息技术服务业", "is_demo": True, "note": note, "facts": facts, "evidence": evidence}


def change(c, key, value=None, status=None):
    if value is not None:
        c["facts"][key]["value"] = value
        for e in c["evidence"]:
            if e["id"] in c["facts"][key]["evidence"]:
                e["text"] = f"仅用于系统演示的虚构企业材料。\n{key}：{value} {c['facts'][key]['unit']}；所属期间：{c['facts'][key]['period']}"
    if status:
        c["facts"][key]["status"] = status


companies = [company("demo-01", "北京星河智研科技有限公司（模拟）", "完整材料样例：用于展示数量指标、年度计算和证据链。"),
             company("demo-02", "北京青芽数据科技有限公司（模拟）", "材料缺失样例：2024年度研发费用待补充。"),
             company("demo-03", "北京远山制造有限公司（模拟）", "不满足样例：职工规模超过科技型中小企业上限。"),
             company("demo-04", "北京知微软件有限公司（模拟）", "证据冲突样例：人员数量在两份材料中不一致。"),
             company("demo-05", "北京初禾创新科技有限公司（模拟）", "新成立企业样例：高企注册年限不足。")]
companies[1]["facts"].pop("rd_2024")
companies[1]["evidence"] = [e for e in companies[1]["evidence"] if e["id"] != "demo-02-rd_2024"]
change(companies[2], "employees", 520)
change(companies[3], "employees", status="conflict")
companies[3]["evidence"].append({"id": "demo-04-staff-other", "title": "社保人员汇总（模拟）", "locator": "2025年度合计", "text": "虚构演示材料：全年平均职工数为90人；与另一份80人记录冲突。"})
companies[3]["facts"]["employees"]["evidence"].append("demo-04-staff-other")
change(companies[4], "registration_date", "2026-05-01")

for filename, obj in [("sources.json", SOURCES), ("policies.json", [sme(2026), hnte, sme(2025)]), ("companies.json", companies)]:
    (OUT / filename).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# A self-contained import template for the UI; users replace values and evidence with their own materials.
(OUT / "company-template.json").write_text(json.dumps(companies[0], ensure_ascii=False, indent=2), encoding="utf-8")
print("Generated 3 policy snapshots and 5 explicitly synthetic companies.")
