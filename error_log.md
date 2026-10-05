# error_log.md — Noticias diarias de IA (noticias-ia)

Log de errores del skill `noticias-ia`: recopila noticias de Wired y El País y las escribe en el Google Doc **Noticias diarias de IA** vía la Google Drive API (service account, sin Zapier). Cada automatización corre a las 09:00 y 21:00 (Europe/Madrid).

---

## Estado actual (2026-10-03 08:10 UTC) — INCIDENTE CERRADO

- **Resolución**: verificación manual el 03-10 ~08:07 UTC mostró credenciales sanas (token emitido OK, GET de metadatos del doc → http 200). Los 401 fueron **transitorios**; la clave de la service account no estaba deshabilitada ni expirada.
- **Publicación recuperada**: 03-10 10:11 (Europe/Madrid), modo "nuevo día", 5 noticias nuevas (Wired 2, El País 3) subidas con http 200.
- El doc vuelve a estar actualizado; la automatización de las 21:00 debe operar con normalidad.
- Recomendación de seguimiento: si los 401 transitorios se repiten, considerar reintentos con backoff en el paso 5 del skill (regenerar token y esperar antes de reintentar, en vez de fallar al instante).

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
