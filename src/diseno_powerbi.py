"""Genera tema validado, banners vectoriales y PNG. No modifica el PBIX.

El esquema oficial se descarga como recurso temporal de validación, fuera de
las salidas. Ejecutar con --schema RUTA al esquema de Microsoft Draft 7.
"""
import argparse
import json
from pathlib import Path
from html import escape
from jsonschema import Draft7Validator
from config import RAIZ

DESTINO=RAIZ/'powerbi/diseno'
FONDO='#080F1B'; PANEL='#111E30'; BORDE='#293B52'
TEXTO='#F3F7FC'; SECUNDARIO='#A9B8CC'; MENTA='#35D9B0'
PALETA=[MENTA,'#54AAFF','#B69CFF','#FFCB66','#FF7D89','#5DDBE6','#91A5BF','#E99ADB']


def color(hexadecimal):
    return {'solid':{'color':hexadecimal}}


def construir_tema():
    tema={'name':'Over 2.5 · Night Match', 'dataColors':PALETA,
          'background':PANEL,'foreground':TEXTO,'tableAccent':MENTA,
          'foregroundNeutralSecondary':SECUNDARIO,'foregroundNeutralTertiary':'#6F829B',
          'backgroundLight':BORDE,'backgroundNeutral':'#182A40',
          'good':MENTA,'neutral':'#FFCB66','bad':'#FF7D89',
          'textClasses':{k:{'fontFace':'Segoe UI','fontSize':tam,'color':col}
                        for k,tam,col in [('title',14,TEXTO),('label',11,SECUNDARIO),
                                          ('callout',28,TEXTO),('header',12,TEXTO)]}}
    globales={'background':[{'color':color(PANEL),'transparency':0}],
              'border':[{'show':True,'color':color(BORDE),'radius':10}],
              'title':[{'show':True,'fontColor':color(TEXTO),'fontSize':13,'fontFamily':'Segoe UI','alignment':'left'}],
              'visualHeader':[{'foreground':color(SECUNDARIO),'background':color(PANEL)}]}
    estilos={'*':{'*':globales},'page':{'*':{
        'background':[{'color':color(FONDO),'transparency':0}],
        'outspace':[{'color':color('#050A12'),'transparency':0}]}}}
    cabecera={'fontColor':color(TEXTO),'backColor':color('#1B3048'),'fontFamily':'Segoe UI','fontSize':11,'bold':True,'wordWrap':True}
    valores={'fontColorPrimary':color(TEXTO),'fontColorSecondary':color(TEXTO),
             'backColorPrimary':color(PANEL),'backColorSecondary':color('#16263B'),
             'fontFamily':'Segoe UI','fontSize':10,'wordWrap':False}
    rejilla={'gridVertical':False,'gridHorizontal':True,'gridHorizontalColor':color(BORDE),'rowPadding':5}
    estilos['tableEx']={'*':{'columnHeaders':[cabecera],'values':[valores],'grid':[rejilla],
                            'total':[{'fontColor':color(TEXTO),'backColor':color('#1B3048'),'fontSize':10}]}}
    estilos['pivotTable']={'*':{'columnHeaders':[cabecera],
            'rowHeaders':[{'fontColor':color(TEXTO),'backColor':color('#1B3048'),'fontSize':11}],
            'values':[valores],'grid':[rejilla]}}
    estilos['card']={'*':{'title':[{'show':False}],'labels':[{'color':color(TEXTO),'fontSize':28,'fontFamily':'Segoe UI'}],
                         'categoryLabels':[{'color':color(SECUNDARIO),'fontSize':11,'fontFamily':'Segoe UI'}]}}
    estilos['cardVisual']={'*':{'title':[{'show':False}],'value':[{'$id':'default','fontColor':color(TEXTO),'fontSize':28,'fontFamily':'Segoe UI','labelDisplayUnits':0}],
                               'label':[{'$id':'default','fontColor':color(SECUNDARIO),'fontSize':11,'fontFamily':'Segoe UI'}],
                               'fillCustom':[{'$id':'default','show':True,'fillColor':color(PANEL),'transparency':0}],
                               'outline':[{'$id':'default','show':False}]}}
    estilos['slicer']={'*':{'title':[{'show':False}],'header':[{'fontColor':color(SECUNDARIO),'background':color(PANEL),'textSize':10,'fontFamily':'Segoe UI'}],
                           'items':[{'fontColor':color(TEXTO),'background':color(PANEL),'textSize':11,'fontFamily':'Segoe UI'}]}}
    for tipo in ['clusteredBarChart','barChart','clusteredColumnChart','columnChart','lineChart']:
        estilos[tipo]={'*':{
            'categoryAxis':[{'labelColor':color(SECUNDARIO),'titleColor':color(SECUNDARIO),'fontSize':10,'fontFamily':'Segoe UI'}],
            'valueAxis':[{'labelColor':color(SECUNDARIO),'titleColor':color(SECUNDARIO),'fontSize':10,
                          'gridlineColor':color(BORDE),'gridlineShow':True}],
            'labels':[{'color':color(TEXTO),'fontSize':10,'fontFamily':'Segoe UI'}],
            'legend':[{'labelColor':color(SECUNDARIO),'fontSize':10,'fontFamily':'Segoe UI'}]}}
    tema['visualStyles']=estilos
    return tema


