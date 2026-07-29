REASON_TEXT = {
    "eeg_quality_insufficient": "脑电信号质量不足",
    "fnirs_quality_insufficient": "额区光学信号质量不足",
    "fnirs_saturation": "额区光学信号存在饱和",
    "excessive_motion": "佩戴稳定性不足",
    "lsl_stream_incomplete": "设备数据流不完整",
    "invalid_lsl_timestamps": "设备时间戳异常",
    "insufficient_valid_trials": "有效任务数据不足",
    "high_sleepiness": "当前主观困倦程度较高",
    "short_sleep": "过去24小时睡眠时长偏短",
    "extended_wakefulness": "连续清醒时长较长",
    "elevated_omission_rate": "持续注意任务漏检增加",
    "elevated_commission_rate": "反应抑制错误增加",
    "increased_rt_variability": "反应时间稳定性下降",
    "behavior_shift_from_personal_baseline": "行为指标偏离个人清醒基线",
    "eeg_shift_from_personal_baseline": "脑电特征偏离个人清醒基线",
    "multimodal_shift": "多模态指标同时出现偏移",
}


def explain(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(REASON_TEXT.get(code, code) for code in codes)

