---
name: precheck-report
description: 导出已完成预审的证据报告，保留条款、材料定位、计算口径和输入指纹。仅用于已有 report_id 的报告交付，不代替前置核查。
---

# 预审报告导出

使用已返回的 report_id 调用 `export_review_report`。没有 report_id 时先按用户已选择的企业、事项和日期完成 `review_enterprise`。

输出工具返回的 Markdown 正文或保存为返回的文件名。保留企业模拟标识、版本、日期、受理窗口、每项判断、政策 URL、材料定位、人工事项及 SHA-256 指纹。

可以压缩说明文字，但不得删除 unknown、conflict、失败项、来源或尚未覆盖的业务条件。报告不包含“认定通过”“保证获批”等超出工具证据的表述。

模板迁移时修改地域及事项配置并重新评测，不以改名证明跨行业适用性。
