# Fundamentos de OpenSees

## Índice
1. [Introducción](#introducción)
2. [Workflow General de Modelado](#workflow-general-de-modelado)
3. [Teoría del Método de Elementos Finitos](#teoría-del-método-de-elementos-finitos)
4. [Sistemas de Coordenadas](#sistemas-de-coordenadas)
5. [Grados de Libertad](#grados-de-libertad)
6. [Inicialización de Modelos](#inicialización-de-modelos)

---

## Introducción

**OpenSees** (Open System for Earthquake Engineering Simulation) es un framework de software para simular la respuesta sísmica de sistemas estructurales y geotécnicos. **OpenSeesPy** es la interfaz Python que permite acceder a todas las capacidades de OpenSees mediante scripting en Python.

### Características Principales

- **Software libre y de código abierto**
- **Capacidades no-lineales avanzadas** (materiales, geometría, contacto)
- **Análisis estático y dinámico**
- **Amplia biblioteca de elementos y materiales**
- **Ideal para investigación y aplicaciones profesionales**

### ¿Cuándo usar OpenSees?

✅ **Sí, úsalo para:**
- Análisis sísmico avanzado (pushover, time-history)
- Modelado no-lineal de estructuras
- Investigación en ingeniería sísmica
- Análisis que requieren modelos constitutivos especializados

❌ **Considera otras herramientas para:**
- Diseño estructural rutinario (SAP2000, ETABS más eficientes)
- Modelado arquitectónico (Revit + plugins)
- Análisis térmico o CFD (fuera del alcance)

---

## Workflow General de Modelado

### Diagrama de Flujo

```
┌─────────────────────────────┐
│  1. Import y Wipe           │
│  import openseespy.opensees │
│  ops.wipe()                 │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  2. Inicializar Modelo      │
│  ops.model(...)             │
│  Definir ndm, ndf           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  3. Definir Nodos           │
│  ops.node(tag, x, y, z)     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  4. Definir Materiales      │
│  ops.uniaxialMaterial(...)  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  5. Definir Secciones       │
│  ops.section(...)           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  6. Transformaciones Geom.  │
│  ops.geomTransf(...)        │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  7. Crear Elementos         │
│  ops.element(...)           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  8. Condiciones de Borde    │
│  ops.fix(), equalDOF()      │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  9. Definir Cargas          │
│  ops.pattern(), load()      │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  10. Crear Recorders        │
│  ops.recorder(...)          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  11. Configurar Análisis    │
│  system, numberer, etc.     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  12. Ejecutar Análisis      │
│  ops.analyze(numSteps)      │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  13. Procesar Resultados    │
│  ops.nodeDisp(), eleForce() │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  14. Limpiar Modelo         │
│  ops.wipe()                 │
└─────────────────────────────┘
```

### Paso 1: Import y Limpieza

```python
import openseespy.opensees as ops

# Limpiar cualquier modelo previo en memoria
ops.wipe()
```

**Teoría:** `wipe()` elimina todos los objetos del dominio (nodos, elementos, materiales, etc.). Siempre úsalo al inicio para evitar conflictos.

### Paso 2: Inicializar Modelo

```python
ops.model('basic', '-ndm', ndm, '-ndf', ndf)
```

**Parámetros:**
- `'basic'`: Tipo de modelo builder (siempre usar 'basic')
- `ndm`: Número de dimensiones (2 o 3)
- `ndf`: Número de grados de libertad por nodo

**Ejemplos comunes:**

| Tipo de Estructura | ndm | ndf | Descripción |
|-------------------|-----|-----|-------------|
| Armadura 2D       | 2   | 2   | Desplazamientos X, Y |
| Pórtico 2D        | 2   | 3   | Ux, Uy, Rz |
| Armadura 3D       | 3   | 3   | Ux, Uy, Uz |
| Pórtico 3D        | 3   | 6   | Ux, Uy, Uz, Rx, Ry, Rz |

```python
# Ejemplo: Pórtico espacial (3D frame)
ops.model('basic', '-ndm', 3, '-ndf', 6)
```

### Paso 3: Definir Nodos

```python
ops.node(nodeTag, *coords, '-mass', *massValues)
```

**Parámetros:**
- `nodeTag`: Identificador único (entero positivo)
- `coords`: Coordenadas (x,) para 1D, (x, y) para 2D, (x, y, z) para 3D
- `massValues` (opcional): Masas en cada DOF

```python
# Nodos de un pórtico 3D
ops.node(1, 0.0, 0.0, 0.0)          # Nodo en origen
ops.node(2, 5.0, 0.0, 0.0)          # 5m en X
ops.node(3, 0.0, 0.0, 3.5)          # 3.5m en Z (vertical)

# Nodo con masa para análisis dinámico
mass = 50.0  # toneladas (kN·s²/m)
ops.node(4, 5.0, 0.0, 3.5, '-mass', mass, mass, mass, 0.0, 0.0, 0.0)
```

**Teoría:** Los nodos son puntos discretos donde se conectan los elementos. Son fundamentales en el MEF (Método de Elementos Finitos). Las masas son necesarias para análisis dinámicos (modal, time-history).

---

## Teoría del Método de Elementos Finitos

### Concepto Fundamental

El **Método de Elementos Finitos (MEF)** aproxima la solución de problemas complejos dividiendo la estructura continua en elementos más simples conectados en nodos.

### Pasos del MEF

#### 1. Discretización

La geometría continua se divide en elementos finitos:

```
Estructura Continua          Modelo Discretizado
━━━━━━━━━━━━━━━━━━━     →    ━━━●━━━●━━━●━━━
                                 1   2   3
                              (nodos y elementos)
```

#### 2. Formulación del Elemento

Para cada elemento, se define:

**Función de desplazamiento:**
$$u(x) = \mathbf{N}(x) \cdot \mathbf{u}_e$$

Donde:
- $u(x)$ = desplazamiento en punto $x$ del elemento
- $\mathbf{N}(x)$ = funciones de forma (shape functions)
- $\mathbf{u}_e$ = desplazamientos nodales

**Relación deformación-desplazamiento:**
$$\boldsymbol{\varepsilon} = \mathbf{B} \cdot \mathbf{u}_e$$

**Ley constitutiva (material):**
$$\boldsymbol{\sigma} = \mathbf{D} \cdot \boldsymbol{\varepsilon}$$

**Matriz de rigidez del elemento:**
$$\mathbf{K}_e = \int_V \mathbf{B}^T \mathbf{D} \mathbf{B} \, dV$$

#### 3. Ensamblaje Global

Las matrices de todos los elementos se ensamblan en la matriz global:

$$\mathbf{K}_{global} = \sum_{e=1}^{n_{elementos}} \mathbf{K}_e$$

#### 4. Aplicación de Condiciones de Borde

Los desplazamientos prescritos (apoyos) se imponen en el sistema:
- DOF fijos se eliminan del sistema (condensación estática)
- O se aplican mediante multiplicadores de Lagrange

#### 5. Solución del Sistema

Para análisis estático lineal:
$$\mathbf{K} \cdot \mathbf{U} = \mathbf{F}$$

Donde:
- $\mathbf{K}$ = matriz de rigidez global
- $\mathbf{U}$ = vector de desplazamientos (incógnitas)
- $\mathbf{F}$ = vector de cargas

Para análisis dinámico:
$$\mathbf{M} \ddot{\mathbf{U}} + \mathbf{C} \dot{\mathbf{U}} + \mathbf{K} \mathbf{U} = \mathbf{F}(t)$$

Donde:
- $\mathbf{M}$ = matriz de masa
- $\mathbf{C}$ = matriz de amortiguamiento
- $t$ = tiempo

#### 6. Post-Procesamiento

De los desplazamientos nodales, se calculan:
- Deformaciones: $\boldsymbol{\varepsilon} = \mathbf{B} \cdot \mathbf{u}_e$
- Esfuerzos: $\boldsymbol{\sigma} = \mathbf{D} \cdot \boldsymbol{\varepsilon}$
- Fuerzas internas: $\mathbf{f}_e = \mathbf{K}_e \cdot \mathbf{u}_e$

### Convergencia del MEF

A medida que refinamos la malla (más elementos, más pequeños):
- La solución se acerca a la exacta
- Error disminuye
- Costo computacional aumenta

**Regla práctica:** Refinar hasta que refinar más cambie los resultados en menos del 5%.

---

## Sistemas de Coordenadas

### Sistema Global

El **sistema de coordenadas global** es único para todo el modelo:

```
        Z ↑
          |
          |
          |________→ Y
         /
        /
       ↙
      X
```

**Convención estándar en OpenSees:**
- **X**: Horizontal, longitudinal
- **Y**: Horizontal, transversal
- **Z**: Vertical (hacia arriba positivo)
- **Regla de la mano derecha**

### Sistema Local del Elemento

Cada elemento tiene su **sistema de coordenadas local**:

```
        3 (local z)
        ↑
        |
        |________→ 2 (local y)
       /
      /
     ↙
    1 (local x, eje del elemento)
```

**Para elementos tipo viga-columna:**
- **Eje 1 (local x)**: A lo largo del elemento (del nodo i al nodo j)
- **Ejes 2 y 3**: Ejes principales de la sección transversal

**Transformación:** El comando `geomTransf` relaciona coordenadas locales con globales.

---

## Grados de Libertad

### 2D (ndm=2, ndf=3)

Para un pórtico plano en el plano X-Z:

| DOF | Descripción | Símbolo |
|-----|-------------|---------|
| 1   | Traslación en X | $u_x$ |
| 2   | Traslación en Z | $u_z$ |
| 3   | Rotación en Y | $\theta_y$ |

```
    Z ↑
      |   ↻ θy (DOF 3)
      |  /
      | /
      |/________→ X
     nodo
      ux (DOF 1)
```

### 3D (ndm=3, ndf=6)

Para estructuras espaciales:

| DOF | Descripción | Símbolo |
|-----|-------------|---------|
| 1   | Traslación en X | $u_x$ |
| 2   | Traslación en Y | $u_y$ |
| 3   | Traslación en Z | $u_z$ |
| 4   | Rotación sobre X | $\theta_x$ |
| 5   | Rotación sobre Y | $\theta_y$ |
| 6   | Rotación sobre Z | $\theta_z$ |

```
        Z ↑
          |     ↻ θz
          |    /
          |   ↻ θx
          |  /
          | /________→ Y
          |/    ↻ θy
         /
        /
       ↙ X
     nodo
```

### Armaduras (ndf=2 o 3)

Elementos tipo "truss" solo tienen traslaciones, sin rotaciones:

- **2D**: ndf=2 (ux, uz)
- **3D**: ndf=3 (ux, uy, uz)

---

## Inicialización de Modelos

### Plantilla Básica

```python
import openseespy.opensees as ops

# Limpiar memoria
ops.wipe()

# Modelo 3D con 6 DOF por nodo
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Aquí continúa la definición del modelo...
```

### Reiniciar Modelo

```python
# Durante el script, si necesitas empezar de cero:
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)
```

⚠️ **Advertencia:** `wipe()` borra TODO, incluyendo materiales y secciones. Debes redefinir todo después.

### Modelo con Opciones Adicionales

```python
# Para modelos muy grandes, con rayleigh damping
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# ... definir nodos, elementos, etc. ...

# Luego, si necesitas amortiguamiento de Rayleigh:
alphaM = 0.0
betaK = 0.0
betaKinit = 0.0
betaKcomm = 0.00125
ops.rayleigh(alphaM, betaK, betaKinit, betaKcomm)
```

---

## Ejemplo Completo: Marco Simple 2D

```python
import openseespy.opensees as ops

# ============================================
# 1. INICIALIZACIÓN
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# ============================================
# 2. DEFINIR NODOS
# ============================================
# Coordenadas: (X, Z)
ops.node(1, 0.0, 0.0)    # Base izquierda
ops.node(2, 4.0, 0.0)    # Base derecha
ops.node(3, 0.0, 3.0)    # Tope izquierdo
ops.node(4, 4.0, 3.0)    # Tope derecho

# ============================================
# 3. CONDICIONES DE BORDE
# ============================================
# Empotramientos en la base
ops.fix(1, 1, 1, 1)  # Fijo en x, z, rotación
ops.fix(2, 1, 1, 1)

# ============================================
# 4. TRANSFORMACIÓN GEOMÉTRICA
# ============================================
# Para columnas verticales (en plano XZ)
ops.geomTransf('Linear', 1)

# ============================================
# 5. MATERIAL
# ============================================
E = 200e6  # kPa (200 GPa para acero)
ops.uniaxialMaterial('Elastic', 1, E)

# ============================================
# 6. SECCIÓN (Columna)
# ============================================
A_col = 0.02    # m² (área de sección)
I_col = 2e-4    # m⁴ (momento de inercia)
ops.section('Elastic', 1, E, A_col, I_col)

# Sección (Viga)
A_beam = 0.015  # m²
I_beam = 1.5e-4 # m⁴
ops.section('Elastic', 2, E, A_beam, I_beam)

# ============================================
# 7. ELEMENTOS
# ============================================
# Columnas (elementos 1 y 2)
ops.element('elasticBeamColumn', 1, 1, 3, A_col, E, I_col, 1)
ops.element('elasticBeamColumn', 2, 2, 4, A_col, E, I_col, 1)

# Viga (elemento 3)
ops.element('elasticBeamColumn', 3, 3, 4, A_beam, E, I_beam, 1)

# ============================================
# 8. CARGAS
# ============================================
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

# Carga vertical en nodo 4 (10 kN hacia abajo)
ops.load(4, 0.0, -10.0, 0.0)

# ============================================
# 9. RECORDERS
# ============================================
ops.recorder('Node', '-file', 'desplazamientos.txt', '-time', 
             '-node', 3, 4, '-dof', 1, 2, 3, 'disp')

# ============================================
# 10. ANÁLISIS
# ============================================
ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

# Ejecutar
ops.analyze(1)

# ============================================
# 11. RESULTADOS
# ============================================
disp_x = ops.nodeDisp(4, 1)  # Desplazamiento horizontal
disp_z = ops.nodeDisp(4, 2)  # Desplazamiento vertical

print(f"Desplazamiento horizontal nodo 4: {disp_x*1000:.3f} mm")
print(f"Desplazamiento vertical nodo 4: {disp_z*1000:.3f} mm")

# Reacciones
R1x = ops.nodeReaction(1, 1)
R1z = ops.nodeReaction(1, 2)
R2x = ops.nodeReaction(2, 1)
R2z = ops.nodeReaction(2, 2)

print(f"\nReacciones:")
print(f"Nodo 1: Rx = {R1x:.2f} kN, Rz = {R1z:.2f} kN")
print(f"Nodo 2: Rx = {R2x:.2f} kN, Rz = {R2z:.2f} kN")

# ============================================
# 12. LIMPIAR
# ============================================
ops.wipe()
```

---

## Puntos Clave

✅ **Siempre iniciar con `ops.wipe()`**  
✅ **Definir `ndm` y `ndf` apropiados para tu estructura**  
✅ **Mantener consistencia de unidades**  
✅ **Los tags (identificadores) deben ser únicos**  
✅ **El orden importa: nodos antes que elementos**  
✅ **Recorders antes de `analyze()`**

---

## Siguiente Capítulo

Continúa con **[Materiales y Secciones](02-materiales-y-secciones.md)** para aprender a definir el comportamiento constitutivo de los elementos.
