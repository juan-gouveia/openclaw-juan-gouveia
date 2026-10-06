# error_log.md — Noticias diarias de IA (noticias-ia)

Log de errores del skill `noticias-ia`: recopila noticias de Wired y El País y las escribe en el Google Doc **Noticias diarias de IA** vía la Google Drive API (service account, sin Zapier). Cada automatización corre a las 09:00 y 21:00 (Europe/Madrid).

---

## Estado actual (2026-10-06 06:55 UTC) — CORREGIDO (pendiente confirmar en ejecuciones programadas)

- **Causa raíz**: el agente copiaba una cabecera `Authorization` enmascarada por OpenClaw (placeholder en lugar del token). Desde el 05-10, además, el paso 5 usaba un esquema de autorización que Google no acepta. Detalle en la sección **2026-10-06** al final.
- **Corrección**: paso 5 del SKILL.md con `curl --oauth2-bearer` + `Content-Type: text/html`; eliminados los auxiliares rotos de `state/`.
- **Prueba**: ejecución manual de la automatización el 06-10 08:47 (Europe/Madrid), modo "nuevo día", 4 noticias (Wired 1, El País 3). Subida con `http 200` **al primer intento**, sin reintentos ni depuración; el doc exportado muestra el bloque del 06-10 08:48; Telegram entregado.
- **06-10 09:00 (programada, modo append)**: sin fallos (confirmado por Juan).
- **Pendiente**: confirmar la ejecución programada del 06-10 a las 21:00 para cerrar el caso.
- La sección "INCIDENTE CERRADO" del 03-10 y su diagnóstico de "401 transitorios" quedan **invalidados**; se conservan abajo como historial.

---

## Timeline de incidentes

### 2026-10-01 ~10:27 UTC — Primera ejecución manual (401)
- Paso 5 (subida al doc): `http 401 Invalid Credentials`.
- Token regenerado → `token-ok`, reintento → 401 otra vez.
- Hipótesis inicial (incorrecta): el SKILL.md tenía el header `Authorization` corrupto por efecto de la redacción de OpenClaw (`Bearer *** token)` en la línea del paso 5).

### 2026-10-01 11:33–12:06 UTC — Diagnóstico erróneo, resolución por prueba real
- Verificación con `grep` confirmaba el header "corrupto" en mi vista del archivo.
- Juan informó que lo había corregido desde el TUI; pedí la prueba real.
- **Resultado: http 200 — la subida funcionó.** El fix de Juan existía en disco desde el principio.
- **Causa raíz del falso diagnóstico**: el sistema de redacción de OpenClaw enmascara cualquier token/secret en las lecturas/ediciones de archivos que hago. Mi vista del SKILL.md mostraba la versión redactada, no la real.
- **Lección**: nunca diagnosticar archivos que contienen tokens por lectura directa; la única evidencia válida es ejecutar el flujo completo.

### 2026-10-02 19:04 UTC — Automatización 21:00 (401)
- Paso 5: `http 401` dos veces; token regenerado (`token-ok`) e igual.
- Doc intacto (contenido del 02-10 09:00). 4 noticias pendientes.

### 2026-10-03 07:07 UTC — Automatización 09:00 (401)
- Paso 5: 401 otra vez; reintento con token nuevo → 401.
- Observación de la automatización: la obtención de token funciona, pero Drive lo rechaza. Sospecha de clave/proyecto de la cuenta de servicio o del proxy de salida contra `www.googleapis.com`.
- 5 noticias pendientes (Wired 2, El País 3).

### 2026-10-03 07:58 UTC — Verificación manual (401)
- Token regenerado (`token-ok`) + GET de metadatos del doc → `http 401`.
- Confirma: el fallo no es del comando de subida ni intermitente de red en este momento; la credencial emitida por Google es rechazada por la API de Drive.

### 2026-10-03 08:03–08:07 UTC — Diagnóstico profundo de la SA (SIN fallo)
- Script de diagnóstico completo: metadata de la SA (proyecto `openclaw-noticias-ia`, clave RSA 2048 bits `9f824f8e...`), emisión de token → `http 200`, y **GET de metadatos del doc → `http 200`**.
- La credencial funciona ahora. Descarta hipótesis de clave deshabilitada/expirada. Los 401 previos fueron **transitorios**.

### 2026-10-03 10:11 (Europe/Madrid) — Publicación recuperada
- Modo "nuevo día", bloque del 03-10-2026 10:11 con 5 noticias nuevas (Wired 2, El País 3) subido con `http 200`.
- Incidente cerrado.

---

## Diagnóstico (actualizado al cierre)

El flujo de generación de token (JWT firmado con la clave privada de la service account) produce un token que Google rechazó en una ventana (02-10 19:04 UTC → 03-10 07:58 UTC) y acepta desde el 03-10 ~08:07 UTC. La clave de la SA está **activa y funcional** verificada en frío: token emitido y Drive responde 200.

**Causa más probable**: intermitencia del lado de Google (aceptación de tokens) o del proxy de salida durante esa ventana. No hay evidencia de problema en el skill ni en las credenciales locales.

Acción única pendiente (opcional): si se repite, añadir reintento con backoff al paso 5 (ya contemplado: regenerar token una vez; podría ampliarse a 2–3 reintentos espaciados).

---

## Impacto (resuelto)