def svg_base(w,h,contenido):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="g"><stop stop-color="#0D1A2A"/><stop offset="1" stop-color="#14283C"/></linearGradient></defs>{contenido}</svg>'


def banners():
    superior=svg_base(1280,90,'''<rect width="1280" height="90" fill="url(#g)"/>
<path d="M0 88H1280" stroke="#293B52" stroke-width="2"/>
<rect x="24" y="22" width="48" height="46" rx="12" fill="#35D9B0"/>
<path d="M37 54V39h22v15z M48 39v15 M45 46h6" fill="none" stroke="#08241E" stroke-width="2"/>
<text x="88" y="42" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="27" font-weight="700">OVER 2.5</text>
<text x="89" y="63" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="12" letter-spacing="2">ANÁLISIS DE GOLES · PYTHON + POWER BI</text>
<path d="M395 24v42" stroke="#293B52"/>
<text x="420" y="40" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="15">Premier League · LaLiga · Bundesliga</text>
<text x="420" y="61" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="12">Historia 2023–26 · Evaluación temporal · Probabilidades Over / Under</text>
<g transform="translate(1030,13)" fill="none" stroke="#35D9B0" opacity="0.28"><rect width="144" height="64" rx="3"/><path d="M72 0v64M0 17h22v30H0m144-30h-22v30h22"/><circle cx="72" cy="32" r="14"/></g>
<path d="M1166 65l17-19 18 8 20-28 25 8" fill="none" stroke="#54AAFF" stroke-width="3"/>
<circle cx="1221" cy="26" r="4" fill="#35D9B0"/>''')
    lateral=svg_base(200,630,'''<rect width="200" height="630" fill="#0B1523"/>
<path d="M199 0v630" stroke="#293B52"/>
<text x="18" y="32" fill="#35D9B0" font-family="Segoe UI,Arial" font-size="10" letter-spacing="1">PROYECTO ACADÉMICO</text>
<text x="18" y="71" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="26" font-weight="700">FÚTBOL</text>
<text x="18" y="102" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="26" font-weight="700">EN DATOS</text>
<path d="M18 125h44" stroke="#35D9B0" stroke-width="3"/>
<text x="18" y="158" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="10" letter-spacing="2">EXPLORAR INFORME</text>
<path d="M18 392h164" stroke="#293B52"/>
<text x="18" y="423" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="10">FUENTE</text>
<text x="18" y="444" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="14">Flashscore</text>
<text x="18" y="481" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="10">PRUEBA DEL MODELO</text>
<text x="18" y="502" fill="#F3F7FC" font-family="Segoe UI,Arial" font-size="14">Temporada 2025–26</text>
<text x="18" y="539" fill="#A9B8CC" font-family="Segoe UI,Arial" font-size="10">CORTE DE FIXTURES</text>
<text x="18" y="560" fill="#FFCB66" font-family="Segoe UI,Arial" font-size="14">17 OCT 2026</text>
<text x="18" y="604" fill="#6F829B" font-family="Segoe UI,Arial" font-size="10">Over ≥ 3 goles · Under ≤ 2</text>''')
    return {'banner_superior':(1280,90,superior),'banner_lateral':(200,630,lateral)}


