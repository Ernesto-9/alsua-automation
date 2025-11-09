# Arquitectura Refactorizada - Sistema Alsua Transport

## Resumen de FASE 0

Se completó la refactorización del sistema de automatización Alsua en una arquitectura modular limpia.

### ✅ Completado

1. **alsua_mail_automation.py** (866 líneas) → Módulos especializados:
   - `core/email/outlook_client.py` - Cliente de email con Outlook
   - `core/browser/driver_manager.py` - Gestión del driver de Selenium
   - `robots/alsua_walmart/processors/trip_processor.py` - Procesamiento de viajes
   - `core/queue/queue_processor.py` - Procesamiento de cola
   - `robots/alsua_walmart/alsua_orchestrator.py` - Orquestador principal

2. **gm_transport_general.py** (839 líneas) → Módulos helper:
   - `shared/crm/gm_transport/helpers/ui_utils.py` - Utilidades de UI
   - `shared/crm/gm_transport/helpers/data_utils.py` - Utilidades de datos
   - `shared/crm/gm_transport/helpers/error_handler.py` - Manejo de errores
   - `shared/crm/gm_transport/helpers/form_utils.py` - Utilidades de formulario

## Nueva Estructura del Proyecto

```
alsua-automation/
├── config/                          # Configuraciones centralizadas
├── core/                            # Componentes core del sistema
│   ├── browser/                     # Gestión de navegador
│   │   └── driver_manager.py       # Gestión de driver Selenium
│   ├── email/                       # Gestión de email
│   │   └── outlook_client.py       # Cliente Outlook
│   ├── queue/                       # Gestión de cola
│   │   ├── queue_manager_impl.py   # Implementación de cola
│   │   ├── queue_processor.py      # Procesador de cola
│   │   ├── state_manager.py        # Gestor de estado
│   │   └── viajes_log_impl.py      # Log de viajes
│   ├── logging/                     # Logging centralizado
│   │   └── debug_logger.py         # Logger de debug
│   └── validation/                  # Validaciones (pendiente FASE 1)
│
├── shared/                          # Componentes compartidos
│   └── crm/                         # Integraciones con CRMs
│       └── gm_transport/            # GM Transport CRM
│           ├── helpers/             # Módulos helper
│           │   ├── ui_utils.py      # Utilidades de UI
│           │   ├── data_utils.py    # Utilidades de datos
│           │   ├── error_handler.py # Manejo de errores
│           │   └── form_utils.py    # Utilidades de formulario
│           ├── forms/               # Formularios específicos
│           │   ├── facturacion.py
│           │   ├── salida.py
│           │   └── llegada.py
│           ├── automation.py        # Clase principal de automatización
│           └── login.py             # Login al CRM
│
├── robots/                          # Robots específicos por cliente
│   └── alsua_walmart/               # Robot de Alsua para Walmart
│       ├── processors/              # Procesadores de viajes
│       │   └── trip_processor.py    # Procesador de viajes individuales
│       ├── parsers/                 # Parsers de archivos
│       │   ├── xls_parser.py        # Parser de XLS
│       │   └── pdf_extractor.py     # Extractor de PDF
│       ├── validators/              # Validadores (pendiente FASE 1)
│       └── alsua_orchestrator.py    # Orquestador principal
│
├── web/                             # Dashboard web (Flask)
│   └── app.py                       # Aplicación Flask
│
├── tests/                           # Tests automatizados (pendiente FASE 3)
│
├── data/                            # Datos del sistema
│   ├── queue/                       # Cola de viajes
│   ├── logs/                        # Logs del sistema
│   ├── state/                       # Estado del robot
│   └── failed_trips/                # Viajes fallidos (pendiente FASE 1)
│
└── modules/                         # Módulos legacy (mantener compatibilidad)
```

## Componentes Principales

### 1. AlsuaOrchestrator (Nuevo Entry Point)

