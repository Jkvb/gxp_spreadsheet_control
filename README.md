# gxp_spreadsheet_control (Odoo 12)

Módulo para control regulado de hojas de cálculo en entornos GxP, con enfoque conservador alineado a **21 CFR Part 11** y **GAMP 5**.

## ¿Qué resuelve?

Este módulo permite gestionar un ciclo de vida controlado para hojas de cálculo reguladas dentro de Odoo:

- Inventario maestro de hojas controladas.
- Versionado con hash SHA-256.
- Flujo de estados (borrador, revisión, aprobación, vigente, retirada).
- Firma electrónica con reautenticación.
- Audit trail inmutable (modelo propio).
- Capa visual complementaria en mensajería (chatter) para legibilidad.
- Control de cambios y revisión periódica.
- Estructura base para expediente de validación.

> Nota: El audit trail regulatorio principal es `gxp.audit.event` (append-only). El chatter se usa como apoyo visual y operativo, no como única evidencia.

---

## Modelos principales

- `gxp.controlled.sheet`: ficha maestra del documento regulado.
- `gxp.sheet.version`: versiones controladas del archivo (con hash e inmutabilidad de efectivas).
- `gxp.signature.event`: eventos de firma electrónica.
- `gxp.audit.event`: bitácora de auditoría inmutable.
- `gxp.validation.package`: expediente de validación (base).
- `gxp.test.case`: casos de prueba vinculados al expediente.
- `gxp.change.control`: control de cambios.
- `gxp.periodic.review`: revisiones periódicas.

---

## Seguridad y roles

Grupos incluidos:

- GxP Admin
- GxP Author
- GxP Reviewer
- GxP Approver
- GxP Validator
- GxP Auditor Readonly

Incluye:

- ACL por modelo (`security/ir.model.access.csv`).
- Record rules por compañía (`security/security.xml`).
- Restricción de borrado físico en registros regulados.

---

## Firma electrónica

Implementada mediante `gxp.sign.wizard` con:

- Reautenticación con contraseña del usuario actual.
- Captura de significado de firma (review/approval/retirement).
- Snapshot de hash del registro al firmar.
- Registro de evento de firma + evento de auditoría.

---

## Auditoría

### 1) Evidencia regulatoria principal

`gxp.audit.event` registra, entre otros:

- Altas y modificaciones relevantes.
- Cambios de estado.
- Firmas.
- Descargas/exportaciones.
- Intentos fallidos de firma.

Con metadatos técnicos:

- Fecha/hora servidor
- Usuario
- Sesión
- IP
- User-agent

### 2) Evidencia visual complementaria

Si `use_chatter_audit` está activo en la hoja:

- Se publican notas en chatter con resumen del evento.
- Tabla antes/después para cambios de campos.

---

## UX / Vistas

- Vista Kanban “canvas” para hoja controlada con indicadores visuales.
- Formulario con panel chatter.
- Asistente de uso (`gxp.onboarding.wizard`) por pasos.

---

## Instalación

1. Copiar el módulo en la ruta de addons de Odoo 12.
2. Actualizar lista de apps.
3. Instalar **GxP Spreadsheet Control**.
4. Asignar roles a usuarios según segregación de funciones.

---

## Datos técnicos incluidos

- Secuencias:
  - `gxp.controlled.sheet`
  - `gxp.change.control`
- Cron diario:
  - generación de revisiones periódicas vencidas.

---

## Pruebas

Pruebas automáticas en `tests/test_gxp_spreadsheet.py` cubren base funcional:

- Creación de hoja y cálculo hash.
- Bloqueo de versión efectiva.
- Supersedencia de versión vigente.
- Prohibición de borrado físico en modelos regulados.
- Validación de cierre de change control.
- Creación de audit events.
- Publicación/no publicación en chatter según configuración.

---

## Limitaciones actuales del MVP

- No edita Excel en tiempo real dentro del navegador.
- No incluye biometría ni MFA productiva.
- No incluye OCR ni análisis celda-a-celda de fórmulas.
- No sustituye SOPs y controles organizacionales.

---

## Recomendaciones de uso en entorno regulado

- Mantener el sistema como **closed system** por defecto.
- Definir SOPs de:
  - alta/baja de usuarios,
  - firma electrónica,
  - respaldo/restore,
  - revisión periódica,
  - gestión de cambios.
- Ejecutar validación basada en riesgo con trazabilidad URS→FS/DS→Pruebas→Evidencia.

