---
name: 4geeks-task-detail
description: Obtener el detalle de una tarea de 4Geeks con el feedback del revisor, fechas y URLs de entrega. Usar cuando Juan pregunta qué le dijo el revisor, cuándo entregó algo, o quiere ver el estado detallado de una tarea concreta.
---

# Skill 6 — Detalle de tarea con feedback (4Geeks)

Recupera el detalle completo de una tarea de Juan: feedback del revisor, fechas de entrega/revisión, URLs del repo y cohort.

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (ver Skill 1 para autenticación)
- **Endpoint:** `GET /v1/assignment/task/{task_id}`

## Paso 1 — Autenticar (requerido)

Seguir el flujo de la Skill 1 (`4geeks-auth`).

## Paso 2 — Resolver el task_id

Si Juan da un ID numérico directo, usarlo. Los IDs son números grandes (ej. 955197); un ID pequeño como "4" devuelve 404.

Si Juan da un **título**, buscar el ID en la sesión activa (la lista de proyectos de la Skill 2 ya contiene los IDs) o hacer `GET /v1/assignment/user/me/task?limit=50&offset=N` (paginado) y filtrar por `title`.

## Paso 3 — Obtener el detalle

```bash
curl -s -H "Authorization: Token ***" \
  "https://breathecode.herokuapp.com/v1/assignment/task/{task_id}"
```

## Campos del response

| Campo | Contenido |
|---|---|
| `description` | **Feedback del revisor** (texto libre, ej. "Excelente trabajo! Responsive y super limpio!") |
| `task_status` / `revision_status` | Estado (DONE/APPROVED, DONE/PENDING, etc.) |
| `delivered_at` | Fecha de entrega |
| `reviewed_at` | Fecha de revisión |
| `github_url` / `live_url` | URLs de entrega |
| `cohort.name` | Cohort al que pertenece |
| `opened_at` / `read_at` | Cuándo se abrió/leyó |

## Criterio de éxito

Detalle completo con título, estado, feedback del revisor (o indicación de que aún no hay revisión), fechas y URLs.

## Notas

- Respuesta 404 = task_id inexistente; avisar y ofrecer buscar por título.
- Algunas tareas en revisión tienen `description: ""` y `reviewed_at: null` — reportar "aún sin feedback".
- Ejemplo verificado: id=955197 → "A simple Dashboard with Tailwind CSS", DONE+APPROVED, feedback "Excelente trabajo! Responsive y super limpio!\n\n-A", entregado 2026-07-24, revisado 2026-08-01.
