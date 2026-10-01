---
name: 4geeks-progress
description: Resumen de progreso de Juan en 4Geeks: estadísticas globales de tareas (aprobadas, en revisión, pendientes) y cohortes activas. Usar cuando pregunta qué tanto avanza en el curso, su progreso general, o estadísticas de su cuenta.
---

# Skill 4 — Resumen de progreso (4Geeks)

Genera el resumen de avance de Juan calculado a partir de las tareas de la API de BreatheCode, más el listado de cohortes activas.

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (ver Skill 1 para autenticación)
- **Endpoint principal:** `GET /v1/assignment/user/me/task?limit=50&offset=<n>` (sin filtros — todas las tareas)

## Paso 1 — Autenticar (requerido)

Seguir la Skill 1 (`4geeks-auth`).

## Paso 2 — Obtener todas las tareas (paginado)

Mismo patrón paginado que Skills 2 y 3, pero **sin parámetros de filtro** — se necesitan todas para las estadísticas.

## Paso 3 — Calcular estadísticas

Agregaciones sobre la lista completa:

| Métrica | Cálculo |
|---|---|
| Total | `len(all_tasks)` |
| Entregadas | `task_status == "DONE"` |
| Aprobadas | `DONE` + `revision_status == "APPROVED"` |
| En revisión | `DONE` + `revision_status == "PENDING"` |
| Pendientes | `task_status == "PENDING"` |
| Por tipo | conteo de `task_type` (EXERCISE / PROJECT / LESSON) |

Tasa de aprobación = aprobadas / total. Tasa de entrega = entregadas / total.

## Paso 4 — Cohortes activas

`GET /v1/admissions/academy/cohort/me?academy=<academy_id>`

El `academy_id` se obtiene de `GET /v1/admissions/user/me` — cazar el objeto `academy.id` anidado (en sep 2026: ids 5 y 6; el 5 es "4Geeks Santiago" y el 6 devuelve lista vacía). El endpoint `/v1/admissions/academy/cohort/me` **sin** el param `academy` devuelve 403 ("Missing academy_id parameter").

Cohortes con `educational_status == "ACTIVE"` = cursos en curso actualmente.

## Paso 5 — Reportar

Resumen con: total tareas, aprobadas, en revisión, pendientes, tasas, desglose por tipo y lista de cohortes activas.

## Datos de referencia (sep 2026)

- 200 tareas: 116 entregadas (95 aprobadas, 21 en revisión), 84 pendientes
- Por tipo: 136 EXERCISE, 35 PROJECT, 29 LESSON
- 27 cohortes en cuenta, 24 activas

## Notas

- **`GET /v1/activity/me` devuelve 403** ("don't have capability read_activity") con token de estudiante — no usar; el progreso se calcula desde las tareas.
- El cálculo se hace en el cliente (agregación Python) porque la API no expone un endpoint de resumen.
