"""Verificación de entregables: mismo test, métricas reproducibles y exclusiones."""
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from config import RAIZ
from modelo import CLEAN, MODELOS, NOMBRES, metricas


def main():
    info = json.loads((CLEAN/'metadatos_modelado.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((CLEAN/'dataset_modelo.csv').read_bytes()).hexdigest() == info['hash_dataset']
    modelos = joblib.load(MODELOS/'modelo.joblib')
    datos = pd.read_csv(CLEAN/'dataset_modelo.csv')
    test = datos[datos.temporada.eq('2025-26')].sort_values(['fecha','id_partido'])
    pred = pd.read_csv(CLEAN/'predicciones_prueba.csv')
    m = pd.read_csv(CLEAN/'metricas.csv')
    assert set(pred.modelo) == set(NOMBRES) and len(pred) == 4*len(test)
    assert not pred.duplicated(['id_partido','modelo']).any()
    for nombre in NOMBRES:
        t = pred[pred.modelo.eq(nombre)].set_index('id_partido').loc[test.id_partido]
        assert set(t.index) == set(test.id_partido)
        p = modelos['modelos'][nombre].predict_proba(test[modelos['columnas']])[:,1]
        np.testing.assert_allclose(p, t.probabilidad_over25, atol=1e-9)
        np.testing.assert_array_equal(test.over25, t.over25)
        for liga in ['Todas']+sorted(test.liga.unique()):
            mask = np.ones(len(test),bool) if liga=='Todas' else test.liga.eq(liga).to_numpy()
            r = m[m.modelo.eq(nombre)&m.liga.eq(liga)].iloc[0]
            esperado = metricas(test.over25.to_numpy()[mask],p[mask])
            for campo,valor in esperado.items():
                np.testing.assert_allclose(r[campo],valor,atol=1e-8)
            assert r.tn+r.fp+r.fn+r.tp==r.n
    futuros = pd.read_csv(CLEAN/'predicciones_fixtures.csv')
    sin = futuros.estado_prediccion.eq('sin predicción')
    assert len(futuros)==70 and sin.sum()==19
    assert futuros.loc[sin,['probabilidad_over25','prediccion_over25']].isna().all().all()
    assert futuros.loc[~sin,'probabilidad_over25'].between(0,1).all()
    originales = pd.read_csv(CLEAN/'dataset_fixtures_features.csv').set_index('id_partido')
    aptos = futuros.loc[~sin]
    p = modelos['modelos'][modelos['seleccionado']].predict_proba(originales.loc[aptos.id_partido,modelos['columnas']])[:,1]
    np.testing.assert_allclose(p,aptos.probabilidad_over25,atol=1e-9)
    folds = pd.read_csv(CLEAN/'validacion_temporal.csv')
    assert len(folds)==4 and (folds.fecha_max_train < folds.fecha_min_validacion).all()
    assert len(list((RAIZ/'graficas').glob('*.png')))==8
    info['verificacion_entregables']='OK: artefacto recargado; probabilidades y todas las métricas reproducidas; 70 fixtures, 19 vacíos; dataset aprobado intacto; ocho PNG.'
    (CLEAN/'metadatos_modelado.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(info['verificacion_entregables'])


if __name__=='__main__':
    main()
