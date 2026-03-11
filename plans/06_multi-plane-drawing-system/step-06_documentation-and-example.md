# Step 6: Documentation and Example Workflow

## Goal
Document the complete multi-plane workflow with best practices, add a new section to the existing docs, and create an example script demonstrating a multi-story building modeled floor-by-floor using the plane system.

## Prerequisites
Steps 1–5 must be completed and committed.

---

### Step-by-Step Instructions

#### 6.1 — Add "Sistema de Planos de Trabajo" section to `docs/04-modelo-3d.md`

- [ ] Open `docs/04-modelo-3d.md`
- [ ] Find the `## Índice` section at the top (line 3) and add entry 6:

```markdown
## Índice
1. [Sistemas de Coordenadas 3D](#sistemas-de-coordenadas-3d)
2. [Definición de Nodos 3D](#definición-de-nodos-3d)
3. [Transformaciones Geométricas](#transformaciones-geométricas)
4. [Orientación de Elementos](#orientación-de-elementos)
5. [Ejemplo Completo: Edificio 3D](#ejemplo-completo-edificio-3d)
6. [Sistema de Planos de Trabajo (GUI)](#sistema-de-planos-de-trabajo-gui)
```

- [ ] At the END of the file (after the Ejemplo Completo section), append the following new section:

```markdown

---

## Sistema de Planos de Trabajo (GUI)

La GUI de OPynSees2000 incluye un sistema de planos de trabajo que permite modelar estructuras piso por piso, similar al workflow de SAP2000.

### Modos de Plano

| Modo | Eje Bloqueado | Vista de Cámara | Descripción |
|------|---------------|-----------------|-------------|
| **XY** | Z = elevación | Planta (top) | Para vigas y losas en un piso horizontal |
| **XZ** | Y = elevación | Frontal (front) | Para pórticos en el plano X-Z |
| **YZ** | X = elevación | Lateral (side) | Para pórticos en el plano Y-Z |
| **Free 3D** | Ninguno | Isométrica | Para conectar nodos existentes entre pisos |

### Filtrado por Plano

Cuando un plano está activo, el viewport muestra **únicamente** los elementos que están completamente contenidos en ese plano:

- Un nodo es visible si su coordenada bloqueada coincide exactamente con la elevación
- Un frame/shell es visible solo si **todos** sus nodos están en el plano
- Elementos que cruzan planos (como columnas entre pisos) no se muestran en ningún plano individual
- En modo Free 3D, todos los elementos son visibles

### Restricciones por Modo

- **Planos XY/XZ/YZ:** Permiten crear nodos nuevos y elementos libremente
- **Free 3D:** Solo permite conectar nodos existentes. No se pueden crear nodos nuevos en este modo
- Al intentar entrar en modo "Dibujar Nodo" con Free 3D activo, se cambia automáticamente a XY

### Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| **Tab** | Ciclar plano: XY → XZ → YZ → Free → XY |
| **Shift+Tab** | Ciclar plano en reversa |
| **Ctrl+1** | Seleccionar plano XY |
| **Ctrl+2** | Seleccionar plano XZ |
| **Ctrl+3** | Seleccionar plano YZ |
| **Ctrl+4** | Seleccionar modo Free 3D |
| **PgUp** | Aumentar elevación (1× espaciado de grilla) |
| **PgDn** | Disminuir elevación (1× espaciado de grilla) |
| **Shift+clic** | Override temporal a Free 3D (un clic) |

### Diagrama de Planos

```
          Z ↑         Plano XY (azul)
            |         ┌─────────┐ Z = elevación
            |         │  ·  ·  ·│
            |         │  ·  ·  ·│
            |         └─────────┘
            └──────→ Y
           /
          ↙ X

          Z ↑         Plano XZ (verde)
            |         ┌─────────┐
            |         │  ·  ·  ·│ Y = elevación
            |         │  ·  ·  ·│
            |         └─────────┘
            └──────→ X

          Z ↑         Plano YZ (rojo)
            |         ┌─────────┐
            |         │  ·  ·  ·│ X = elevación
            |         │  ·  ·  ·│
            |         └─────────┘
            └──────→ Y
```
```

---

#### 6.2 — Add "Modelado Estructural por Pisos" section to `docs/11-buenas-practicas.md`

- [ ] Open `docs/11-buenas-practicas.md`
- [ ] Find the `## Índice` section and add entry 7:

