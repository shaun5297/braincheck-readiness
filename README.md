# 脑安检（BrainCheck Readiness）

面向高风险岗位班前场景的短时认知准备度辅助评估产品。产品只有一条固定流程：

```text
匿名身份 → 隐私告知 → 必要状态 → 设备质检 → 睁眼基线
→ 3 分钟 SART → 多模态特征 → 四态结果 → 必要时休息复测
```

输出为“正常、建议复测、建议休息、无法评估”。结果只描述当次班次状态，不构成医疗诊断、自动化上岗决定、绩效评价或永久能力画像。

## 运行

```bash
bash "macos/setup.sh"
bash "macos/run.sh"
```

比赛演示：

```bash
bash "macos/run.sh" --competition-demo
```

`--competition-demo` 会执行真实 LSL/XDF/Marker 采集、30 秒质检、45 秒睁眼基线和
3 分钟 SART。数据通过质量门控后，结果页显示明确标注的 `正常（演示）` 占位结果；
该结果会以 `competition_demo_placeholder_v1` 落盘，不代表真实受试状态结论。质量门控
失败时仍显示“无法评估”，不会用演示结果掩盖设备或数据问题。

仅检查结果页面、不连接设备时使用合成情景演示：

```bash
bash "macos/run.sh" --demo --scenario retest
bash "macos/run.sh" --demo --scenario unable
bash "macos/self_test.sh"
```

不带演示参数时进入真实正式流程，并使用当前 `pilot_rules_v2` 先导规则。仓库尚未部署
经过该场景验证的训练模型；模型缺失不会自动等同于 `normal`，也不应把先导规则结果
描述为已验证的临床或岗位结论。

调试端默认隐藏，仅 `--debug` 启用。产品主流程不包含研究协议选择或 PVT；原始 XDF、
Marker 审计和采集上下文保存在数据根目录的 `captures/` 下，普通受试结果页不显示路径或
原始脑信号。
