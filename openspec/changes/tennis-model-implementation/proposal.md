# Proposal: Tennis Model Implementation

## Change: tennis-model-implementation

### Intent
Implement tennis prediction modeling in 3 phases: data structures, basic framework, and simple ML model.

### Scope
- **Phase 1**: Data structures (90 lines) - tennis torneos, entity fields
- **Phase 2**: Basic framework (130 lines) - endpoint, schema, sin ML  
- **Phase 3**: Simple ML model (170 lines) - RandomForest ligero, features básicas
- **Total**: ~380 líneas (size:exception aprobado)

### Delivery: Single PR, size:exception approved

### Non-Goals
- Modelos ML avanzados (deep learning)
- Datos tenísticos externos
- Features complejas

### Success Criteria
- 380 líneas cambiadas máximo
- 176 tests backend pasan
- 71 tests frontend pasan
- Backward compat: soccer sin cambios
