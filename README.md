# Cuándo hace falta leer las imágenes de un PDF

Muchos PDF tienen parte del contenido dentro de imágenes: capturas de pantalla, gráficas,
tablas pegadas como foto. Un programa que lee el PDF ve el texto normal, pero lo que hay
dentro de esas imágenes no lo ve. Para leerlo hace falta OCR, que reconoce las letras en
la imagen como lo haría una persona. El problema es que el OCR es lento, y pasarlo por
todas las páginas sale caro.

En este proyecto medí en qué páginas merece la pena usarlo y qué cambia después en un
asistente de IA que responde preguntas sobre esos documentos (lo que se suele llamar un
RAG). Lo probé con 2.382 páginas de 13 documentos públicos.

Lo que salió:

- Que haga falta OCR no depende del tipo de documento, sino de cómo se fabricó el PDF.
  En un informe maquetado no aporta nada. En unas diapositivas de clase llenas de
  capturas, sí.
- Bastan tres comprobaciones sencillas para elegir las páginas: que tengan poco texto,
  que no estén en blanco y que tengan alguna imagen. Con eso se encuentran las mismas
  páginas útiles que con la regla habitual, pasando el OCR 12 veces menos.
- Sin OCR, el asistente encuentra la diapositiva correcta (por el título), pero no la
  respuesta, que está en la imagen. Con OCR, la respuesta le llega en 7 de 8 preguntas,
  frente a 1 de 8 sin él.

El resto del documento entra en detalle. Algunos términos que aparecen:

| Término | Qué es |
|---|---|
| Texto nativo | El texto que el PDF ya trae y que se puede copiar y pegar |
| OCR | Reconocer el texto que hay dentro de una imagen |
| Fragmento | Trozo de unas 180 palabras en el que se divide cada página para buscar en él |
| Buscador | La parte que, dada una pregunta, encuentra los fragmentos más parecidos |
| LLM | El modelo de lenguaje que redacta la respuesta a partir de esos fragmentos |

## 1. La regla de los caracteres

La regla habitual es "si la página tiene menos de N caracteres de texto nativo, pásale
OCR". Con distintos valores de N sobre las mismas páginas:

| Regla | Páginas a OCR | % del total | En blanco | Con mejora medida | Páginas medidas | Acierto sobre lo medido |
|---|---:|---:|---:|---:|---:|---:|
| menos de 10 caracteres | 11 | 0,5 % | 8 | 1 de 3 | 27 % | 33 % |
| menos de 80 caracteres | 48 | 2,0 % | 21 | 10 de 27 | 56 % | 37 % |
| menos de 1000 caracteres | 929 | 39,0 % | 21 | 26 de 109 | 12 % | 24 % |
| `medido` | 75 | 3,1 % | 0 | 26 de 75 | 100 % | 35 % |

Esos tres umbrales los tenía yo escritos en tres sitios distintos del mismo proyecto, sin
ninguna medición detrás.

La regla `medido` pide tres cosas: poco texto nativo, algo de tinta al dibujar la
página y al menos una imagen. Encuentra las mismas 26 páginas en las que el OCR aporta
algo que la regla de 1000 caracteres, pasando el OCR 12 veces menos, y no gasta tiempo en
ninguna página en blanco.

- Mirar la tinta descarta los folios vacíos. Con la regla de 10 caracteres, 8 de las 11
  páginas que van a OCR están en blanco.
- Mirar si hay imágenes evita mandar a OCR portadas con poco texto que ya se leía bien.

Ojo con la última columna: solo sé si el OCR aportó algo en las páginas a las que se lo
pasé. Con la regla de 1000 caracteres son 109 de 929; las otras 820 no se midieron, así
que el porcentaje se calcula sobre las medidas. Una versión anterior lo calculaba sobre
todas y daba un 3 % engañoso. Lo que no cambia es que las 26 páginas con mejora caen
todas dentro de las 75 de `medido`.

## 2. Lo que decide es cómo se fabricó el PDF

El mismo código sobre tres grupos de documentos:

| Documentos | Páginas | A OCR | Texto nativo → con OCR | Páginas con mejora |
|---|---:|---:|---:|---:|
| Informe del IPCC (ES) + manual de R | 217 | 2,8 % | ×1,0 | 0 |
| Manual de QGIS | 1.645 | 1,2 % | ×4,6 | 14 |
| Diapositivas de Stanford (CS224n y CS231n) | 438 | 19,2 % | ×1,6 | 12 |

En documentos generados con LaTeX o con un programa de maquetación, el OCR devuelve el
mismo texto que ya había. En manuales con capturas de pantalla y en diapositivas recupera
texto que de otra forma no existe.

