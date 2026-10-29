"""Fase 4 y predicciones: selección temporal, sin consultar el test al ajustar.

Ejecutar desde proyecto_over25: .venv/Scripts/python.exe -u src/modelo.py
Se conservan los cuatro estimadores en un único artefacto joblib canónico.
"""
import hashlib
import json
import logging
import platform
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             roc_auc_score, log_loss, confusion_matrix, brier_score_loss)
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from config import RAIZ, SEMILLA
from estimadores import BasePorLiga

CLEAN = RAIZ / 'data/clean'
MODELOS = RAIZ / 'data/modelo'
NOMBRES = ['Línea base', 'Regresión logística', 'Random Forest', 'XGBoost']


def guardar(df, nombre):
    """Escritura atómica con el mismo control de bloqueos de los CSV anteriores."""
    from config import reemplazar
    path = CLEAN / nombre
    tmp = path.with_suffix(path.suffix + '.tmp')
    df.to_csv(tmp, index=False, encoding='utf-8-sig', float_format='%.10g')
    reemplazar(tmp, path)


def metricas(y, p):
    pred = (p >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(n=len(y), accuracy=accuracy_score(y, pred),
                precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred, zero_division=0),
                f1=f1_score(y, pred, zero_division=0), roc_auc=roc_auc_score(y, p),
                log_loss=log_loss(y, p, labels=[0, 1]), brier=brier_score_loss(y, p),
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(RAIZ/'informe/scraping.log', encoding='utf-8')])
    import verificar
    verificar.main()
    meta = json.loads((CLEAN/'metadatos_modelo.json').read_text(encoding='utf-8'))
    numericas = meta['features_numericas']
    columnas = numericas + ['liga']
    assert not set(columnas) & {'motivo_exclusion', 'over25', 'goles_local', 'goles_visitante', 'total_goles'}
    datos = pd.read_csv(CLEAN/'dataset_modelo.csv').sort_values(['fecha', 'id_partido']).reset_index(drop=True)
    train = datos[datos.temporada.isin(['2023-24', '2024-25'])].reset_index(drop=True)
    test = datos[datos.temporada.eq('2025-26')].reset_index(drop=True)
    assert len(train) == 1749 and len(test) == 1008 and len(datos) == len(train)+len(test)
    assert train.fecha.max() < test.fecha.min()
    assert not set(train.id_partido) & set(test.id_partido)
    X, y = train[columnas], train.over25.astype(int)
    Xt, yt = test[columnas], test.over25.astype(int)
    assert np.isfinite(X[numericas]).all().all() and np.isfinite(Xt[numericas]).all().all()

    # TimeSeriesSplit opera sobre días únicos; jamás separa partidos del mismo día.
    dias = np.array(sorted(train.fecha.unique()))
    folds, auditoria = [], []
    for i, (a, b) in enumerate(TimeSeriesSplit(n_splits=4).split(dias), 1):
        ia = np.flatnonzero(train.fecha.isin(dias[a]))
        ib = np.flatnonzero(train.fecha.isin(dias[b]))
        assert train.iloc[ia].fecha.max() < train.iloc[ib].fecha.min()
        folds.append((ia, ib))
        auditoria.append(dict(fold=i, n_train=len(ia), n_validacion=len(ib),
                              fecha_max_train=train.iloc[ia].fecha.max(),
                              fecha_min_validacion=train.iloc[ib].fecha.min(),
                              fecha_max_validacion=train.iloc[ib].fecha.max()))

    def pipeline(estimador, escalar=False):
        pasos = [('imputar', SimpleImputer(strategy='median'))]
        if escalar:
            pasos.append(('escalar', StandardScaler()))
        prep = ColumnTransformer([('num', Pipeline(pasos), numericas),
                                  ('liga', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['liga'])])
        return Pipeline([('preparar', prep), ('modelo', estimador)])

    candidatos = {
        NOMBRES[0]: (BasePorLiga(), {}),
        NOMBRES[1]: (pipeline(LogisticRegression(max_iter=3000, random_state=SEMILLA), True),
                     {'modelo__C': [.005, .02, .1, .5]}),
        NOMBRES[2]: (pipeline(RandomForestClassifier(n_estimators=300, max_features=.5,
                      max_samples=.8, n_jobs=2, random_state=SEMILLA)),
                     {'modelo__max_depth': [2, 3], 'modelo__min_samples_leaf': [40, 80]}),
        NOMBRES[3]: (pipeline(XGBClassifier(n_estimators=150, learning_rate=.03,
                      subsample=.8, colsample_bytree=.7, reg_alpha=5, reg_lambda=30,
                      eval_metric='logloss', n_jobs=2, random_state=SEMILLA, tree_method='hist')),
                     {'modelo__max_depth': [1, 2], 'modelo__min_child_weight': [30, 60]})}
    ajustados, busquedas, resumen, cv_filas = {}, {}, [], []
    for nombre, (estimador, grid) in candidatos.items():
        print(f'Ajustando {nombre}: cuatro cortes temporales', flush=True)
        busqueda = GridSearchCV(estimador, grid, cv=folds,
                               scoring={'log_loss': 'neg_log_loss', 'roc_auc': 'roc_auc'},
                               refit='log_loss', n_jobs=1, error_score='raise', return_train_score=False)
        busqueda.fit(X, y)
        ajustados[nombre] = busqueda.best_estimator_
        busquedas[nombre] = busqueda
        k = busqueda.best_index_
        resumen.append(dict(modelo=nombre, cv_log_loss=-float(busqueda.cv_results_['mean_test_log_loss'][k]),
                             cv_roc_auc=float(busqueda.cv_results_['mean_test_roc_auc'][k]),
                             parametros=busqueda.best_params_))
        for j, params in enumerate(busqueda.cv_results_['params']):
            cv_filas.append(dict(modelo=nombre, parametros=json.dumps(params, ensure_ascii=False),
                                 log_loss_media=-busqueda.cv_results_['mean_test_log_loss'][j],
                                 log_loss_desv=busqueda.cv_results_['std_test_log_loss'][j],
                                 roc_auc_media=busqueda.cv_results_['mean_test_roc_auc'][j]))
        logging.info('FASE 4 %s CV log loss %.5f', nombre, resumen[-1]['cv_log_loss'])
    # Selección cerrada antes de evaluar el test. La referencia también puede ganar.
    elegido = sorted(resumen, key=lambda r: (r['cv_log_loss'], -r['cv_roc_auc']))[0]['modelo']
    registros, predicciones = [], []
    for nombre, estimador in ajustados.items():
        p = estimador.predict_proba(Xt)[:, 1]
        salida = test[['id_partido', 'liga', 'temporada', 'fecha', 'jornada', 'local', 'visitante', 'over25']].copy()
        salida['modelo'] = nombre
        salida['probabilidad_over25'] = p
        salida['prediccion_over25'] = (p >= .5).astype(int)
        salida['acierto'] = (salida.prediccion_over25 == yt).astype(int)
        salida['seleccionado_cv'] = int(nombre == elegido)
        predicciones.append(salida)
        for liga in ['Todas'] + sorted(test.liga.unique()):
            mask = np.ones(len(test), dtype=bool) if liga == 'Todas' else test.liga.eq(liga).to_numpy()
            registros.append(dict(modelo=nombre, liga=liga, temporada='2025-26', **metricas(yt[mask], p[mask])))
    resultados = pd.DataFrame(registros)
    base = resultados[resultados.modelo.eq(NOMBRES[0])].set_index('liga')
    for m in ['accuracy', 'roc_auc', 'log_loss']:
        resultados[f'delta_{m}_vs_base'] = resultados[m] - resultados.liga.map(base[m])
    guardar(resultados, 'metricas.csv')
    guardar(pd.concat(predicciones, ignore_index=True), 'predicciones_prueba.csv')
    guardar(pd.DataFrame(cv_filas), 'resultados_cv.csv')
    guardar(pd.DataFrame(auditoria), 'validacion_temporal.csv')

    futuros = pd.read_csv(CLEAN/'dataset_fixtures_features.csv')
    aptos = futuros.historial_suficiente.eq(1)
    assert len(futuros) == 70 and (~aptos).sum() == 19
    salida = futuros[['id_partido', 'liga', 'temporada', 'fecha', 'jornada', 'local', 'visitante',
                      'historial_suficiente', 'motivo_exclusion']].copy()
    salida['modelo'] = elegido
    salida['estado_prediccion'] = np.where(aptos, 'con predicción', 'sin predicción')
    salida['probabilidad_over25'] = np.nan
    salida['prediccion_over25'] = pd.Series(pd.NA, index=salida.index, dtype='Int64')
    p = ajustados[elegido].predict_proba(futuros.loc[aptos, columnas])[:, 1]
    salida.loc[aptos, 'probabilidad_over25'] = p
    salida.loc[aptos, 'prediccion_over25'] = (p >= .5).astype(int)
    assert salida.loc[~aptos, ['probabilidad_over25', 'prediccion_over25']].isna().all().all()
    guardar(salida, 'predicciones_fixtures.csv')

    # Importancia en validación interna final, con un estimador que NO vio esas filas.
    # Permutación individual: correlación entre ventanas puede repartir la importancia.
    importancia = []
    ia, ib = folds[-1]
    for nombre in NOMBRES[1:]:
        est = clone(ajustados[nombre]).fit(X.iloc[ia], y.iloc[ia])
        imp = permutation_importance(est, X.iloc[ib], y.iloc[ib], scoring='neg_log_loss',
                                     n_repeats=8, random_state=SEMILLA, n_jobs=1)
        for col, media, desv in zip(columnas, imp.importances_mean, imp.importances_std):
            importancia.append(dict(modelo=nombre, variable=col, aumento_log_loss=media,
                                    desviacion=desv, poblacion='último fold interno', n=len(ib)))
    guardar(pd.DataFrame(importancia), 'importancia_variables.csv')

    # Auditoría específica de cualquier accuracy >66%, incluso por liga.
    altos = resultados[resultados.accuracy.gt(.66)]
    controles = []
    for nombre in altos.modelo.unique():
        est = clone(ajustados[nombre])
        y_mezclado = np.random.default_rng(SEMILLA).permutation(y.to_numpy())
        est.fit(X, y_mezclado)
        pp = est.predict_proba(Xt)[:, 1]
        controles.append(dict(modelo=nombre, control_etiquetas_permutadas=metricas(yt, pp)))

    MODELOS.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(modelos=ajustados, seleccionado=elegido, columnas=columnas,
                     semilla=SEMILLA, temporadas_train=['2023-24', '2024-25']), MODELOS/'modelo.joblib')
    info = dict(fase='fase4_completa', seleccionado=elegido, criterio='menor log loss media en cuatro folds temporales; ROC-AUC desempata',
                train=len(train), test=len(test), fixtures=len(futuros), fixtures_sin_prediccion=int((~aptos).sum()),
                comparacion_cv=resumen, umbral=.5, variables=columnas,
                entrenamiento_hasta=train.fecha.max(), prueba_desde=test.fecha.min(),
                hash_dataset=hashlib.sha256((CLEAN/'dataset_modelo.csv').read_bytes()).hexdigest(),
                auditoria=dict(verificacion_features=meta.get('verificacion'), fechas_estrictas=True,
                               preprocesamiento_dentro_de_fold=True, seleccion_sin_test=True,
                               columnas_prohibidas_excluidas=True, casos_accuracy_mayor_66=altos.to_dict('records'),
                               controles_permutados=controles),
                limitaciones=['Test no se usa para ajustar, calibrar ni seleccionar; umbral fijo 0.5.',
                              'Fixtures usan historia hasta 2025-26 y modelo entrenado únicamente con 2023-24/2024-25.',
                              'Modelo Over/Under académico; no incluye lesiones ni alineaciones.',
                              'Importancias correlacionadas no son causales; validación interna final, ocho repeticiones.'],
                versiones={p: version(p) for p in ['numpy', 'pandas', 'scikit-learn', 'xgboost', 'matplotlib', 'seaborn', 'joblib']},
                python=platform.python_version(), backup_eliminado=not (RAIZ/'data/_backup_raw').exists())
    (CLEAN/'metadatos_modelado.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(seleccionado=elegido, test=resultados[resultados.liga.eq('Todas')][['modelo','accuracy','roc_auc','log_loss']].to_dict('records')), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