```markdown
## Índice
1. [Unidades y Consistencia](#unidades-y-consistencia)
2. [Refinamiento de Malla](#refinamiento-de-malla)
3. [Convergencia](#convergencia)
4. [Validación de Modelos](#validación-de-modelos)
5. [Errores Comunes](#errores-comunes)
6. [Optimización](#optimización)
7. [Modelado por Pisos (GUI)](#modelado-por-pisos-gui)
```

- [ ] Find the `## Resumen` section (line 457) and insert the following **before** it:

```markdown

---

## Modelado por Pisos (GUI)

### Flujo de Trabajo Recomendado

El sistema de planos de trabajo permite modelar edificios piso por piso de forma organizada:

#### Paso 1: Definir Nodos del Piso 1
1. Seleccionar modo **Dibujar Nodo**
2. Establecer plano **XY** con elevación Z=0.0
3. Crear nodos en la posición de cada columna
4. Repetir con Z=3.5 (o la altura del piso)

#### Paso 2: Crear Vigas en Cada Piso
1. Seleccionar modo **Dibujar Frame**
2. Mantener plano **XY** con la elevación del piso
3. Conectar nodos del mismo piso para crear vigas
4. Usar **PgUp/PgDn** para cambiar de piso rápidamente

#### Paso 3: Conectar Columnas entre Pisos
1. Cambiar a modo **Free 3D** (Tab o Ctrl+4)
2. Hacer clic en nodo inferior y luego en el superior
3. Repetir para todas las columnas

#### Paso 4: Verificar por Pisos
1. Regresar al plano **XY** para cada elevación
2. Verificar que cada piso tiene vigas completas
3. Verificar que los apoyos están en Z=0

### Consejos

| Consejo | Descripción |
|---------|-------------|
| **PgUp/PgDn** | Cambiar de piso rápidamente sin abrir paneles |
| **Free para columnas** | Solo usar Free 3D para conectar nodos existentes |
| **Verificar por piso** | Revisar cada elevación individualmente antes de analizar |
| **Shift+clic** | Override temporal para snap libre sin cambiar de modo |
| **Tab** | Ciclar rápidamente entre planos para inspección |

### Errores Comunes en Modelado por Pisos

1. **Crear nodos en Free 3D:** No está permitido. Use planos XY/XZ/YZ para crear nodos nuevos
2. **Columnas invisibles:** Las columnas cruzan entre pisos, por lo que no aparecen en vistas de un solo piso. Use Free 3D para verificarlas
3. **Nodos desalineados:** Si un nodo tiene Z=3.499 en vez de Z=3.5, no aparecerá en el filtro del plano XY a Z=3.5. Use snap a grilla para evitar esto
4. **Olvidar SpecialtyUI:** Siempre verificar en modo Free (todos los elementos visibles) antes de ejecutar análisis

```

---

#### 6.3 — Create example script `ejemplo_06_edificio_multi_piso.py`

- [ ] Create a new file `ejemplos/ejemplo_06_edificio_multi_piso.py` with the following content:

