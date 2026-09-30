---
name: 4geeks-pending
description: Listar el trabajo pendiente de Juan en 4Geeks (proyectos, ejercicios y lecciones sin entregar). Usar cuando pregunta qué le falta, qué tiene que hacer, o qué está pendiente.
---

# Skill 3 — Trabajo pendiente (4Geeks)

Recupera todo lo que Juan aún no ha entregado en la API de BreatheCode, agrupado por tipo.

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (ver Skill 1 para autenticación)
- **Endpoint:** `GET /v1/assignment/user/me/task?task_status=PENDING&limit=50&offset=<n>`

## Paso 1 — Autenticar (requerido)

Seguir el flujo de la Skill 1 (`4geeks-auth`).

## Paso 2 — Obtener pendientes (con paginación)

Mismo patrón paginado que la Skill 2: iterar `results` hasta que `next` sea `None`.

```python
qs = urlencode({"task_status": "PENDING", "limit": 50, "offset": offset})
GET f"{base}/v1/assignment/user/me/task?{qs}" con header Authorization
```

## Paso 3 — Agrupar por tipo

| task_type | Qué es |
|---|---|
| PROJECT | Proyectos (entregables con repo/despliegue) |
| EXERCISE | Ejercicios (práctica de conceptos) |
| LESSON | Lecciones (contenido teórico) |

Por cada ítem mostrar: `title`, `cohort.name`, `associated_slug`.

## Criterio de éxito

Tres bloques (Proyectos / Ejercicios / Lecciones) con sus títulos y cohortes. Si el total es grande, ofrecer resumen numérico + lista solo de proyectos (los más importantes) y dejar ejercicios/lecciones como conteo.

## Notas

- Conteo sep 2026: 84 pendientes (53 EXERCISE, 16 LESSON, 15 PROJECT).
- Algunos pendientes son duplicados entre cohortes (ej. spain-aie-pt-4 repite ejercicios de otras cohortes); listar tal cual para no perder contexto de cohorte.
- El proyecto "My 4Geeks Assistant" (slug: openclaw-integration) es el que se está construyendo ahora mismo — está en pendientes.
- Diferencia con Skill 2: esta skill filtra `task_status=PENDING` (sin importar tipo); la 2 filtra `task_type=PROJECT` (todos sus estados).
