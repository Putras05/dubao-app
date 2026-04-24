"""Validation cho AR order (p)."""
import math
from core.i18n import t


def validate_ar_order(p: int, n_train: int) -> tuple:
    """
    Validate AR order p.
    Returns (status, message): status ∈ {'ok', 'warn', 'err'}
    """
    if not isinstance(p, int) or p < 1:
        return 'err', t('validate.err_p_min')
    if p > 50:
        return 'err', t('validate.err_p_max', p=p)
    if p > n_train - 50:
        return 'err', t('validate.err_p_data', p=p, max_p=max(1, n_train - 50))

    sqrt_n = int(math.sqrt(n_train))
    n10    = n_train // 10

    if p > sqrt_n:
        return 'warn', t('validate.warn_overfit', p=p, sqrt_n=sqrt_n)
    if p > n10:
        return 'warn', t('validate.warn_params', p=p, n10=n10)

    return 'ok', t('validate.ok', obs=n_train)


def validate_params(p: int, n_total: int, train_ratio: float) -> dict:
    """Validate AR order p. Returns dict với status + messages."""
    n_train = int(n_total * train_ratio)

    p_status, p_msg = validate_ar_order(p, n_train)

    return {
        'overall':  p_status,
        'p_status': p_status,
        'p_msg':    p_msg,
    }
