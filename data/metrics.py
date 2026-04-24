import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error


def calc_metrics(ytrue, ypred, k: int = 1) -> dict:
    ytrue, ypred = np.array(ytrue), np.array(ypred)
    rmse  = np.sqrt(mean_squared_error(ytrue, ypred))
    mae   = mean_absolute_error(ytrue, ypred)
    mask  = ytrue != 0
    mape  = np.mean(np.abs((ytrue[mask] - ypred[mask]) / ytrue[mask])) * 100
    ssr   = np.sum((ytrue - ypred) ** 2)
    sst   = np.sum((ytrue - np.mean(ytrue)) ** 2)
    r2    = 1 - ssr / sst if sst else 0
    n     = len(ytrue)
    r2adj = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2
    return dict(MAPE=mape, RMSE=rmse, MAE=mae, R2adj=r2adj)


def calc_r2(ytrue, ypred) -> float:
    ytrue, ypred = np.array(ytrue), np.array(ypred)
    ssr = np.sum((ytrue - ypred) ** 2)
    sst = np.sum((ytrue - np.mean(ytrue)) ** 2)
    return 1 - ssr / sst if sst else 0


def _ci95(ytrue, ypred) -> float:
    return 1.96 * float(np.std(np.array(ytrue) - np.array(ypred)))


def _star(mape: float) -> str:
    if mape < 1.0: return '★★★'
    if mape < 2.0: return '★★'
    if mape < 3.0: return '★'
    return ''
