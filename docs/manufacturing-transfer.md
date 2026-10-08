# 第二行业迁移演示：制造业来料抽检

`data/manufacturing_transfer.json` 是**完全合成的内部规范与批次**，只用于验证企策通的规则、事实、证据和报告结构能否脱离北京政策场景复用；它不是行业标准、企业合同或真实批次。

演示模板包含供应商准入、抽样合格率和严重缺陷数三项规则，以及分别预期通过、不通过和待补证的三批合成数据。`scripts/evaluate_transfer.py` 使用与北京案例相同的 `qicetong.engine.review` 和证据依赖图生成器；运行结果在 `artifacts/manufacturing-transfer-results.json`，目前 3/3 符合预设状态。`tests/test_transfer.py` 还在隔离数据库中验证了复用 `review_enterprise` 工具函数，且北京原有政策未被覆盖。

这个结果只证明当前结构能承载另一类规则与证据，不证明制造业真实现场效果，也没有实测迁移工时、真实材料抽取或第二行业 Nexent Skill。它属于合成模板的技术迁移验证。