```python
"""
Ejemplo 06: Edificio de 3 Pisos — Modelado por Planos
=====================================================

Objetivo:
- Demostrar el workflow multi-plano de OPynSees2000
- Nodos organizados por pisos (plano XY a diferentes elevaciones)
- Vigas horizontales en cada piso
- Columnas verticales conectando pisos
- Análisis estático con carga lateral

El flujo de trabajo en la GUI sería:
  1. Plano XY Z=0  → crear nodos de base (4 esquinas)
  2. Plano XY Z=3  → crear nodos del piso 1
  3. Plano XY Z=6  → crear nodos del piso 2
  4. Plano XY Z=9  → crear nodos del piso 3
  5. Free 3D       → conectar columnas entre pisos
  6. Plano XY Z=3  → crear vigas del piso 1
  7. Plano XY Z=6  → crear vigas del piso 2
  8. Plano XY Z=9  → crear vigas del piso 3

Sistema de unidades: kN, m, s
"""

import openseespy.opensees as ops
import numpy as np

# ============================================
# LIMPIEZA Y CONFIGURACIÓN INICIAL
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

print("=" * 60)
print("EJEMPLO 06: EDIFICIO 3 PISOS — MODELADO POR PLANOS")
print("=" * 60)

# ============================================
# GEOMETRÍA
# ============================================

# Parámetros
num_stories = 3
story_height = 3.0      # m
span_x = 5.0            # m (1 vano en X)
span_y = 4.0            # m (1 vano en Y)

# Elevaciones de cada piso
elevations = [i * story_height for i in range(num_stories + 1)]
# [0.0, 3.0, 6.0, 9.0]

# Posiciones en planta (4 esquinas)
corners = [
    (0.0, 0.0),
    (span_x, 0.0),
    (span_x, span_y),
    (0.0, span_y),
]

# ============================================
# NODOS — organizados por plano XY a cada elevación
# ============================================
print("\n--- Nodos por plano ---")

node_grid = {}  # (ix, iy, iz) -> tag
tag = 1

for iz, z in enumerate(elevations):
    print(f"  Plano XY @ Z={z:.1f}m:")
    for ic, (cx, cy) in enumerate(corners):
        ops.node(tag, cx, cy, z)
        node_grid[(ic, iz)] = tag
        print(f"    Nodo {tag}: ({cx:.1f}, {cy:.1f}, {z:.1f})")
        tag += 1

print(f"\nTotal nodos: {tag - 1}")

# ============================================
# RESTRICCIONES — base empotrada (Z=0)
# ============================================
print("\n--- Apoyos empotrados en Z=0 ---")
for ic in range(len(corners)):
    base_tag = node_grid[(ic, 0)]
    ops.fix(base_tag, 1, 1, 1, 1, 1, 1)
    print(f"  Nodo {base_tag}: empotrado")

# ============================================
# MATERIAL Y SECCIONES
# ============================================
E_conc = 24_821_000.0  # kPa (f'c=28 MPa)
G_conc = 10_342_000.0  # kPa

# Material elástico
ops.uniaxialMaterial('Elastic', 1, E_conc)

# Sección columna 40x40
A_col = 0.16
Iz_col = 2.1333e-3
Iy_col = 2.1333e-3
J_col = 3.6053e-3
ops.section('Elastic', 1, E_conc, A_col, Iz_col, Iy_col, G_conc, J_col)

# Sección viga 30x50
A_beam = 0.15
Iz_beam = 3.125e-3
Iy_beam = 1.125e-3
J_beam = 3.516e-3
ops.section('Elastic', 2, E_conc, A_beam, Iz_beam, Iy_beam, G_conc, J_beam)

# ============================================
# TRANSFORMACIONES GEOMÉTRICAS
# ============================================

# Columnas (verticales): vecxz apunta en X
ops.geomTransf('PDelta', 1, 1.0, 0.0, 0.0)

# Vigas (horizontales): vecxz apunta en Z
ops.geomTransf('Linear', 2, 0.0, 0.0, 1.0)

# ============================================
# ELEMENTOS — Columnas (conectan pisos, visibles en Free 3D)
# ============================================
print("\n--- Columnas (Free 3D) ---")
elem_tag = 1

for ic in range(len(corners)):
    for iz in range(num_stories):
        ni = node_grid[(ic, iz)]
        nj = node_grid[(ic, iz + 1)]
        ops.element('elasticBeamColumn', elem_tag, ni, nj, 1, 1)
        print(f"  Columna {elem_tag}: [{ni} → {nj}]")
        elem_tag += 1

# ============================================
# ELEMENTOS — Vigas (en cada piso, visibles en plano XY)
# ============================================
print("\n--- Vigas por plano ---")

# Conectividad de vigas en planta (esquinas adyacentes)
beam_connections = [
    (0, 1),  # esquina 0-1 (viga en X)
    (1, 2),  # esquina 1-2 (viga en Y)
    (2, 3),  # esquina 2-3 (viga en X)
    (3, 0),  # esquina 3-0 (viga en Y)
]

for iz in range(1, num_stories + 1):
    z = elevations[iz]
    print(f"  Plano XY @ Z={z:.1f}m:")
    for ic_i, ic_j in beam_connections:
        ni = node_grid[(ic_i, iz)]
        nj = node_grid[(ic_j, iz)]
        ops.element('elasticBeamColumn', elem_tag, ni, nj, 2, 2)
        print(f"    Viga {elem_tag}: [{ni} → {nj}]")
        elem_tag += 1

print(f"\nTotal elementos: {elem_tag - 1}")

# ============================================
# CARGAS — Lateral en X (sismo simplificado)
# ============================================
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

# Fuerzas laterales proporcionales a la altura
F_base = 50.0  # kN (fuerza base total)
total_weight_factor = sum(elevations[1:])  # Suma de alturas

print("\n--- Cargas laterales ---")
for iz in range(1, num_stories + 1):
    z = elevations[iz]
    F_floor = F_base * z / total_weight_factor
    F_per_node = F_floor / len(corners)

    for ic in range(len(corners)):
        n_tag = node_grid[(ic, iz)]
        ops.load(n_tag, F_per_node, 0.0, 0.0, 0.0, 0.0, 0.0)
        print(f"  Nodo {n_tag} (Z={z:.1f}m): Fx = {F_per_node:.2f} kN")

# ============================================
# ANÁLISIS ESTÁTICO
# ============================================
print("\n--- Análisis estático ---")

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Newton')
ops.test('NormDispIncr', 1.0e-6, 100)
ops.analysis('Static')

result = ops.analyze(1)

if result == 0:
    print("  ✓ Análisis completado exitosamente")
else:
    print("  ✗ Error en el análisis")

# ============================================
# RESULTADOS
# ============================================
print("\n--- Desplazamientos por piso ---")
print(f"  {'Piso':<6} {'Z [m]':<8} {'Ux [mm]':<12} {'Uy [mm]':<12} {'Uz [mm]':<12}")
print("  " + "-" * 50)

for iz in range(num_stories + 1):
    z = elevations[iz]
    # Promedio de desplazamientos en el piso
    ux_avg = 0.0
    uy_avg = 0.0
    uz_avg = 0.0
    for ic in range(len(corners)):
        n_tag = node_grid[(ic, iz)]
        disp = ops.nodeDisp(n_tag)
        ux_avg += disp[0]
        uy_avg += disp[1]
        uz_avg += disp[2]
    n_corners = len(corners)
    ux_avg /= n_corners
    uy_avg /= n_corners
    uz_avg /= n_corners

    print(
        f"  {iz:<6} {z:<8.1f} {ux_avg * 1000:<12.4f} "
        f"{uy_avg * 1000:<12.4f} {uz_avg * 1000:<12.4f}"
    )

# ============================================
# DERIVAS DE ENTREPISO
# ============================================
print("\n--- Derivas de entrepiso (drift) ---")
print(f"  {'Piso':<6} {'Drift X':<12} {'Drift Y':<12} {'Límite':<10}")
print("  " + "-" * 40)

drift_limit = 0.015  # 1.5% típico para marcos

for iz in range(1, num_stories + 1):
    # Desplazamiento promedio del piso actual y anterior
    ux_top = sum(
        ops.nodeDisp(node_grid[(ic, iz)])[0]
        for ic in range(len(corners))
    ) / len(corners)
    ux_bot = sum(
        ops.nodeDisp(node_grid[(ic, iz - 1)])[0]
        for ic in range(len(corners))
    ) / len(corners)

    uy_top = sum(
        ops.nodeDisp(node_grid[(ic, iz)])[1]
        for ic in range(len(corners))
    ) / len(corners)
    uy_bot = sum(
        ops.nodeDisp(node_grid[(ic, iz - 1)])[1]
        for ic in range(len(corners))
    ) / len(corners)

    drift_x = abs(ux_top - ux_bot) / story_height
    drift_y = abs(uy_top - uy_bot) / story_height

    status_x = "✓" if drift_x < drift_limit else "✗"
    status_y = "✓" if drift_y < drift_limit else "✗"

    print(
        f"  {iz:<6} {drift_x:<12.6f} {drift_y:<12.6f} "
        f"{status_x}{status_y} (<{drift_limit})"
    )

print("\n" + "=" * 60)
print("Verificación de modelado por pisos:")
print(f"  - Plano XY Z=0.0: 4 nodos base (empotrados)")
print(f"  - Plano XY Z=3.0: 4 nodos + 4 vigas")
print(f"  - Plano XY Z=6.0: 4 nodos + 4 vigas")
print(f"  - Plano XY Z=9.0: 4 nodos + 4 vigas")
print(f"  - Free 3D: 12 columnas (no visibles en planos individuales)")
print("=" * 60)

ops.wipe()
```

---

### Step 6 Verification Checklist

- [ ] Documentation in `docs/04-modelo-3d.md` renders correctly in Markdown viewer
- [ ] Table of keyboard shortcuts is accurate and complete
- [ ] Documentation in `docs/11-buenas-practicas.md` is clear and follows existing style
- [ ] Workflow steps in buenas-practicas match the actual GUI behavior
- [ ] Run `python ejemplos/ejemplo_06_edificio_multi_piso.py` → verify it executes without errors
- [ ] Verify output shows nodes organized by plane, elements by type, and analysis results
- [ ] Load the example model in the GUI (recreate manually following the workflow) → verify each floor visible when switching planes in the GUI
- [ ] Verify no spelling errors or broken Markdown links in documentation
- [ ] Index entries in both docs point to correct anchors

---

#### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
