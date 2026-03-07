# OPynSees2000

**GUI tipo SAP2000 para modelado estructural con OpenSeesPy.**

Interfaz gráfica interactiva para crear modelos de análisis estructural,
generar scripts OpenSeesPy, y ejecutar análisis estático y modal — todo
desde una interfaz visual al estilo SAP2000.

## Características

- **Modelado visual** — nodos, elementos (frame, truss, shell), restricciones
- **Definición de propiedades** — materiales, secciones, transformaciones
- **Cargas** — patrones de carga con cargas nodales
- **Viewport 3D** — PyVista/VTK con etiquetas, selección interactiva, flechas de carga
- **Generación de scripts** — exporta código OpenSeesPy listo para ejecutar
- **Análisis** — estático lineal y modal con visualización de deformada
- **Persistencia** — guardar/abrir proyectos en formato JSON (.opss)
- **Undo/Redo** — edición de propiedades con Ctrl+Z / Ctrl+Y

## Requisitos

- Python ≥ 3.10
- PySide6 ≥ 6.6
- PyVista ≥ 0.43
- NumPy ≥ 1.24
- OpenSeesPy ≥ 3.5 (opcional, para ejecución de análisis)

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/your-user/OPynSees2000.git
cd OPynSees2000

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

# Instalar dependencias
pip install -e .

# Con soporte de análisis
pip install -e ".[analysis]"
```

## Ejecución

```bash
# Desde la raíz del proyecto
python -m gui

# O usando el entry point (después de pip install -e .)
opynsees2000
```

## Estructura del proyecto

```
gui/
├── main.py                 # Entry point
├── main_window.py          # Ventana principal
├── core/
│   ├── model_data.py       # Dataclasses del modelo
│   ├── project_io.py       # Serialización JSON
│   ├── script_generator.py # Generador OpenSeesPy
│   ├── analysis_runner.py  # Ejecución de análisis
│   └── undo_manager.py     # Sistema Undo/Redo
├── dialogs/                # Diálogos modales
├── panels/                 # Paneles laterales
├── viewport/               # Viewport 3D PyVista
└── theme/                  # QSS theme
docs/                       # Documentación de fundamentos
ejemplos/                   # Scripts de ejemplo OpenSeesPy
```

## Flujo de trabajo

1. **Definir** — materiales, secciones, transformaciones, patrones de carga
2. **Dibujar** — nodos (coordenadas), elementos (conectividad)
3. **Asignar** — restricciones, cargas nodales
4. **Analizar** — estático lineal o modal
5. **Resultados** — deformada, desplazamientos, períodos

## Licencia

MIT
