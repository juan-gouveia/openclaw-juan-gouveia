---
name: 4geeks-auth
description: Autenticar y verificar la sesión en la API de estudiante de 4Geeks/BreatheCode. Usar cuando Juan pregunta por su cuenta 4Geeks, verifica su sesión, o como paso previo de otras skills 4geeks.
---

# Skill 1 — Autenticación 4Geeks

Verifica que el token de estudiante de Juan es válido y que la sesión está activa en la API de BreatheCode (4Geeks Academy).

## Configuración

- **Base URL:** `https://breathecode.herokuapp.com`
- **Token:** secreto protegido `FOURGEEKS_STUDENT_TOKEN` (egress proxy activo; el sentinel se inyecta solo en `exec` del gateway)
- **Vigencia del token actual:** expira 2026-10-02. Si da 401, pedir a Juan que obtenga la cookie `4g_tok` de learn.4geeks.com (DevTools → Application → Cookies).

## Paso 1 — Verificar token vía path

```bash
curl -s -m 25 "https://breathecode.herokuapp.com/v1/auth/token/$FOURGEEKS_STUDENT_TOKEN"
```

Respuesta esperada (HTTP 200):

```json
{"token": "...", "token_type": "login", "expires_at": "2026-10-02T...", "user_id": 1117}
```

- HTTP 401 → token inválido o expirado; avisar a Juan.
- HTTP 200 → token válido; continuar.

## Paso 2 — Confirmar identidad vía header

Usar el valor `token` de la respuesta anterior en el header:

```bash
curl -s -m 25 -H "Authorization: Token ***" \
  "https://breathecode.herokuapp.com/v1/admissions/user/me"
```

Respuesta esperada: objeto de usuario con `id`, `email`, `first_name`, `last_name`, `github`, `profile`.

## Criterio de éxito

Ambos pasos devuelven HTTP 200 y el `id` del usuario es `1117` (Juan). Reportar: nombre, email, fecha de expiración del token y estado de la sesión.

## Notas

- El header correcto es `Authorization: Token *** `Bearer` no sirve (devuelve "credentials not provided").
- El valor de `$FOURGEEKS_STUDENT_TOKEN` en el entorno es un sentinel `oc-sent-v2...`; el egress proxy lo sustituye solo para `breathecode.herokuapp.com`.
- No loguear ni mostrar el token en claro nunca.
