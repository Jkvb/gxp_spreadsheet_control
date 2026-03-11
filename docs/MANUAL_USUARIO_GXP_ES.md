# Manual de Usuario
## gxp_spreadsheet_control (Odoo 12)

### 1. Objetivo
Este módulo permite controlar hojas de cálculo reguladas en Odoo con enfoque GxP:
- Inventario maestro de hojas controladas.
- Versionado con hash SHA-256.
- Flujo de revisión y aprobación.
- Firma electrónica con reautenticación.
- Audit trail inmutable.
- Control de cambios y revisión periódica.
- Edición tabular en navegador y apertura de Excel/PDF.

### 2. Menú principal
Ir a **Control Hojas calculo**.
Submenús más usados:
- Hojas controladas
- Versiones
- Change Control
- Periodic Reviews
- Audit Trail
- Catálogos

### 3. Alta de hoja controlada
1) Entrar a **Hojas controladas** y pulsar **Crear**.
2) Completar campos mínimos:
   - Nombre
   - Intended use
   - Proceso de negocio (catálogo)
   - Tipo de registro (catálogo)
   - Predicate rule (catálogo)
3) Guardar. El sistema asigna código automáticamente.

### 4. Crear una versión controlada
1) Ir a **Versiones** y pulsar **Crear**.
2) Seleccionar la hoja.
3) Elegir modo:
   - Archivo: cargar Excel en `file_binary`.
   - Navegador: activar `Edición en navegador` y capturar filas en la pestaña de contenido web.
4) Completar `change_summary`.
5) Guardar.

### 5. Editar hoja desde navegador
1) Abrir la versión en estado borrador.
2) Activar `Edición en navegador`.
3) En pestaña **Contenido web (navegador)** agregar/modificar filas.
4) El hash de la versión se recalcula automáticamente.

### 6. Abrir documentos
- **Abrir Excel**:
  - Si la versión tiene archivo, abre/descarga el Excel real.
  - Si es modo web, exporta CSV.
- **Ver PDF embebido**:
  - Abre `pdf_snapshot_binary` en visor embebido (download=false).

### 7. Flujo de estados de versión
Estados:
- Draft -> In Review -> Pending Approval -> Effective
- Effective -> Superseded / Retired

Reglas clave:
- No enviar a revisión sin contenido (archivo o web).
- No pasar a aprobación sin firma de revisión.
- No hacer efectiva sin firma de aprobación.
- Reemplazar una versión efectiva requiere Change Control cerrado y vinculado.
- Versiones efectivas/bloqueadas no se editan.

### 8. Firma electrónica
1) En versión, usar botones:
   - Firmar revisión
   - Firmar aprobación
2) Ingresar contraseña del usuario actual (reauth).
3) El sistema guarda evento de firma con:
   - firmante
   - fecha/hora
   - significado
   - hash firmado

### 9. Auditoría
- Evidencia principal: modelo `gxp.audit.event` (append-only).
- Evidencia complementaria: notas en chatter (si `use_chatter_audit` está activo).
- Se registran eventos de creación, cambios, firmas, descargas/exportaciones y transiciones de estado.

### 10. Change Control y revisión periódica
- Toda sustitución de versión vigente debe vincularse a Change Control cerrado.
- El cron diario genera revisiones periódicas vencidas.

### 11. Roles recomendados
- Author: crea y prepara borradores.
- Reviewer: revisa y firma revisión.
- Approver: firma aprobación y decide vigencia/retiro.
- Auditor Readonly: consulta evidencia.
- Admin: parametrización y soporte.

### 12. Buenas prácticas GxP
- No trabajar con archivos maestros fuera de Odoo.
- Usar siempre el flujo de versión + firma.
- Mantener SOPs de usuarios, firma, backup/restore y change control.
- Ejecutar validación basada en riesgo con trazabilidad documental.
