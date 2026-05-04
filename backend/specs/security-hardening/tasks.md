# Tasks — Cierre de Gaps de Seguridad Full-Stack

## Preparación y línea base
- [ ] Crear y revisar los artefactos `spec.md`, `plan.md` y `tasks.md` del cambio.
- [ ] Consolidar la lista de gaps verificados con evidencia de archivo y severidad.
- [ ] Definir qué endpoints quedan en cada categoría de privilegio:
  - [ ] admin mutation
  - [ ] ops read
  - [ ] feedback write
- [ ] Confirmar qué dominios externos de highlights/media siguen siendo válidos en
      producto.
- [ ] Confirmar qué datos del frontend deben sobrevivir entre sesiones y cuáles no.

## Fase 0 — Contención inmediata
- [ ] Eliminar del runtime el bypass admin por host loopback.
- [ ] Garantizar que la dependencia administrativa falle sin credencial válida.
- [ ] Proteger temporalmente `POST /api/v1/suggested-picks/feedback` si aún no está
      lista la solución granular definitiva.
- [ ] Proteger temporalmente `GET /api/v1/suggested-picks/learning-stats`.
- [ ] Revisar si `/_ready` debe pasar a modo protegido o apagado en despliegues
      públicos.
- [ ] Revisar si `metrics` debe quedar protegido o apagado.
- [ ] Revisar si `monitor/backlog` debe quedar protegido o apagado.
- [ ] Validar con requests de regresión que las rutas críticas ya no devuelven `200`
      a caller anónimo.

## Fase 1 — Auth y autorización backend

### Diseño de dependencias de auth
- [ ] Definir una dependencia explícita para admin mutation.
- [ ] Definir una dependencia explícita para ops read.
- [ ] Definir una dependencia explícita para feedback write.
- [ ] Evitar reutilizar una sola credencial con privilegios innecesarios si no es
      estrictamente obligatorio.
- [ ] Documentar el contrato de env vars/keys resultante.

### Aplicación a rutas sensibles
- [ ] Aplicar auth explícita a `POST /api/v1/train/run-now`.
- [ ] Revisar `GET /api/v1/train/status` y `GET /api/v1/train/cached` para confirmar
      si deben seguir públicas.
- [ ] Aplicar auth explícita a `POST /admin/labeler/dry-run`.
- [ ] Aplicar auth explícita a `POST /admin/labeler/run`.
- [ ] Aplicar auth explícita a `GET /admin/monitor/backlog`.
- [ ] Aplicar auth explícita a `POST /api/v1/suggested-picks/feedback`.
- [ ] Aplicar auth explícita a `GET /api/v1/suggested-picks/learning-stats` si sigue
      considerándose sensible.
- [ ] Aplicar auth explícita a `/_ready` si permanece disponible.
- [ ] Aplicar auth explícita a métricas si permanecen disponibles.

## Fase 1B — Rate limiting y validación de abuso
- [ ] Añadir rate limit a `POST /api/v1/suggested-picks/feedback`.
- [ ] Añadir rate limit a `POST /admin/labeler/dry-run`.
- [ ] Añadir rate limit a `POST /admin/labeler/run`.
- [ ] Añadir rate limit a `GET /admin/monitor/backlog` si sigue expuesto.
- [ ] Definir límites distintos para lectura operativa y mutación administrativa.
- [ ] Convertir `market_type` a whitelist o enum controlado.
- [ ] Convertir `prediction` a whitelist o enum controlado.
- [ ] Convertir `actual_outcome` a whitelist o enum controlado.
- [ ] Validar que `match_id` exista antes de registrar feedback.
- [ ] Validar que el feedback corresponda a un mercado soportado por el sistema.
- [ ] Rechazar feedback incoherente o incompleto antes de tocar aprendizaje.

## Fase 1C — Labeler y trabajo costoso
- [ ] Hacer que `window_days` filtre realmente el query del labeler.
- [ ] O eliminar el parámetro `window` si no va a acotar el trabajo real.
- [ ] Evitar full scans innecesarios cuando solo se necesita una ventana temporal.
- [ ] Verificar que `dry-run` no haga escrituras persistentes.
- [ ] Verificar que `run` solo escriba lo estrictamente necesario y audite sin
      exponer datos innecesarios.

## Fase 2 — Superficie operativa y errores internos
- [ ] Desactivar docs/OpenAPI/Redoc en despliegues expuestos por defecto.
- [ ] Mantener `GET /health` como única superficie pública mínima si Render la
      necesita.
- [ ] Proteger o apagar `/_ready`.
- [ ] Proteger o apagar `monitor`.
- [ ] Proteger o apagar `metrics`.
- [ ] Sustituir `str(exc)` en respuestas HTTP por mensajes opacos.
- [ ] Introducir `error_id` o equivalente para correlación segura de errores.
- [ ] Evitar devolver texto crudo de excepciones de base de datos o dependencias.
- [ ] Sanitizar logs de inicialización para no imprimir el DSN completo.
- [ ] Revisar otros logs que puedan filtrar host, usuario o credenciales.

## Fase 3 — Configuración y secretos fail-closed