def maqueta():
    import csv
    with (RAIZ/'data/clean/metricas.csv').open(encoding='utf-8-sig',newline='') as f:
        datos={r['modelo']:r for r in csv.DictReader(f) if r['liga']=='Todas'}
    rf,base=datos['Random Forest'],datos['Línea base']
    partes=[f'<rect width="1280" height="720" fill="{FONDO}"/>',banners()['banner_superior'][2],
            banners()['banner_lateral'][2].replace('<svg ','<svg x="0" y="90" ',1)]
    def text(x,y,t,size=12,col=TEXTO,bold=False):
        return f'<text x="{x}" y="{y}" fill="{col}" font-family="Segoe UI,Arial" font-size="{size}" font-weight="{700 if bold else 400}">{escape(str(t))}</text>'
    def panel(x,y,w,h):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PANEL}" stroke="{BORDE}"/>'
    for i,t in enumerate(['01  Resumen','02  Modelos','03  Equipos','04  Próximos']):
        y=270+i*46
        partes.append(f'<rect x="14" y="{y}" width="172" height="38" rx="7" fill="{"#183C3B" if i==0 else PANEL}"/>')
        partes.append(text(28,y+24,t,12,MENTA if i==0 else SECUNDARIO))
    for x,w,label,valor in [(220,508,'MODELO','Random Forest'),(744,516,'TEMPORADA DE PRUEBA','2025–26')]:
        partes.extend([panel(x,110,w,48),text(x+14,128,label,9,SECUNDARIO),text(x+14,148,valor,13),text(x+w-24,142,'⌄',15,SECUNDARIO)])
    n=int(rf['n']); aciertos=int(rf['tn'])+int(rf['tp'])
    for x,label,valor,col in [(220,'Partidos evaluados',f'{n:,}'.replace(',','.'),TEXTO),(572,'Predicciones correctas',str(aciertos),MENTA),(924,'Predicciones incorrectas',str(n-aciertos),'#FF7D89')]:
        partes.extend([panel(x,174,336,68),text(x+16,196,label,11,SECUNDARIO),text(x+16,226,valor,25,col,True)])
    def numero(v,pct=False):
        return (f'{v*100:.2f}%' if pct else f'{v:.4f}').replace('.',',')
    filas=[(258,'ROC-AUC',float(rf['roc_auc']),float(base['roc_auc']),False),
           (400,'Log loss',float(rf['log_loss']),float(base['log_loss']),False),
           (542,'Exactitud',float(rf['accuracy']),float(base['accuracy']),True)]
    for y,label,valor,referencia,pct in filas:
        delta=(referencia-valor) if label=='Log loss' else (valor-referencia)
        vd=(f'{delta*100:+.2f} pp' if pct else f'{delta:+.4f}').replace('.',',')
        for x,t,v,col in [(220,label+' · modelo',numero(valor,pct),TEXTO),(572,label+' · línea base',numero(referencia,pct),SECUNDARIO),
                          (924,'Mejora en log loss' if label=='Log loss' else 'Cambio de '+label,vd,MENTA if delta>=0 else '#FF7D89')]:
            partes.extend([panel(x,y,336,126),text(x+18,y+29,t,12,SECUNDARIO),text(x+18,y+82,v,34,col,True)])
    partes.append(text(220,699,'Maqueta de diseño · Datos reales de prueba · Mejora probabilística modesta, sin mejora de exactitud',10,SECUNDARIO))
    return svg_base(1280,720,''.join(partes))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--schema',required=True); args=parser.parse_args()
    esquema=json.loads(Path(args.schema).read_text(encoding='utf-8-sig'))
    tema=construir_tema()
    errores=sorted(Draft7Validator(esquema).iter_errors(tema),key=lambda e:str(e.path))
    if errores:
        for e in errores[:20]:print('/'.join(map(str,e.path)),e.message[:500])
        raise SystemExit('Tema no válido contra el esquema oficial.')
    DESTINO.mkdir(parents=True,exist_ok=True)
    (DESTINO/'tema_over25.json').write_text(json.dumps(tema,ensure_ascii=False,indent=2),encoding='utf-8')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        for nombre,(w,h,svg) in banners().items():
            (DESTINO/(nombre+'.svg')).write_text(svg,encoding='utf-8')
            page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
            page.set_content('<html><body style="margin:0">'+svg+'</body></html>')
            page.screenshot(path=str(DESTINO/(nombre+'.png')))
            page.close()
        page=browser.new_page(viewport={'width':1280,'height':720},device_scale_factor=1)
        page.set_content('<html><body style="margin:0">'+maqueta()+'</body></html>')
        page.screenshot(path=str(DESTINO/'maqueta_resumen.png'))
        page.close()
        browser.close()
    print('Tema válido contra Microsoft 2.157; dos banners SVG y PNG con dimensiones exactas.')


if __name__=='__main__':main()
