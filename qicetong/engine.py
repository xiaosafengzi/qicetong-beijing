"""Deterministic, evidence-aware checks. No LLM is allowed to replace numeric rules."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from .models import Company

LABELS = {
    "city": "注册地", "resident_enterprise": "居民企业身份", "registration_date": "注册日期",
    "employees": "职工总数", "tech_staff": "科技人员数", "allowed_industry": "行业范围核查",
    "core_ip": "核心知识产权所有权", "supported_domain": "高新技术领域归属",
    "sme_compliance": "科技型中小企业信用与事故核查", "hnte_compliance": "高企事故核查",
    "ip_class1": "有效且相关的Ⅰ类知识产权数", "ip_class2": "有效且相关的Ⅱ类知识产权数",
    "fast_track": "有效直通车资格", "sales": "销售收入", "rd": "研发费用",
    "domestic_rd": "境内研发费用", "assets": "资产总额", "cost": "成本费用",
    "total_income": "总收入", "hightech_income": "高新产品（服务）收入",
}
STATUS_LABELS = {"pass": "已核对条件满足", "fail": "存在不满足项", "unknown": "待补证或复核", "conflict": "材料存在冲突"}


def field_label(key: str) -> str:
    parts = key.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
        return f"{parts[1]}年{LABELS.get(parts[0], parts[0])}"
    return LABELS.get(key, key)


class NeedsReview(Exception):
    def __init__(self, message: str, fields: list[str], status="unknown"):
        self.fields = fields
        self.status = status
        super().__init__(message)


class Facts:
    def __init__(self, company: Company):
        self.company = company
        self.used: list[str] = []

    def read(self, key: str, period: str = ""):
        if key not in self.used:
            self.used.append(key)
        fact = self.company.facts.get(key)
        if not fact or fact.value is None:
            raise NeedsReview(f"缺少{field_label(key)}", [key])
        if fact.status == "conflict":
            raise NeedsReview(f"{field_label(key)}的材料记录相互冲突", [key], "conflict")
        if fact.status != "confirmed":
            raise NeedsReview(f"{field_label(key)}尚未人工核对", [key])
        if period and fact.period != period:
            raise NeedsReview(f"{field_label(key)}需要 {period} 期间数据，当前标记为 {fact.period or '未标注'}", [key])
        return fact.value

    def number(self, key: str, unit="", period="") -> Decimal:
        value = self.read(key, period)
        if isinstance(value, bool):
            raise NeedsReview(f"{field_label(key)}需要数值，不能使用布尔值", [key])
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise NeedsReview(f"{field_label(key)}不是有效数值", [key]) from None
        if not number.is_finite() or number < 0:
            raise NeedsReview(f"{field_label(key)}必须是非负有限数值", [key])
        original_unit = self.company.facts[key].unit
        if unit and original_unit != unit:
            if unit == "万元" and original_unit in ("元", "亿元"):
                number *= Decimal("0.0001") if original_unit == "元" else Decimal(10000)
            else:
                raise NeedsReview(f"{field_label(key)}单位应为{unit}，当前为{original_unit or '未标注'}", [key])
        if unit in ("人", "项") and number != number.to_integral_value():
            raise NeedsReview(f"{field_label(key)}应填写整数", [key])
        return number


def division(numerator: Decimal, denominator: Decimal, fields: list[str]) -> Decimal:
    if denominator <= 0:
        raise NeedsReview("分母必须大于零，不能推断比例", fields)
    return numerator / denominator


def bucket(value: Decimal, thresholds: list[tuple[str, int]]) -> int:
    return next((score for threshold, score in thresholds if value >= Decimal(threshold)), 0)


def evaluate_rule(rule: dict, facts: Facts, as_of: date, policy: dict) -> tuple[bool, str, dict]:
    keys, op = rule["fields"], rule["op"]
    period = rule.get("period", "")
    if op == "eq":
        value = facts.read(keys[0], period)
        expected = rule["expected"]
        if isinstance(expected, bool) and type(value) is not bool:
            raise NeedsReview("请确认材料后填写 true/false，不接受文字或数字代替布尔判断", keys)
        return value == expected, f"核对值：{value}；要求：{expected}", {}
    if op == "lte":
        value = facts.number(keys[0], rule["unit"], period)
        within_limit = value <= Decimal(str(rule["threshold"]))
        relation = "≤" if within_limit else ">"
        return within_limit, f"{value:g} {rule['unit']} {relation} {rule['threshold']} {rule['unit']}", {"value": float(value), "threshold": rule["threshold"]}
    if op == "age":
        try:
            registered = date.fromisoformat(str(facts.read(keys[0])))
        except ValueError:
            raise NeedsReview("注册日期格式必须为 YYYY-MM-DD", keys) from None
        days = (as_of - registered).days
        return days >= 365, f"截至 {as_of}，注册 {days} 天；按满 365 天预核查", {"days": days}
    if op == "ratio":
        numerator = facts.number(keys[0], rule["unit"], period)
        denominator = facts.number(keys[1], rule["unit"], period)
        ratio = division(numerator, denominator, keys)
        if numerator > denominator:
            raise NeedsReview("分子超过同口径总量，请核对材料", keys, "conflict")
        return ratio >= Decimal(str(rule["threshold"])), f"{numerator:g} ÷ {denominator:g} = {ratio:.2%}；要求 ≥ {rule['threshold']:.0%}", {"ratio": float(ratio)}
    if op in ("rd_ratio", "domestic_ratio"):
        try:
            registered = date.fromisoformat(str(facts.read("registration_date")))
        except ValueError:
            raise NeedsReview("请核实注册日期", ["registration_date"]) from None
        if registered.year > policy["year"] - 3:
            raise NeedsReview("实际经营期不足三个会计年度，需按实际经营时间人工复核；未按缺失年度补零", keys)
        years = range(policy["year"] - 3, policy["year"])
        rd = [facts.number(f"rd_{y}", "万元", str(y)) for y in years]
        if op == "rd_ratio":
            sales = [facts.number(f"sales_{y}", "万元", str(y)) for y in years]
            ratio = division(sum(rd), sum(sales), keys)
            threshold = Decimal("0.05") if sales[-1] <= 5000 else Decimal("0.04") if sales[-1] <= 20000 else Decimal("0.03")
            return ratio >= threshold, f"三年合计 {sum(rd):g} ÷ {sum(sales):g} = {ratio:.2%}；最近一年销售 {sales[-1]:g} 万元，对应门槛 {threshold:.0%}", {"ratio": float(ratio), "threshold": float(threshold), "rd_total": float(sum(rd)), "sales_total": float(sum(sales))}
        domestic = [facts.number(f"domestic_rd_{y}", "万元", str(y)) for y in years]
        if any(a > b for a, b in zip(domestic, rd)):
            raise NeedsReview("某年度境内研发费用超过全部研发费用", keys, "conflict")
        ratio = division(sum(domestic), sum(rd), keys)
        return ratio >= Decimal("0.6"), f"三年境内研发 {sum(domestic):g} ÷ 全部研发 {sum(rd):g} = {ratio:.2%}；要求 ≥ 60%", {"ratio": float(ratio)}
    if op == "sme_score":
        fast = facts.company.facts.get("fast_track")
        if fast and fast.status == "confirmed" and fast.value is True and fast.period == str(policy["year"]):
            facts.read("fast_track", str(policy["year"]))
            return True, "材料已核对有效直通车资格；仍须满足其余基础条件", {"route": "fast_track"}
        staff = facts.number("employees", "人", period)
        tech = facts.number("tech_staff", "人", period)
        if tech > staff:
            raise NeedsReview("科技人员数超过职工总数", ["tech_staff", "employees"], "conflict")
        staff_score = bucket(division(tech, staff, ["employees"]), [(".30", 20), (".25", 16), (".20", 12), (".15", 8), (".10", 4)])
        rd = facts.number(f"rd_{period}", "万元", period)
        # Either R&D basis is permitted. A valid path can prove the threshold even when the other is missing.
        paths, issues = [], []
        for key, thresholds in [(f"sales_{period}", [(".06", 50), (".05", 40), (".04", 30), (".03", 20), (".02", 10)]),
                                (f"cost_{period}", [(".30", 50), (".25", 40), (".20", 30), (".15", 20), (".10", 10)])]:
            try:
                ratio = division(rd, facts.number(key, "万元", period), [key])
                paths.append((bucket(ratio, thresholds), key, ratio))
            except NeedsReview as exc:
                issues.append(exc)
        if not paths:
            raise issues[0]
        ip1 = facts.number("ip_class1", "项", period)
        if ip1 >= 1:
            ip_score = 30
        else:
            ip2 = facts.number("ip_class2", "项", period)
            ip_score = min(4, int(ip2)) * 6
        rd_score, basis, rd_ratio = max(paths)
        total = staff_score + rd_score + ip_score
        passed = total >= 60 and staff_score > 0
        if not passed and issues:
            raise NeedsReview("已知路径未达标，另一研发计分路径资料不全，不能直接判定不满足", [f"sales_{period}", f"cost_{period}"])
        if not passed and (not fast or fast.status != "confirmed" or fast.period != str(policy["year"])):
            raise NeedsReview("普通计分路径未达标，直通车资格尚未核清", ["fast_track"])
        message = f"人员 {staff_score} + 研发 {rd_score} + 成果 {ip_score} = {total} 分；采用{field_label(basis)}口径（{rd_ratio:.2%}）"
        return passed, message, {"route": "score", "score": total, "staff_score": staff_score, "rd_score": rd_score, "ip_score": ip_score, "basis": basis}
    raise ValueError(f"Unsupported rule operation: {op}")


def window_status(policy: dict, as_of: date) -> dict:
    if as_of < date.fromisoformat(policy["published"]):
        return {"status": "not_published", "label": "该版本尚未发布", "next_deadline": None}
    if as_of < date.fromisoformat(policy["start"]):
        return {"status": "not_open", "label": "尚未开放", "next_deadline": policy["deadlines"][0]}
    available = [d for d in policy["deadlines"] if date.fromisoformat(d) >= as_of]
    labels = policy.get("window_labels") or {}
    return {"status": "open" if available else "closed", "label": labels.get("open", "本批次可办理时间内") if available else labels.get("closed", "本年度填报已截止"), "next_deadline": available[0] if available else None,
            "deadlines": policy["deadlines"], "source": policy["source"], "note": "仅依据已收录通知；截止日具体时刻及区级受理安排须另行核实。"}


def quality_metrics(results: list[dict], manual_checks: list[str]) -> dict:
    """Compute auditable coverage metrics without changing any rule decision."""
    total = len(results)
    resolved = [item for item in results if item["status"] in ("pass", "fail")]
    evidence_backed = [item for item in results if item.get("evidence")]
    traceable = [
        item for item in resolved
        if item.get("evidence")
        and item.get("clause")
        and (item.get("source") or {}).get("url")
    ]

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    return {
        "automated_check_count": total,
        "manual_check_count": len(manual_checks),
        "resolved_check_count": len(resolved),
        "unresolved_check_count": total - len(resolved),
        "evidence_backed_check_count": len(evidence_backed),
        "traceable_decision_count": len(traceable),
        "decision_coverage": rate(len(resolved), total),
        "evidence_coverage": rate(len(evidence_backed), total),
        "traceability_rate": rate(len(traceable), len(resolved)),
        "automation_scope": rate(total, total + len(manual_checks)),
        "definition": {
            "decision_coverage": "已得到通过或不通过结论的自动检查占比",
            "evidence_coverage": "至少关联一条企业材料证据的自动检查占比",
            "traceability_rate": "同时具备政策来源、条款和企业材料的已决检查占比",
            "automation_scope": "当前已编码检查占全部自动与人工检查事项的占比",
        },
    }


def review(company_data: dict, policy: dict, as_of: date) -> dict:
    company = Company.model_validate(company_data)
    results = []
    for rule in policy["rules"]:
        facts = Facts(company)
        missing = []
        try:
            passed, reasoning, calculation = evaluate_rule(rule, facts, as_of, policy)
            status = "pass" if passed else "fail"
        except NeedsReview as exc:
            status, reasoning, calculation = exc.status, str(exc), {}
            missing = exc.fields
        except (ValueError, TypeError, InvalidOperation) as exc:
            status, reasoning, calculation = "unknown", f"数据格式需核验：{exc}", {}
            missing = rule["fields"]
        evidence_ids = list(dict.fromkeys(eid for key in facts.used if key in company.facts for eid in company.facts[key].evidence))
        results.append({**rule, "status": status, "status_label": STATUS_LABELS[status], "reasoning": reasoning,
                        "calculation": calculation, "used_fields": facts.used, "missing_fields": missing,
                        "evidence": [e.model_dump() for e in company.evidence if e.id in evidence_ids]})
    counts = {s: sum(r["status"] == s for r in results) for s in STATUS_LABELS}
    status = "fail" if counts["fail"] else "conflict" if counts["conflict"] else "unknown" if counts["unknown"] else "pass"
    fingerprint = hashlib.sha256(json.dumps({"company": company_data, "policy": policy, "as_of": str(as_of)}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"id": uuid4().hex, "company_id": company.id, "company_name": company.name, "is_demo": company.is_demo,
            "policy_id": policy["id"], "policy_name": policy["name"], "policy_version": policy["version"], "as_of": str(as_of),
            "status": status, "status_label": STATUS_LABELS[status], "counts": counts, "checks": results,
            "window": window_status(policy, as_of), "manual_checks": policy["manual_checks"], "scope_note": policy["scope_note"],
            "quality": quality_metrics(results, policy["manual_checks"]),
            "fingerprint": fingerprint, "engine_version": "0.2.0",
            "missing_fields": list(dict.fromkeys(k for r in results for k in r["missing_fields"])),
            "disclaimer": "材料预审辅助结果，仅覆盖已实现指标，不是资格认定或获批承诺。"}


def dependency_graph(report: dict) -> dict:
    nodes, edges = {}, []
    def node(nid, label, kind, **extra):
        nodes[nid] = {"id": nid, "label": label, "kind": kind, **extra}
    def edge(source, target, relation):
        edges.append({"source": source, "target": target, "relation": relation})
    node("decision", report["status_label"], "decision", status=report["status"])
    for check in report["checks"]:
        rid = "rule:" + check["id"]
        sid = "source:" + check["source"]["id"]
        node(sid, check["source"]["title"], "source", url=check["source"]["url"])
        node(rid, check["title"], "rule", status=check["status"], reasoning=check["reasoning"])
        edge(sid, rid, check["clause"])
        edge(rid, "decision", "支撑预审")
        for key in check["used_fields"]:
            fid = "fact:" + key
            node(fid, field_label(key), "fact")
            edge(fid, rid, "参与判断")
        for evidence in check["evidence"]:
            eid = "evidence:" + evidence["id"]
            node(eid, evidence["title"], "evidence", text=evidence["text"], locator=evidence["locator"])
            # This link records actual material use in the check, not inferred causality.
            edge(eid, rid, "提供材料")
    return {"nodes": list(nodes.values()), "edges": edges, "report_id": report["id"]}


def compare_policies(old: dict, new: dict, companies: list[dict], as_of: date) -> dict:
    if old["family"] != new["family"]:
        raise ValueError("仅能比较同一事项的版本")
    changes = []
    for key, label in [("year", "申报年度"), ("start", "开放日期"), ("deadlines", "申报截止日期"), ("published", "通知发布日期")]:
        if old.get(key) != new.get(key):
            changes.append({"field": key, "label": label, "before": old.get(key), "after": new.get(key), "source": new["source"]})
    old_rules = {r["id"]: r for r in old["rules"]}
    changed_rules = []
    for rule in new["rules"]:
        previous = old_rules.get(rule["id"], {})
        keys = ("fields", "op", "threshold", "expected", "period")
        if any(previous.get(k) != rule.get(k) for k in keys):
            changed_rules.append(rule["id"])
            changes.append({"field": rule["id"], "label": rule["title"], "before": {k: previous[k] for k in keys if k in previous}, "after": {k: rule[k] for k in keys if k in rule}, "source": rule["source"]})
    impacts = []
    for company in companies:
        before = review(company, old, as_of)
        after = review(company, new, as_of)
        impacts.append({"company_id": company["id"], "company_name": company["name"], "before_status": before["status_label"], "after_status": after["status_label"],
                        "before_window": before["window"]["label"], "after_window": after["window"]["label"], "review_rule_ids": changed_rules,
                        "missing_fields": after["missing_fields"], "requires_review": bool(changes)})
    return {"old": old["id"], "new": new["id"], "as_of": str(as_of), "changes": changes, "impacts": impacts,
            "note": "两个真实申报季的配置比较；年份及资料期间变化不代表全国认定门槛发生变化。复核结果按同一指定日期重算。"}


def markdown_report(report: dict) -> str:
    lines = [f"# {report['company_name']} · 材料预审报告", "", f"事项：{report['policy_name']}（{report['policy_version']}）", f"核查日期：{report['as_of']}",
             f"数据性质：{'模拟企业、模拟材料' if report['is_demo'] else '用户提供，来源及真实性需核验'}", f"指标核查：{report['status_label']}", f"受理窗口：{report['window']['label']}", "", report["disclaimer"], ""]
    quality = report.get("quality") or {}
    if quality:
        lines.extend([
            "## 可验证性指标",
            f"- 决策覆盖率：{quality['decision_coverage']:.0%}（{quality['resolved_check_count']}/{quality['automated_check_count']}）",
            f"- 企业材料证据覆盖率：{quality['evidence_coverage']:.0%}",
            f"- 已决检查可追溯率：{quality['traceability_rate']:.0%}",
            f"- 当前自动化范围：{quality['automation_scope']:.0%}；仍有 {quality['manual_check_count']} 项需人工核验",
            "",
        ])
    for check in report["checks"]:
        lines.extend([f"## {check['title']}：{check['status_label']}", check["reasoning"], f"政策依据：[{check['source']['title']}]({check['source']['url']}) · {check['clause']}", f"条款摘要：{check['quote']}"])
        for e in check["evidence"]:
            lines.extend([f"材料：{e['title']} · {e['locator']}", e["text"]])
        lines.append("")
    lines.extend(["## 待人工核验", *[f"- {x}" for x in report["manual_checks"]], "", report["scope_note"], "", f"输入与规则快照 SHA-256：{report['fingerprint']}"])
    return "\n".join(lines)
