"""Build editable README diagrams using the standard library and saved evaluation data."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
INK = "#172849"
MUTED = "#586b87"
BLUE = "#627fe2"
TEAL = "#228c78"
FONT = "'Noto Sans SC','Noto Sans CJK SC','Microsoft YaHei','PingFang SC',Arial,sans-serif"


class SVG:
    def __init__(self, width: int, height: int, title: str, description: str):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8b9bb9"/></marker></defs>',
        ]
        self.rect(0, 0, width, height, "#ffffff", radius=24)

    def rect(self, x, y, width, height, fill, radius=12, stroke="none"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')

    def text(self, x, y, content, size=18, fill=INK, weight=400, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="{escape(FONT, quote=True)}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(str(content))}</text>')

    def line(self, x1, y1, x2, y2, color="#dce4f0", width=1):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')

    def arrow(self, path, dashed=False):
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        self.parts.append(f'<path d="{path}" fill="none" stroke="#8b9bb9" stroke-width="2.2" stroke-linejoin="round"{dash} marker-end="url(#arrow)"/>')

    def node(self, x, y, width, title, lines, tag, color=BLUE, height=132):
        self.rect(x, y, width, height, "#ffffff", stroke="#dfe6f2")
        self.rect(x+18, y+18, 36, 26, "#edf2ff" if color == BLUE else "#eaf7f1", radius=7)
        self.text(x+36, y+37, tag, 13, color, 700, "middle")
        self.text(x+65, y+38, title, 21, INK, 650)
        for index, line in enumerate(lines):
            self.text(x+20, y+72+index*25, line, 16, MUTED)

    def save(self, path: Path):
        content = "\n".join(self.parts) + "\n</svg>\n"
        ElementTree.fromstring(content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def architecture():
    s = SVG(1320, 890, "企策通系统流程", "企业材料经解析和人工确认形成事实，官方政策形成版本化规则，两者进入确定性核查并生成报告与证据图。Nexent Agent 通过 MCP 编排核查、检索和版本影响分析。")
    s.text(48, 66, "从材料到判断，保留完整证据路径", 33, weight=700)
    s.text(48, 103, "Nexent 编排业务工具 · 规则引擎执行核查 · 人工确认材料事实", 18, MUTED)
    s.rect(32, 130, 1256, 163, "#f3f6ff", radius=18)
    s.rect(32, 329, 1256, 499, "#f8fafc", radius=18)
    s.text(52, 321, "浏览器工作台：材料审核与预审操作", 17, MUTED)

    # Dashed paths carry orchestration; solid paths carry facts, rules, or results.
    s.arrow("M 614 216 L 652 216", dashed=True)
    s.arrow("M 914 216 L 952 216", dashed=True)
    s.arrow("M 783 272 L 783 305 L 1109 305 L 1109 363", dashed=True)
    s.arrow("M 1268 216 L 1304 216 L 1304 691 L 1268 691")
    s.arrow("M 314 429 L 352 429")
    s.arrow("M 614 429 L 652 429")
    s.arrow("M 914 429 L 952 429")
    s.arrow("M 314 628 L 352 628")
    s.arrow("M 614 628 L 930 628 L 930 466 L 952 466")
    s.arrow("M 1109 495 L 1109 635")

    s.node(352, 150, 262, "Nexent Agent", ["意图理解与工具编排", "5 个 Skill 工作流"], "AI", height=122)
    s.node(652, 150, 262, "MCP 工具服务", ["9 个业务工具", "HTTP / SSE / stdio"], "↗", height=122)
    s.node(952, 150, 316, "检索与版本分析", ["政策证据检索", "版本差异与企业影响"], "↻", height=122)
    s.text(57, 184, "智能体入口", 24, weight=650)
    s.text(57, 219, "按任务调用工具", 17, MUTED)
    s.text(57, 249, "组织结论与待补事项", 17, MUTED)
    s.node(52, 363, 262, "企业材料", ["文档 · 表格 · 图片", "原文位置与文件标识"], "01")
    s.node(352, 363, 262, "解析与候选", ["文本解析 / OCR / 模型", "逐项人工核对"], "02")
    s.node(652, 363, 262, "已确认事实", ["数值 · 单位 · 所属期间", "审核状态与证据引用"], "03")
    s.node(952, 363, 316, "确定性核查", ["阈值 · 比例 · 期间 · 冲突", "条件与受理窗口分别计算"], "04", TEAL)
    s.node(52, 562, 262, "官方政策", ["政策条款与年度通知", "来源与适用日期"], "P")
    s.node(352, 562, 262, "版本化规则", ["规则 ID · 所需字段", "原文出处与会计期间"], "R")
    s.node(952, 635, 316, "报告与证据图", ["逐项状态与引用", "待补事项与复核建议"], "05", TEAL)
    s.text(674, 762, "材料事实 + 政策规则", 18, TEAL, 600)
    s.line(48, 842, 1272, 842)
    s.text(48, 871, "实线：业务数据与结果", 15, MUTED)
    s.text(286, 871, "虚线：智能体工具调用", 15, MUTED)
    s.text(1272, 871, "企策通 · 北京企业政策预审", 15, MUTED, anchor="end")
    s.save(OUT / "architecture.svg")


def evaluation():
    record = json.loads((ROOT / "artifacts/evaluation-results.json").read_text(encoding="utf-8"))
    engine = record["engine"]["summary"]
    model = record["llm_baseline"]["summary"]
    metrics = [
        ("状态判断", "status_correct", "case_count"),
        ("案例精确匹配", "exact_case_count", "case_count"),
        ("待补字段精确匹配", "missing_field_exact", "missing_field_cases"),
    ]
    s = SVG(1200, 585, "企策通模拟困难案例评测", "在同一政策规则和结构化企业事实下比较确定性规则引擎与 Qwen3 8B 单模型。结果从 evaluation-results.json 读取；待补字段指标使用有字段标注的案例子集。")
    s.text(48, 62, "规则执行与单模型判断的对比", 33, weight=700)
    s.text(48, 99, "模拟困难案例 · 同一政策规则与结构化事实 · 精确匹配指标", 18, MUTED)
    s.rect(50, 126, 15, 15, BLUE, radius=4)
    s.text(76, 140, "确定性规则引擎", 16, MUTED)
    s.rect(287, 126, 15, 15, TEAL, radius=4)
    s.text(313, 140, "Qwen3 8B 单模型", 16, MUTED)

    for index, (label, correct_key, total_key) in enumerate(metrics):
        left = 48 + index*380
        s.text(left, 193, label, 22, weight=650)
        assert engine[total_key] == model[total_key] and engine[total_key] > 0
        total = engine[total_key]
        s.text(left, 221, f"标注样本：{total} 个", 15, MUTED)
        plot_left, plot_width = left, 330
        # Each percentage axis starts at zero and ends at 100.
        for percentage in (0, 50, 100):
            x = plot_left + plot_width*percentage/100
            s.line(x, 242, x, 452, "#e9edf4")
            s.text(x, 477, f"{percentage}%", 13, MUTED, anchor="middle")
        for row, (summary, color, method) in enumerate([(engine, BLUE, "确定性规则引擎"), (model, TEAL, "Qwen3 8B 单模型")]):
            correct = summary[correct_key]
            assert 0 <= correct <= total
            value = correct/total
            y = 275 + row*108
            s.text(plot_left, y-12, method, 15, MUTED)
            s.rect(plot_left, y, plot_width, 36, "#f0f3f8", radius=6)
            s.rect(plot_left, y, round(plot_width*value, 3), 36, color, radius=6)
            formatted = "100%" if correct == total else f"{value*100:.1f}%"
            s.text(plot_left+10, y+25, formatted, 17, "#ffffff", 650)
            s.text(plot_left+plot_width, y-12, f"{correct}/{total}", 17, color, 700, "end")
    s.line(48, 512, 1152, 512)
    s.text(48, 543, "样本类型：公开政策规则 + 模拟企业材料", 15, MUTED)
    s.text(48, 568, "来源：artifacts/evaluation-results.json · 指标按保存的正确数 / 标注样本数计算", 14, MUTED)
    s.save(OUT / "evaluation.svg")


def main():
    architecture()
    evaluation()
    print("Generated docs/assets/architecture.svg and docs/assets/evaluation.svg")


if __name__ == "__main__":
    main()