### Runtime backend
- [ ] Eliminar fallback `admin/adminpassword@localhost` de `MongoRepository`.
- [ ] Eliminar fallback `admin/adminpassword@localhost` de `AsyncMongoRepository`.
- [ ] Eliminar fallback `admin/adminpassword@localhost` de `AsyncMongoAdapter`.
- [ ] Exigir `MONGO_URI` explícito en todos los paths sync/async.
- [ ] Mantener `MONGO_DB_NAME` con default seguro solo si el equipo lo justifica;
      si no, exigirlo también de forma explícita.

### Configuración local y docs
- [ ] Reemplazar ejemplos ejecutables con root credentials en `.env.example`.
- [ ] Actualizar `backend/README.md` para reflejar contrato fail-closed.
- [ ] Revisar `scripts/setup-dev.sh` y utilidades relacionadas para que no
      regeneren defaults inseguros.
- [ ] Endurecer `docker-compose.dev.yml`:
  - [ ] evitar exposición innecesaria de Mongo al host,
  - [ ] evitar root credentials predecibles,
  - [ ] documentar el contrato local seguro.
- [ ] Verificar que `render.yaml` siga alineado con el nuevo contrato.

## Fase 4 — Hardening frontend de confianza externa

### Política de URLs seguras
- [ ] Crear una utilidad central para validar URLs externas.
- [ ] Permitir solo `https` y hosts aprobados.
- [ ] Rechazar `javascript:`, `data:`, `blob:` y esquemas no soportados.
- [ ] Aplicar esa utilidad en `MatchDetailsModal`.
- [ ] Aplicar esa utilidad en `MatchCard`.
- [ ] Aplicar esa utilidad en `PreMatchPrediction`.

### Navegación y embeds externos
- [ ] Añadir `rel="noopener noreferrer"` en enlaces con `target="_blank"`.
- [ ] Añadir `sandbox` explícito a `iframe` externos.
- [ ] Añadir `referrerPolicy` a embeds y enlaces externos cuando aplique.
- [ ] Definir fallback de UI cuando una URL externa no pase validación.

### CSP y headers
- [ ] Añadir una CSP base en `frontend/index.html`.
- [ ] Inventariar dominios necesarios para `fonts`, `connect-src`, `frame-src` e
      `img-src`.
- [ ] Alinear la configuración de despliegue con esa CSP.

## Fase 4B — Persistencia local y PWA
- [ ] Clasificar cada store persistida como preferencia, cache temporal o dato no
      persistible.
- [ ] Revisar `useParleyStore` y decidir si `selectedPicks` debe persistirse.
- [ ] Revisar `usePredictionStore` y limitar persistencia a preferencias mínimas.
- [ ] Revisar `useBotStore` y limitar persistencia a datos realmente necesarios.
- [ ] Revisar otras stores persistidas (`live`, `cache`, etc.) con el mismo criterio.
- [ ] Añadir TTL o purge explícito donde se mantenga cache local.
- [ ] Reducir `runtimeCaching` de Workbox a endpoints permitidos uno por uno.
- [ ] Excluir de la cache PWA rutas operativas, feedback, entrenamiento y cualquier
      endpoint sensible actual o futuro.
- [ ] Verificar si `dev-dist/sw.js` debe seguir siendo artefacto versionado o si el
      source of truth debe quedarse solo en `vite.config.ts`.

## Fase 5 — Regresión y validación

### Backend tests
- [ ] Añadir tests que prueben que rutas admin fallan sin credencial.
- [ ] Añadir tests que prueben que feedback falla sin credencial.
- [ ] Añadir tests que prueben que feedback inválido es rechazado.
- [ ] Añadir tests que prueben que `/_ready` no expone excepciones crudas.
- [ ] Añadir tests que prueben que `monitor` no devuelve `str(exc)`.
- [ ] Añadir tests que prueben que Mongo falla si falta `MONGO_URI`.
- [ ] Añadir tests que prueben que el labeler sí respeta la ventana efectiva o que
      ya no expone ese parámetro.

### Frontend tests
- [ ] Añadir tests de utilidad de URL segura.
- [ ] Añadir tests de componentes para verificar `sandbox`/`noopener`/fallback.
- [ ] Añadir tests o verificación controlada del allowlist de Workbox.
- [ ] Añadir tests que aseguren que errores internos no se muestran crudos al
      usuario cuando el diseño final lo prohíba.

### Gates
- [ ] Ejecutar `./scripts/quality_gate.sh backend`.
- [ ] Ejecutar `./scripts/quality_gate.sh frontend`.
- [ ] Ejecutar `./scripts/quality_gate.sh all`.

## Cierre documental
- [ ] Actualizar documentación operativa del backend con el nuevo contrato de auth.
- [ ] Actualizar documentación de despliegue con el nuevo contrato Mongo.
- [ ] Documentar la policy de URLs externas y CSP del frontend.
- [ ] Documentar qué estado del frontend puede persistirse y cuál no.
- [ ] Guardar memoria del cierre con hallazgos resueltos, validaciones y riesgos
      residuales.

## Criterio de cierre de la spec
- [ ] No queda ningún path de runtime con bypass admin implícito por host.
- [ ] No queda ninguna escritura anónima al sistema de aprendizaje.
- [ ] No quedan respuestas HTTP con excepciones crudas o fuga de DSN.
- [ ] No quedan fallbacks Mongo con credenciales conocidas en runtime.
- [ ] El frontend rechaza URLs externas no aprobadas y no embebe media sin
      restricciones.
- [ ] La PWA ya no cachea genéricamente todo `/api`.
- [ ] Existe regresión automatizada para los gaps cerrados.