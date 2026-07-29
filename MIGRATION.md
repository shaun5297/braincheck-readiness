# 从 bsense-lsl 的产品化迁移

只迁移 LSL 接入、内置录制、Marker、线程安全状态机制和必要质量检查。研究协议 M0-M5/M7、PVT、完整研究问卷和协议选择器均不进入本工程。

`readiness.py` 已拆分为：

- `quality/`：先于推理的数据质量门控；
- `features/`：行为、EEG、fNIRS、背景与个人偏移；
- `inference/`：透明规则、可选模型、融合和解释；
- `workflow/`：固定筛查与复测状态机；
- `baseline/`：跨日个人清醒基线；
- `privacy/` 与 `reports/`：角色隔离、审计和结果投影。

研究采集与离线训练由 `bsense-dataset-studio` 负责；BrainCheck 只加载经审计的模型，不在现场训练。