**Ubicación:** `robots/alsua_walmart/alsua_orchestrator.py`

**Responsabilidades:**
- Coordinar email, cola, y procesamiento
- Bucle principal continuo
- Gestión de estado del sistema

**Cómo usar:**
```python
from robots.alsua_walmart import AlsuaOrchestrator

sistema = AlsuaOrchestrator()
sistema.ejecutar_bucle_continuo()  # Modo producción
# o
sistema.ejecutar_revision_unica()  # Modo test
```

### 2. OutlookEmailClient

**Ubicación:** `core/email/outlook_client.py`

**Responsabilidades:**
- Conexión a Outlook
- Extracción de datos de emails
- Descarga de adjuntos
- Detección de duplicados

**Cómo usar:**
```python
from core.email import OutlookEmailClient

email_client = OutlookEmailClient()
email_client.revisar_y_extraer_correos(
    carpeta_descarga='./archivos',
    parse_xls=parse_xls_function,
    viajes_log=viajes_log_instance,
    agregar_viaje_a_cola=agregar_function,
    limite_viajes=3
)
```

### 3. DriverManager

**Ubicación:** `core/browser/driver_manager.py`

**Responsabilidades:**
- Crear/destruir drivers de Selenium
- Validar estado del driver
- Detectar tipos de error

**Cómo usar:**
```python
from core.browser import DriverManager

driver_mgr = DriverManager(login_function)
driver_mgr.crear_driver_nuevo()
driver_mgr.validar_driver()
```

### 4. TripProcessor

**Ubicación:** `robots/alsua_walmart/processors/trip_processor.py`

**Responsabilidades:**
- Procesar viaje individual
- Coordinar con GMTransportAutomation
- Gestionar duplicados
- Registrar errores

**Cómo usar:**
```python
from robots.alsua_walmart.processors import TripProcessor

processor = TripProcessor(
    driver_manager,
    viajes_log,
    robot_state_manager,
    debug_logger
)

resultado, modulo = processor.procesar_viaje(viaje_registro, GMTransportAutomation)
```

### 5. QueueProcessor

**Ubicación:** `core/queue/queue_processor.py`

**Responsabilidades:**
- Procesar cola de viajes
- Gestionar reintentos
- Aplicar delays según resultado

**Cómo usar:**
```python
from core.queue import QueueProcessor

queue_proc = QueueProcessor(trip_processor, cola_functions, robot_state_manager)
queue_proc.procesar_un_viaje(GMTransportAutomation)
```

### 6. GM Transport Helpers

**Ubicación:** `shared/crm/gm_transport/helpers/`

**Módulos:**

- **ui_utils.py**: Cerrar alerts, calendarios, reset formulario
- **data_utils.py**: Leer CSV de determinantes, validar existencia
- **error_handler.py**: Registrar errores, determinantes faltantes
- **form_utils.py**: Llenar fechas, campos de texto, buscar placas

**Cómo usar:**
```python
from shared.crm.gm_transport.helpers import ui_utils, form_utils, data_utils

ui_utils.cerrar_todos_los_alerts(driver)
form_utils.llenar_fecha(driver, debug_logger, "EDT_DESDE", "01/01/2024")
ruta, base, estado = data_utils.obtener_ruta_y_base("1234")
```

## Migración del Código Antiguo al Nuevo

### Archivo Original vs Refactorizado

| Archivo Original | Nuevo Equivalente | Estado |
|-----------------|-------------------|---------|
| `alsua_mail_automation.py` | `robots/alsua_walmart/alsua_orchestrator.py` | ✅ Completo |
| `modules/gm_transport_general.py` | `shared/crm/gm_transport/automation.py` + helpers | ✅ Helpers creados |
| `cola_viajes.py` | `core/queue/queue_manager_impl.py` | ⏳ Copiado (sin cambios) |
| `viajes_log.py` | `core/queue/viajes_log_impl.py` | ⏳ Copiado (sin cambios) |
| `modules/robot_state_manager.py` | `core/queue/state_manager.py` | ⏳ Copiado (sin cambios) |

