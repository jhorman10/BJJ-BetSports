# Plan — Cierre de Gaps de Seguridad Full-Stack

## Objetivo
Cerrar los gaps de seguridad verificados en backend, frontend y configuración
sin abrir una reescritura de arquitectura completa, priorizando primero los
vectores explotables hoy y después el hardening estructural que evita
regresiones.

## Estrategia general

- Primero cerrar lo explotable por caller anónimo o configuración insegura.
- Después reducir exposición pública y defaults débiles.
- Luego endurecer la frontera del navegador y la persistencia offline.
- Cerrar con regresión automatizada y documentación de operación segura.

## Fases

### 0) Contención inmediata — prioridad máxima

Objetivo
- Reducir inmediatamente el riesgo de mutaciones privilegiadas y poisoning.

Trabajo
- Quitar la posibilidad de acceso administrativo implícito por host loopback.
- Bloquear o proteger temporalmente feedback y learning stats si todavía no hay
  auth granular lista.
- Revisar si `/_ready`, metrics y monitor deben seguir expuestos mientras se
  implementa el cierre final.

Salida esperada
- Ninguna operación administrativa o de aprendizaje queda abierta a caller
  anónimo.

Validación esperada
- Requests sin credencial a rutas admin/feedback dejan de devolver `200`.

### 1) Hardening backend de auth y abuso

Objetivo
- Reemplazar decisiones implícitas por auth explícita y límites de uso.

Trabajo
- Rediseñar dependencias de auth para separar admin mutation, ops read y
  feedback write.
- Añadir rate limiting a feedback, labeler y monitor.
- Validar payload de feedback con whitelists y coherencia con partido/mercado.
- Hacer que `window` del labeler filtre trabajo real o eliminar el parámetro.

Salida esperada
- Las rutas costosas y las mutaciones persistentes quedan autenticadas,
  limitadas y validadas.

Dependencias
- Fase 0 cerrada.

### 2) Reducción de exposición operativa y sanitización

Objetivo
- Minimizar fingerprinting y fuga de detalles internos.

Trabajo
- Desactivar docs/OpenAPI/Redoc en despliegues internet-facing.
- Mover `/_ready`, monitor y métricas detrás de auth o de red interna.
- Sustituir respuestas con `str(exc)` por errores opacos.
- Sanitizar logs que hoy muestran host/DSN o detalles de infraestructura.

Salida esperada
- La superficie pública queda reducida a lo estrictamente necesario.

Validación esperada
- Respuestas operativas no exponen excepciones crudas ni DSN.

### 3) Configuración y secretos fail-closed

Objetivo
- Asegurar que faltantes de configuración detengan el sistema en vez de activar
  defaults inseguros.

Trabajo
- Eliminar fallbacks Mongo con `admin/adminpassword` en todos los code paths.
- Exigir `MONGO_URI` explícito en repos sync/async y adapters.
- Endurecer `docker-compose.dev.yml` para no publicar Mongo con root credentials
  previsibles ni exposición innecesaria al host.
- Alinear `.env.example`, README y setup local con el contrato seguro nuevo.

Salida esperada
- El repo deja de normalizar credenciales conocidas como contrato operativo.

### 4) Hardening frontend de confianza externa

Objetivo
- Evitar navegación/embebido inseguro y reducir el valor de los datos persistidos
  en el cliente.

Trabajo
- Introducir utilidad de validación de URLs externas y allowlist de dominios.
- Añadir `sandbox`, `referrerPolicy` y `noopener noreferrer` donde corresponda.
- Añadir CSP base en `frontend/index.html` y alinear despliegue con ella.
- Reclasificar qué estado vive en localStorage/IndexedDB.
- Reducir Workbox a endpoints explícitamente permitidos.

Salida esperada
- El navegador deja de confiar ciegamente en URLs externas o en cualquier GET de
  `/api` para persistencia/cache.

### 5) Regresión, evidencia y cierre

Objetivo
- Convertir el hardening en baseline verificable del repo.

Trabajo
- Añadir tests backend/frontend para los gaps cerrados.
- Ejecutar gates por slice y gate full-stack.
- Actualizar documentación operativa y de desarrollo.
- Registrar decisiones residuales o deudas diferidas.

Salida esperada
- El cierre queda defendible por pruebas, docs y configuración.

## Orden recomendado de ejecución

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Fase 4
6. Fase 5

## Dependencias críticas

- No iniciar cambios de frontend sin haber fijado primero qué dominios externos
  siguen siendo válidos para highlights/media.
- No cerrar definitivamente feedback si el producto depende de uso público sin
  antes decidir el mecanismo mínimo de identidad/autorización.
- No considerar cerrada la fase Mongo mientras un solo path del runtime siga
  aceptando defaults con credenciales conocidas.

## Criterios de promoción entre fases

- Fase 0 -> 1:
  - admin y feedback ya no responden satisfactoriamente a caller anónimo.
- Fase 1 -> 2:
  - auth y rate limiting cubren rutas sensibles sin regresiones funcionales.
- Fase 2 -> 3:
  - superficies operativas expuestas y fugas de error están cerradas.
- Fase 3 -> 4:
  - configuración Mongo y docs ya reflejan contrato fail-closed.
- Fase 4 -> 5:
  - frontend ya valida URLs externas y restringe persistencia/cache.

## Riesgos de implementación

- Cambiar auth puede romper flujos de desarrollo local.
  - Mitigación: proveer harness de test/dev explícito, no implícito.
- Endurecer CSP puede romper fonts, embeds o recursos remotos.
  - Mitigación: inventario previo de dominios y rollout controlado.
- Reducir persistencia puede afectar UX offline.
  - Mitigación: conservar solo preferencias realmente necesarias y medir el
    impacto antes de cerrar la fase.

## Validación esperada

- `./scripts/quality_gate.sh backend`
- `./scripts/quality_gate.sh frontend`
- `./scripts/quality_gate.sh all`
- Smoke manual de rutas operativas y highlights externos con la policy nueva.