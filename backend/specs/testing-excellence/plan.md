# Plan — Excelencia de Validación Full-Stack

## Objetivo
Hacer reproducible y estricta la validación del repositorio con un único flujo local
que replique CI, exponga la deuda restante y permita iterar hacia un estado verde.

## Fases

1) Fundaciones del gate canónico — hoy
   - Crear un script full-stack único en `scripts/`.
   - Evitar instalaciones oportunistas y comportamientos mágicos.
   - Hacer que `scripts/local_checks.sh` deje de ser una fuente de verdad paralela.

2) Línea base real de calidad — hoy
   - Ejecutar el gate canónico completo.
   - Registrar familias de fallos por severidad y coste de reparación.

3) Primer bloque de remediación — hoy
   - Corregir la primera familia de fallos de mayor retorno.
   - Revalidar el slice afectado y luego el gate completo.

4) Endurecimiento incremental — siguiente iteración
   - Continuar por familias: imports/nombres indefinidos, tipado básico, formato,
     refactors complejos con tests, coverage y branch protection.

## Cierre ejecutado

- `scripts/quality_gate.sh all` ya es la fuente de verdad full-stack y pasó en verde.
- `scripts/local_checks.sh` dejó de divergir del flujo canónico.
- Los workflows remotos relevantes (`ci.yml`, `ci-pr.yml`, `lint.yml`) quedaron alineados con los mismos checks base del gate local.
- La deuda restante ya no bloquea reproducibilidad ni paridad local/remota; queda relegada a endurecimiento incremental fuera del alcance de este spec.

## Decisiones técnicas

- El flujo canónico debe fallar rápido y devolver un código de salida no cero ante el
  primer gate roto.
- El script debe asumir que las dependencias ya existen o fallar con un mensaje claro;
  no debe autoinstalar herramientas silenciosamente.
- La validación backend y frontend deben estar separadas en funciones para facilitar
  ejecución parcial y depuración.
- La documentación debe referenciar exactamente el mismo comando que usa el equipo.

## Validación esperada

- `scripts/quality_gate.sh` o equivalente ejecuta backend + frontend en orden fijo.
- `scripts/local_checks.sh` deja de divergir.
- Se obtiene un output reproducible con la deuda real actual del repo.

## Dependencias

- Entorno Python del backend disponible en `backend/.venv`.
- Dependencias del frontend instaladas con `npm ci`.
- Herramientas de backend presentes en el virtualenv: `ruff`, `black`, `isort`,
  `mypy`, `pytest`.