---
name: 4geeks-assets
description: Buscar en el catálogo de ejercicios/proyectos/lecciones de 4Geeks por dificultad, tecnología o texto. Usar cuando Juan pregunta qué contenido existe (ej. "proyectos de Python difíciles", "ejercicios de TypeScript"), o quiere explorar el catálogo.
---

# Skill 5 — Catálogo de assets (4Geeks)

Busca contenido educativo del catálogo público de BreatheCode con filtros de dificultad, tecnología y tipo.

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (ver Skill 1)
- **Endpoint:** `GET /v1/registry/asset`
- **Catálogo de tecnologías:** `GET /v1/registry/technology`

## Filtros disponibles (query params)

| Param | Valores | Notas |
|---|---|---|
| `difficulty` | `BEGINNER`, `EASY`, `INTERMEDIATE`, `HARD` | Algunos assets tienen difficulty `null` — no aparecen al filtrar |
| `technologies` | slug de tecnología (ej. `python`, `typescript`, `html-css`) | Ver catálogo abajo; slug en minúsculas |
| `asset_type` | `LESSON`, `EXERCISE`, `PROJECT` | |
| `like` | texto de búsqueda | ⚠️ Empareja poco (búsqueda "dashboard" → 0 resultados); preferir filtros por tecnología/tipo |
| `limit` / `offset` | paginación | Respuesta: `{count, results, next, ...}` |

## Flujo

1. **Autenticar** (Skill 1).
2. **Construir query** con los filtros que Juan pida. Ejemplos:
   - "proyectos de Python difíciles" → `{"asset_type": "PROJECT", "technologies": "python", "difficulty": "HARD"}`
   - "ejercicios de TypeScript" → `{"asset_type": "EXERCISE", "technologies": "typescript"}`
3. **Ejecutar** con paginación (mismo patrón que Skills 2-4).
4. **Mostrar** por asset: `title`, `difficulty`, tecnologías, `slug`, `url` (repo).

## Catálogo de tecnologías (sep 2026, 40 slugs útiles)

Flask, Node, Python, React.js, Javascript, TypeScript, Java, Bootstrap, HTML and CSS, databases, Machine Learning, Artificial Intelligence, LLMs, Generative AI, prompt engineering, web-development, git, GitHub, linux, ciberseguridad, UI/UX, Software Engineering with AI, RestAPI, vibe coding, data security, Data Science...

Para slugs exactos: `GET /v1/registry/technology?limit=40` (títulos → slug = título en minúsculas sin espacios, verificado con `python` y `typescript`).

## Campos del response

`title`, `slug`, `difficulty` (puede ser `null`), `asset_type`, `technologies` (lista que puede ser strings o dicts — manejar ambos casos), `url` (repo GitHub), `readme_url`, `category`, `duration`, `description`.

## Criterio de éxito

Lista filtrada con conteo (`count`) y los primeros resultados con título, dificultad, tecnologías y slug. Si count es grande, ofrecer refinar.

## Notas

- Datos sep 2026: 423 PROJECT total; difficulty=HARD → solo 2 (CSS drawing); python → 374 assets; EXERCISE+typescript → 11.
- El campo `technologies` en results inconsistente: a veces strings, a veces dicts — el código debe tolerar ambos.
- `like` con palabras comunes devuelve 0; no confiar en él para búsqueda libre.
