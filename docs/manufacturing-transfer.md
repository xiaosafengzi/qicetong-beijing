# 第二行业迁移演示：制造业来料抽检

`data/manufacturing_transfer.json` 提供合成的内部规范与批次，验证企策通的规则、事实、证据和报告结构在制造业抽检场景中的复用。

演示模板包含供应商准入、抽样合格率和严重缺陷数三项规则，以及分别预期通过、不通过和待补证的三批合成数据。`scripts/evaluate_transfer.py` 使用与北京案例相同的 `qicetong.engine.review` 和证据依赖图生成器；运行结果在 `artifacts/manufacturing-transfer-results.json`，目前 3/3 符合预设状态。`tests/test_transfer.py` 还在隔离数据库中验证了复用 `review_enterprise` 工具函数，且北京原有政策未被覆盖。

这组测试验证了同一引擎在两类业务中的复用。制造业现场效果、迁移工时、真实材料抽取和第二行业 Nexent Skill 的验证是后续扩展项。
