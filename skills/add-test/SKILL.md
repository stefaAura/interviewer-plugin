---
name: add-test
description: >
  Genera tests pytest para aura-core-ai-interviewer. Delega a @test-writer
  para cobertura completa siguiendo las convenciones del proyecto: pytest-asyncio,
  85% coverage, mocks correctos de providers, DB real en integration tests.
---

Delega a `@test-writer` para generar tests para: $ARGUMENTS

El test-writer leerá el módulo, identificará qué cubrir, y producirá tests
unitarios e de integración siguiendo las convenciones del proyecto.
