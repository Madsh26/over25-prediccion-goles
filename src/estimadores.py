"""Estimador de referencia serializable: frecuencias aprendidas solo en train."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class BasePorLiga(ClassifierMixin, BaseEstimator):
    """Mayoría por liga; la probabilidad es la frecuencia Over de entrenamiento."""
    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        self.prior_ = float(np.mean(y))
        self.por_liga_ = {liga: float(np.mean(np.asarray(y)[np.asarray(X['liga']) == liga]))
                          for liga in X['liga'].unique()}
        return self

    def predict_proba(self, X):
        p = X['liga'].map(self.por_liga_).fillna(self.prior_).to_numpy()
        return np.column_stack([1-p, p])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= .5).astype(int)
