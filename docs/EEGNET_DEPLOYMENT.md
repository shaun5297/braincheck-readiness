# EEGNet 部署与多源融合

## 当前已部署

自采模型位于 `src/braincheck/models/pilot_eegnet/`，版本 `eegnet-pilot-49d457921545`。
本地 `.venv-supported` 已安装torch2.12.0等推理依赖。普通 `bash macos/run.sh` 自动加载模型，以 `pilot_assisted` 参与四态融合。
主界面为“EEGNet 多源融合”，结果页展示模型概率及有效窗口，结果详情保留工程阈值未校准说明。
Windows `setup.bat` 已增加推理依赖，未在Windows实机验证。

```bash
bash macos/run.sh
bash macos/run.sh --eegnet-mode shadow
bash macos/run.sh --no-eegnet
```

不要用 `--competition-demo` 验证真实模型融合：该既有选项是固定normal演示占位，与本次实际推理模式不同。
`--demo` 是合成场景演示，均不自动加载真实模型。

## 实际判定配置

- 参考概率>=0.5时，首测至少建议复测，关联复测至少建议休息。0.5是工程参数，不是验证集校准阈值。
- EEGNet低风险不覆盖行为与背景规则的高风险，模型是融合证据之一。
- 仅因整体运动比例失败时，配置允许<=40%运动伪迹且已有至少10个合格模型窗口进入融合。逐窗gyro跨度阈值5保持不变。
- 其他质量问题、>40%运动或不足10个合格窗口仍输出无法评估。原始QC与有效判定QC均保存。
- 当前模型未独立验证，只允许shadow和显式工程策略pilot_assisted。未来经过独立验证的模型才使用原assisted校准路径。

模型清单内 `pilot_decision_policy` 保存上述阈值与calibrated:false。`decision_threshold:null`、`calibration_split:none`保持真实状态，未伪造验证信息。
原训练导出报告默认仅shadow，用户授权参与四态后增加了独立部署策略；权重SHA256未变。

## 推理与复测

完整baseline/SART信号按4秒窗、2秒步长切分，经逐窗EEG/Motion门控、250Hz重采样，使用模型内置去均值、1–40HzFFT和训练通道缩放，取窗口概率均值。
校验模型SHA256、输入形状、通道顺序、采样率、类别和来源。合成模型拒绝现场加载。
结果为建议复测时，点击“休息调整后进行关联复测”，休息后重新采集，会保存父评估ID。更换受试者或普通返回首页清除关联。个人历史基线仍是原有未接入项。
fNIRS用于特征/QC，Motion判断数据可靠性，不作为疲劳分。

## 已运行验证

真实4条XDF回放确认模型与融合可运行，P001首次retest，重复同一XDF验证复测分支为rest；后者只是分支测试，不是新的真实复测。
自动化测试覆盖normal/retest/rest/unable，质量失败优先、模型错误回退、通道校验及复测关联清除。
结果位于 `/Users/shaun/BCI/outputs/readiness_eegnet/20260917-pilot-relaxed/deployed_fusion_verification.json`。

```bash
braincheck-replay --xdf "/path/run.xdf" --events "/path/run_events.jsonl" --context "/path/run_context.json" --output "/path/results" --model-manifest "/path/model_manifest.json" --mode pilot_assisted
```

本次只在macOS进行软件部署及离线真实数据回放，没有新一次设备现场试验，也没有独立模型性能结论。模型363窗全部用于拟合，不能把回放当作泛化评估。
