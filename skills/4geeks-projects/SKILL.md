---
name: 4geeks-projects
description: Listar los proyectos de Juan en 4Geeks con su estado (pendiente, entregado, calificado). Usar cuando pregunta por sus proyectos, qué ha entregado, o qué tiene calificado.
---

# Skill 2 — Mis proyectos (4Geeks)

Recupera los proyectos asignados a Juan en la API de BreatheCode y los muestra con su estado de entrega y revisión.

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (ver Skill 1 para autenticación)
- **Endpoint:** `GET /v1/assignment/user/me/task?task_type=PROJECT&limit=50&offset=<n>`

## Paso 1 — Autenticar (requerido)

Seguir el flujo de la Skill 1 (`4geeks-auth`) para obtener el token canjeado.

## Paso 2 — Obtener proyectos (con paginación)

La respuesta viene paginada: `{count, results, next, ...}`. Iterar hasta agotar `next`:

```python
offset = 0
while True:
    qs = urlencode({"task_type": "PROJECT", "limit": 50, "offset": offset})
    GET f"{base}/v1/assignment/user/me/task?{qs}" con header Authorization
    all_results.extend(page["results"])
    if page["next"] is None: break
    offset += len(page["results"])
```

## Paso 3 — Mapear estados

| task_status | revision_status | Estado para Juan |
|---|---|---|
| PENDING | PENDING | **Pendiente** (sin entregar) |
| DONE | PENDING | **Entregado** (en revisión) |
| DONE | APPROVED | **Calificado / Aprobado** |
| DONE | REJECTED | **Rechazado** (requiere correcciones) |

Campos útiles por proyecto: `title`, `task_status`, `revision_status`, `cohort.name`, `delivered_at`, `github_url`, `description` (feedback del revisor).

## Criterio de éxito

Lista de proyectos agrupada por estado (Pendientes primero, luego Entregados, luego Calificados), mostrando título, cohorte y fecha de entrega si existe.

## Notas

- Algunos proyectos aparecen en varias cohortes (ej. duplicados de spain-aie-pt-4); listar todos sin deduplicar para no perder contexto.
- El campo `description` contiene el feedback del revisor cuando hay revisión.
- `count` total en sep 2026: 35 proyectos.
