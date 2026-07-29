QUALITY_SECONDS = 30
BASELINE_SECONDS = 45
SART_TRIAL_COUNT = 180
SART_SECONDS = 180
RETEST_REST_MINUTES = (10, 15)


def expected_total_seconds(first_time_form: bool = False) -> int:
    return QUALITY_SECONDS + BASELINE_SECONDS + SART_SECONDS + (45 if first_time_form else 15)

