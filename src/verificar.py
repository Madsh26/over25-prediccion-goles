"""Verifica las salidas de Fase 3 con datos reales, sin red ni archivos nuevos."""
from collections import defaultdict
from datetime import date
from statistics import mean
import json
import math
from config import RAIZ
from extraccion import leer


def main():
    carpeta=RAIZ/'data/clean'
    historial=leer(carpeta/'datos_limpios.csv')
    modelo=leer(carpeta/'dataset_modelo.csv')
    fixtures=leer(carpeta/'dataset_fixtures_features.csv')
    excluidos=leer(carpeta/'filas_sin_historial.csv')
    auditoria=leer(carpeta/'auditoria_temporal.csv')
    meta=json.loads((carpeta/'metadatos_modelo.json').read_text(encoding='utf-8'))
    assert len(historial)==3198
    assert len(modelo)+len(excluidos)==len(historial)
    ids_modelo={r['id_partido'] for r in modelo}
    ids_excluidos={r['id_partido'] for r in excluidos}
    assert not ids_modelo & ids_excluidos
    assert ids_modelo | ids_excluidos == {r['id_partido'] for r in historial}
    assert len({r['id_partido'] for r in modelo})==len(modelo)
    assert not {'over25','goles_local','goles_visitante','total_goles'} & set(meta['features_numericas'])
    assert len(auditoria)==len(historial)+len(fixtures)
    for jornadas in meta['jornadas_fixtures_seleccionadas'].values():
        assert len(jornadas)<=3 and jornadas==list(range(jornadas[0],jornadas[0]+len(jornadas)))
    for r in auditoria:
        for lado in ('local','visitante'):
            assert not r[f'ultima_fecha_{lado}'] or r[f'ultima_fecha_{lado}']<r['fecha']
    for r in fixtures:
        assert r['over25']==''
        assert int(r['jornada']) in meta['jornadas_fixtures_seleccionadas'][r['liga']]
    equipos=defaultdict(list)
    for r in historial:
        for lado,opuesto in (('local','visitante'),('visitante','local')):
            equipos[(r['liga'],r[lado])].append({'fecha':r['fecha'],
             'gf':int(r[f'goles_{lado}']),'gc':int(r[f'goles_{opuesto}'])})
    for h in equipos.values():
        h.sort(key=lambda x:x['fecha'])
    # Recalcular cada media de goles de cada fila: no depende del algoritmo
    # incremental y detecta off-by-one o inclusión del encuentro actual.
    for r in modelo:
        assert r['over25'] in ('0','1') and r['historial_suficiente']=='1'
        assert all(r[c] not in ('',None) and math.isfinite(float(r[c])) for c in meta['features_numericas'])
        for lado in ('local','visitante'):
            anteriores=[x for x in equipos[(r['liga'],r[lado])] if x['fecha']<r['fecha']]
            assert len(anteriores)>=10
            for ventana in (5,10):
                for c in ('gf','gc'):
                    esperado=mean(x[c] for x in anteriores[-ventana:])
                    assert abs(float(r[f'{lado}_general_{ventana}_{c}'])-esperado)<1e-5
    meta['verificacion']='OK: partición completa de 3198 resultados, variables numéricas finitas y medias previas de goles recalculadas para todas las filas; auditoría de fechas estrictamente anteriores.'
    (carpeta/'metadatos_modelo.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Verificación OK: {len(modelo)} filas; medias previas recalculadas y auditoría temporal estricta.')


if __name__=='__main__':
    main()