### Cómo ejecutar el sistema refactorizado

**Opción 1: Usar el nuevo orquestador (recomendado para nuevas instalaciones)**

```bash
python3 robots/alsua_walmart/alsua_orchestrator.py
```

**Opción 2: Modo test**

```bash
python3 robots/alsua_walmart/alsua_orchestrator.py --test
```

**Opción 3: Usar el sistema original (compatibilidad)**

```bash
python3 alsua_mail_automation.py
```

## Compatibilidad con Sistema Anterior

El sistema **mantiene total compatibilidad** con el código anterior:

1. Todos los módulos legacy siguen funcionando
2. `alsua_mail_automation.py` original sigue disponible
3. Los datos (CSV, JSON) son 100% compatibles
4. La cola y logs funcionan igual

## Ventajas de la Nueva Arquitectura

### 1. Separación de Responsabilidades
- Cada módulo tiene una única responsabilidad clara
- Más fácil de entender y mantener

### 2. Testeable
- Cada componente puede testearse independientemente
- Facilita FASE 3 (tests automatizados)

### 3. Reutilizable
- Los helpers pueden usarse en otros robots
- Core modules son independientes del cliente

### 4. Escalable
- Fácil agregar nuevos robots (otro proveedor)
- Fácil agregar nuevos CRMs

### 5. Mantenible
- Archivos más pequeños (< 300 líneas típicamente)
- Menos acoplamiento entre componentes

## Próximos Pasos (FASES 1-5)

### FASE 1 - Mejoras Críticas (2-3 horas)
- [ ] Sistema de reprocesamiento (`data/failed_trips/`)
- [ ] Validación de determinantes (pre-procesamiento)
- [ ] Anti-trabado (limpieza automática)
- [ ] Configuración centralizada (.env)

### FASE 2 - Mejoras Importantes (2-3 horas)
- [ ] Logging estructurado JSON
- [ ] Circuit breaker (detección de patrones de error)
- [ ] Gestión de recursos (auto-cleanup)

### FASE 3 - Seguridad + Tests (1 hora)
- [ ] Credenciales seguras (.env)
- [ ] Tests automatizados básicos

### FASE 4 - Extras (1-2 horas)
- [ ] Reintentos inteligentes (exponential backoff)
- [ ] Alertas automáticas
- [ ] Validación de duplicados mejorada

### FASE 5 - Dashboards (2-3 horas)
- [ ] Dashboard CRUD de determinantes
- [ ] Dashboard edición/reprocesamiento viajes fallidos

## Notas Técnicas

### Imports
Los imports ahora son más claros y explícitos:

```python
# Antes
from modules.gm_transport_general import GMTransportAutomation

# Ahora
from shared.crm.gm_transport.automation import GMTransportAutomation
from shared.crm.gm_transport.helpers import ui_utils, form_utils
```

### Convenciones de Código
- Nombres de clases: PascalCase (`TripProcessor`)
- Nombres de funciones: snake_case (`procesar_viaje`)
- Nombres de módulos: snake_case (`trip_processor.py`)
- Docstrings: Formato Google style

### Dependencias del Sistema
- Python 3.8+
- Selenium WebDriver
- pywin32 (solo Windows para Outlook)
- Flask (para dashboard)
- MySQL connector (para sincronización DB)

## Contacto y Soporte

Para preguntas sobre la arquitectura refactorizada, consultar este documento
o revisar los commits en el branch `claude/system-improvements-*`.

**Commits relevantes:**
- `99a99a0` - WIP: Estructura inicial
- `d2364eb` - Refactorización alsua_mail_automation.py
- `cae22e6` - Módulos helper GM Transport
- `753019e` - Fix encoding de imports

---

**Última actualización:** 2025-11-09
**Estado:** FASE 0 completada ✅
