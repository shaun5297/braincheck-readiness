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
braincheck --demo --scenario retest
braincheck --demo --scenario unable
braincheck-self-test
```

调试端默认隐藏，仅 `--debug` 启用。产品主流程不包含研究协议选择、PVT、原始 XDF 路径或原始脑信号。