![El mismo PDF leído sin OCR y con OCR](out/figuras/contraste_ocr.png)

La diapositiva 15 de la primera clase de CS224n es entera capturas de conversaciones con
ChatGPT. Sin OCR se leen 24 caracteres, solo el título. Con OCR, 1.134
(`out/yield/cs224n_l01.jsonl`), y 1.206 después de arreglar los espacios.

## 3. Qué cambia en las respuestas del asistente

Preparé ocho preguntas sobre las diapositivas cuya respuesta está dentro de una imagen:
una tabla de resultados, una gráfica de tiempos, el tamaño de un modelo... Cada una lleva
la respuesta correcta, leída en la diapositiva, y las palabras o cifras que tiene que
contener un texto para contar como acierto (`corpus/preguntas.json`).

Comparo dos versiones que solo se diferencian en las páginas que la regla manda a OCR: en
una esas páginas llevan su texto nativo y en la otra, el texto del OCR. El buscador
devuelve los 5 fragmentos más parecidos a la pregunta, y el LLM es `qwen2.5:3b`, un
modelo pequeño que funciona en el propio ordenador con Ollama. Mido tres cosas por
separado:

| | Sin OCR | Con OCR |
|---|---:|---:|
| La página correcta está entre los 5 resultados | 7/8 | 7/8 |
| Esos fragmentos contienen la respuesta | 1/8 | 7/8 |
| El LLM responde bien | 1/8 | 2/8 |
| El LLM cita la página correcta | 1/8 | 4/8 |

Sin OCR, el buscador encuentra la diapositiva igual de bien, porque el título está en el
texto nativo. Pero al modelo solo le llega el título y responde "no lo sé" en siete de
ocho preguntas. La que acierta es q04, cuya respuesta también está en el texto nativo. Si
solo hubiera mirado la primera fila, habría concluido que el OCR no sirve para nada.

Con OCR la respuesta llega en 7 de 8 casos, pero el modelo, que es pequeño, solo la
aprovecha en 2: q04 y la de DETR (q06). En q01 da bien una de las dos cifras que se
piden y se inventa la otra (toma el 12,7 de la columna de al lado). En la gráfica de
Faster R-CNN, en q05 y en q08 dice no saberlo aunque tiene el dato delante, y en q07
contesta solo con las referencias. Cita la página correcta más veces de las que acierta:
encuentra el sitio, pero no siempre lo lee bien. q03 falla en las dos versiones porque
esa diapositiva se titula "Visualizing and Understanding" y el buscador no la encuentra.

Cuando una pregunta pide comparar dos cifras, la respuesta tiene que traer las dos para
contar como acierto. El modelo no da exactamente la misma respuesta cada vez, así que
`answer_eval.py` repite cada pregunta cinco veces. Las cifras de la tabla salieron
iguales en ocho ejecuciones, cinco seguidas y tres después de reiniciar el modelo. La
primera de todas fue distinta: en q01 dio bien las dos cifras.

Son solo ocho preguntas, así que cada una cuenta un 12,5 %. No ajusté las instrucciones
del modelo para que acertara estas preguntas: son las primeras que escribí y están en
`scripts/qa_graph.py`. Las respuestas completas, con sus citas, están en
`out/rag_eval/respuestas.json`.

La primera versión de este README comparaba con otra versión que quitaba esas páginas
enteras, y de ahí salía que sin OCR no se encontraba ninguna página (0 de 8, frente a 7
de 8). Ese 0 no era una medida real, porque sin OCR las páginas existen y tienen su
título. `rag_eval.py` sigue calculando esa versión (`sin_paginas_ocr`) para poder
compararlas.

## 4. El OCR también estropea

En capturas con letra muy apretada, el OCR pierde los espacios y devuelve cosas como
`Ihopethisemailfindsyouwell`, que luego no se parece a nada al buscar.
`scripts/ocr_normalize.py` vuelve a separar las palabras usando las palabras que ya
aparecen en el texto nativo del mismo documento, con un diccionario general de respaldo.

```
antes : thisimageisthatamanisironingclothesonanironingboard
ahora : this image is that a man is ironing clothes on an ironing board
```

## 5. Un problema que esto no resuelve

Entre los documentos hay tres Gacetas de Madrid (1750, 1885 y 1936). El BOE ya les pasó
OCR hace años, así que traen texto (12.818 caracteres por página de media en la de 1885)
y ninguna regla las manda a OCR. Pero ese texto está lleno de errores:

![Texto con errores en la Gaceta de Madrid de 1750](out/figuras/capa_corrupta.png)