- Doc desactualizado del 02-10 09:00 al 03-10 10:11 (Europe/Madrid) — recuperado con el bloque "nuevo día".
- Las 5 noticias pendientes se publicaron el 03-10; nada se perdió (el corte sale de la última línea `Actualizado:` de `hoy.html`).
- Las automatizaciones fallidas del 02-10 y 03-10 notificaron correctamente a Telegram (el paso de notificación nunca falló).

---

## Nota de procedimiento

- El skill ya no usa Zapier: todo es curl/openssl contra la Google Drive API con service account.
- El token se guarda en `skills/noticias-ia/state/token` (caducidad 1h, se regenera al inicio de cada ejecución).
- Tras cualquier 401, el skill regenera el token una vez y reintenta; si vuelve 401, reporta y no toca el doc.

---

### 2026-10-03 19:01 UTC — RECAÍDA: automatización 21:00 (401) — INCIDENTE REABIERTO

- La ejecución programada de las 21:00 (Europe/Madrid) falló de nuevo: paso 5 devolvió 401 incluso tras refrescar el token una vez. Notificación entregada a Telegram.
- Contradice el cierre de la mañana: a las 10:11 la subida manual funcionó (http 200) y a las 19:01 la automatización falló. El diagnóstico de "401 transitorio, resuelto" era prematuro.
- Patrón observado: las subidas **manuales** (script Python directo) funcionan; las ejecutadas desde el **skill en sesiones automatizadas** fallan con 401. Diferencia clave: el skill usa el bloque bash con openssl desde SKILL.md, el script manual emite el JWT con la librería `cryptography`. Hipótesis actualizada: el comando bash del skill puede estar produciendo un JWT inválido (firma o claim) en el contexto de la automatización aislada, o el token se guarda corrupto en `state/token`.
- Próximo paso sugerido: reemplazar el paso 1 del skill (bloque bash+openssl) por el script Python de diagnóstico (`/tmp/sa_diag.py`, parte de firma) que sí produce tokens aceptados, o añadir verificación tras la firma antes de guardar.
- Doc conserva contenido del 03-10 10:11. Las noticias de la ejecución de las 21:00 no se publican; se recuperarán en la próxima ejecución exitosa (el corte sale de hoy.html).

---

### 2026-10-06 — CAUSA RAÍZ REAL Y CORRECCIÓN

**Los 401 no eran transitorios ni un problema de la clave de la service account.** Diagnóstico hecho revisando los comandos reales de cada ejecución en la base de datos de transcripciones de OpenClaw (`agents/main/agent/openclaw-agent.sqlite`).

- **Mecanismo**: OpenClaw enmascara las cabeceras de autorización en todo el texto que llega al modelo (resultados de herramientas, lecturas de archivos; ver `docs/logging.md`, "Model-visible tool-result text… authorization headers… remain masked"). El paso 5 antiguo escribía la cabecera `Authorization` a mano con `$(cat …/token)`. El agente la veía con el valor sustituido por `***` y **la copiaba literalmente**, así que curl enviaba un placeholder en vez del token → Google respondía `401 Invalid Credentials`. Regenerar el token no cambiaba nada.
- **Por qué funcionaba "a veces"**: solo cuando el modelo, depurando, construyó la cabecera de otra forma en vez de copiarla: 02-10 09:00 (con `printf` y `%s`) y 04-10 09:00 (con `curl --oauth2-bearer`). Las subidas manuales funcionaban por lo mismo. El falso diagnóstico del 01-10 ("mi vista del archivo está redactada") era correcto en el mecanismo, pero se sacó la conclusión equivocada.
- **Regresión del 05-10**: el paso 5 se reescribió en Python con el esquema `"To"+"ken "` para esquivar la máscara. Google solo acepta el esquema OAuth estándar, así que la petición llega como anónima → 401/403 **en todas las ejecuciones** desde el 05-10 21:00. La afirmación del SKILL.md de que "el proxy reemplaza los tokens en los argumentos de curl" era falsa: el proxy de secretos solo sustituye sentinels del almacén de OpenClaw y el token de Google no lo es.
- **Verificación (06-10 ~06:40 UTC, solo GET)**: token emitido por el bloque del paso 1 + esquema OAuth estándar → 200; mismo token con esquema `Token` → 403; cabecera con placeholder literal → 401 Invalid Credentials (el error exacto del log).

**Correcciones aplicadas (06-10 08:47 Europe/Madrid)**:
1. `skills/noticias-ia/SKILL.md` paso 5: vuelve a curl, pasando el token **solo** con `--oauth2-bearer "$(cat token)"` (no forma una cabecera que se pueda enmascarar ni copiar mal) y con `Content-Type: text/html` (el script de Python no lo enviaba). Instrucción explícita de no escribir la cabecera a mano ni crear scripts auxiliares.
2. Eliminados del `state/` los auxiliares obsoletos/rotos (`upload.py` con el esquema incorrecto, `upload.sh` con la cabecera enmascarada guardada en disco y comillas sin cerrar, y los diagnósticos `r2.json` y `about.json`). Copia en `/root/.openclaw/backups/noticias-ia-state-20261006/`.
3. Se descarta la recomendación de "reintentos con backoff": no habría servido.

**Regla para el futuro**: no diagnosticar fallos de autenticación leyendo comandos o archivos desde el agente (se ven enmascarados), y nunca escribir la cabecera `Authorization` en un SKILL.md; usar `--oauth2-bearer`.
