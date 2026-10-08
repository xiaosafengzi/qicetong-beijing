# README 图示

三张图沿用工作台的蓝色与青绿色。封面介绍项目，流程图展示材料、规则与工具的关系，评测图展示保存的模拟困难案例结果。

| 文件 | 内容 | 来源 |
| --- | --- | --- |
| `cover.png` | 项目封面插画 | 使用内置 imagegen 生成，提示词见下文 |
| `architecture.svg` | 材料、规则、核查和报告流程 | `docs/architecture.md` 的系统结构；实线表示业务数据，虚线表示工具调用 |
| `evaluation.svg` | 状态、案例和待补字段精确匹配对比 | `artifacts/evaluation-results.json` 的正确数与标注样本数 |

两张 SVG 保留可编辑文本与矢量图形，由标准库 Python 脚本生成：

```powershell
.\.venv\Scripts\python.exe scripts\build_readme_graphics.py
```

评测图三个面板均使用 0–100% 比例轴，待补字段指标采用有字段标注的 7 个案例。更新评测结果后，可运行脚本刷新图示。

## 封面生成提示词

生成方式：内置 imagegen；不透明背景。提示词如下：

```text
Use case: ads-marketing, illustrated GitHub README project cover.
Create one finished wide horizontal banner, approximately 1600 x 640, for the existing Chinese open-source project 企策通, a Beijing enterprise policy document pre-review workbench.
Use an elegant white and very pale periwinkle background, navy typography, periwinkle blue (#627fe2) and teal (#228c78) accents, restrained soft shadows, lots of breathing room, professional editorial composition. Left area: clearly readable, impeccably typeset exact Chinese title "企策通", smaller second line "北京企业政策预审", and short descriptive third line "从政策条款到企业材料，让每项判断都有依据". At bottom of the text area include three small understated pill labels with exact text "Nexent" "MCP" "Skills".
Right area: tasteful polished isometric illustration of several enterprise document sheets, a policy book, a translucent evidence connection graph, and a teal checkmark. Objects represent materials, rules, evidence and review reports, with tiny abstract grey placeholder lines, no invented interface screenshots or graphs or quantitative metrics. A faint abstract Beijing skyline can form a quiet backdrop.
The banner must remain crisp and highly readable at 800px wide. No people, no robot mascots, no government seal, no Huawei or third-party logos, no copyright marks, no performance claims, no slogans beyond the exact supplied text. Flat editorial illustration with subtle dimension; avoid neon, cyberpunk and clutter. Output a finished opaque banner.
```