Las reglas de arriba miran cuánto texto hay, y aquí el problema es que está mal. Probé
dos formas rápidas de detectarlo (contar palabras muy comunes y un modelo estadístico de
letras) y las dos dijeron que el peor texto de todos era *Attention Is All You Need*,
que está perfecto: confundían inglés y vocabulario técnico con texto roto. Fue una
prueba rápida en un cuaderno aparte y ese código no está en el repo; el resto de cifras
de este README sí salen de ficheros que están aquí.

La idea que quiero probar es pasar el OCR igualmente y compararlo con el texto que ya
traía la página. Si los dos se parecen poco, uno de los dos está mal. De momento es solo
una idea, sin números.

## Cómo está montado

Cada página pasa por un grafo de LangGraph (`scripts/ingest_graph.py`) que decide qué
hacer con ella:

```
texto nativo ─┬─ página en blanco ─→ se descarta (EMPTY)
              ├─ no hace falta OCR ─→ se queda el texto nativo (PLUMBER)
              └─ hace falta OCR ────→ OCR, y se queda con el que tenga más texto (OCR o PLUMBER)
```

Las preguntas pasan por otro grafo (`scripts/qa_graph.py`) con tres pasos: buscar los
fragmentos (con LangChain), pedirle la respuesta al modelo y traducir cada referencia
`[n]` de la respuesta al documento, la página y el método del que salió. Así se puede ver
si un dato vino del texto nativo o del OCR.

El modelo se cambia con la variable `RAG_MODEL` (por defecto `ollama:qwen2.5:3b`). Se
pueden usar otros proveedores, pero las cifras de arriba son solo las de ese modelo.

## Cómo reproducirlo

```bash
pip install -r requirements.txt
python scripts/fetch_corpus.py                 # descarga los 13 PDF y guarda sus huellas

for d in cs224n_l01 cs224n_l08 cs231n_l5 cs231n_l9 cs231n_l11; do
  python scripts/page_profile.py --pdf data/pdf/$d.pdf --doc-id $d --out out/slides/$d.jsonl
  python scripts/extract_corpus.py --pdf data/pdf/$d.pdf --profile out/slides/$d.jsonl \
         --out out/pages/$d.jsonl
done

python scripts/triage.py --profiles "out/profiles/*.jsonl" "out/slides/*.jsonl" \
       --yield-files "out/yield/*.jsonl" "out/yield_oficial/*.jsonl"
python scripts/rag_eval.py                     # página correcta y respuesta en los fragmentos

ollama pull qwen2.5:3b                         # con `ollama serve` en marcha
python scripts/answer_eval.py                  # respuestas del modelo
```

Las cifras de la sección 3 se midieron con Ollama 0.33.3 en un portátil con una RTX
5080; cada respuesta tarda menos de medio segundo.

Los PDF no se suben al repo porque pertenecen a sus autores; aquí solo se usan para
medir. `fetch_corpus.py` los descarga de su web original y guarda una huella (SHA-256)
de cada uno para comprobar que son los mismos.

## Los scripts

| Script | Qué hace |
|---|---|
| `fetch_corpus.py` | Descarga los documentos y guarda sus huellas |
| `page_profile.py` | Mide cada página: caracteres, imágenes, tinta y calidad del texto |
| `triage.py` | Compara las reglas para decidir qué páginas pasar por OCR |
| `threshold_sweep.py` | Prueba distintos umbrales de caracteres y cuenta las páginas en blanco |
| `ocr_yield.py` | Mide cuánto texto añade el OCR en cada página |
| `ocr_utils.py` | Funciones comunes del OCR: dibujar la página, ordenar el texto, confianza |
| `ocr_normalize.py` | Vuelve a separar las palabras que el OCR junta |
| `ingest_graph.py` | Grafo que decide qué hacer con cada página (LangGraph) |
| `extract_corpus.py` | Pasa cada página por ese grafo y guarda el texto y de dónde salió |
| `rag_eval.py` | Mide si se encuentra la página y si los fragmentos traen la respuesta |
| `qa_graph.py` | Grafo de pregunta y respuesta: buscar, responder y citar |
| `answer_eval.py` | Mide las respuestas del modelo con y sin OCR |

## Documentos

13 documentos públicos, 2.382 páginas, agrupados por cómo se fabricaron:

- Maquetados: informe de síntesis del IPCC AR4 (ES), Constitución Española (BOE),
  *Attention Is All You Need* y *An Introduction to R*.
- Manual con capturas: QGIS 3.40 Desktop User Guide.
- Con un OCR antiguo ya hecho: Gaceta de Madrid de 1750, 1885 y 1936.
- Diapositivas: Stanford CS224n clases 1 y 8 y CS231n clases 5, 9 y 11.

Las direcciones exactas están en `corpus/corpus.json`.
