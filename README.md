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

普通启动会自动加载仓库附带的自采 EEGNet 模型
`src/braincheck/models/pilot_eegnet/braincheck_eegnet.pt`，与 `pilot_rules_v2`
融合输出四态，并支持关联复测。模型来自 3 人、4 次记录、363 个窗口的 20 轮训练。
当前为全数据拟合，未独立验证；概率阈值 0.5 和运动门控放宽配置均为未校准工程参数。
模型版本、SHA256、运行模式与验证范围见 [部署说明](docs/EEGNET_DEPLOYMENT.md)。

```bash
bash "macos/run.sh" --eegnet-mode shadow  # 仅记录模型概率
bash "macos/run.sh" --no-eegnet          # 仅使用既有规则
```

旧版固定结果演示（不用于验证 EEGNet 融合）：

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

不带演示参数时进入真实采集与模型融合流程。仓库已附带可运行模型，但尚未完成
独立被试与岗位场景验证；模型缺失不会自动等同于 `normal`，工程结果不应描述为
已验证的临床或岗位结论。

调试端默认隐藏，仅 `--debug` 启用。产品主流程不包含研究协议选择或 PVT；原始 XDF、
Marker 审计和采集上下文保存在数据根目录的 `captures/` 下，普通受试结果页不显示路径或
原始脑信号。
