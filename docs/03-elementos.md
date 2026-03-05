# Elementos Estructurales en OpenSees

## Índice
1. [Introducción](#introducción)
2. [Elementos de Viga-Columna](#elementos-de-viga-columna)
3. [Elementos Truss](#elementos-truss)
4. [Elementos Shell](#elementos-shell)
5. [Comparación y Selección](#comparación-y-selección)

---

## Introducción

Los **elementos** conectan nodos yutilizan materiales/secciones para definir el comportamiento estructural. OpenSees ofrece diversos tipos de elementos según las necesidades de análisis.

### Clasificación Principal

```
Elementos
├── Frame Elements (Viga-Columna)
│   ├── elasticBeamColumn
│   ├── forceBeamColumn (force-based)
│   └── dispBeamColumn (displacement-based)
├── Truss/Cable Elements
│   ├── Truss
│   └── corotTruss
└── Surface/Shell Elements
    ├── ShellMITC4
    └── ShellDKGQ
```

---

## Elementos de Viga-Columna

### 1. Elastic Beam-Column

**Comando:**
```python
ops.element('elasticBeamColumn', eleTag, *eleNodes, A, E, G, J, Iy, Iz, 
            transfTag, '-mass', massDens, '-cMass')
```

**Parámetros:**
- `eleTag`: Identificador único del elemento
- `eleNodes`: `[iNode, jNode]` nodos inicial y final
- `A`: Área de la sección transversal
- `E`: Módulo de elasticidad
- `G`: Módulo de corte
- `J`: Constante torsional
- `Iy`, `Iz`: Momentos de inercia respecto a ejes locales y, z
- `transfTag`: Tag de transformación geométrica
- `massDens`: Masa por unidad de longitud (opcional)
- `-cMass`: Usar matriz de masa consistente (opcional)

**Teoría:**

Basado en la **teoría de vigas de Euler-Bernoulli**:
- Secciones planas permanecen planas y perpendiculares al eje
- No considera deformación por corte
- Válido para vigas esbeltas ($L/h > 10$)

**Matriz de rigidez local (2D):**

Para elemento en eje local x:

$$\mathbf{K}_{local} = \begin{bmatrix}
\frac{EA}{L} & 0 & 0 & -\frac{EA}{L} & 0 & 0 \\
0 & \frac{12EI}{L^3} & \frac{6EI}{L^2} & 0 & -\frac{12EI}{L^3} & \frac{6EI}{L^2} \\
0 & \frac{6EI}{L^2} & \frac{4EI}{L} & 0 & -\frac{6EI}{L^2} & \frac{2EI}{L} \\
-\frac{EA}{L} & 0 & 0 & \frac{EA}{L} & 0 & 0 \\
0 & -\frac{12EI}{L^3} & -\frac{6EI}{L^2} & 0 & \frac{12EI}{L^3} & -\frac{6EI}{L^2} \\
0 & \frac{6EI}{L^2} & \frac{2EI}{L} & 0 & -\frac{6EI}{L^2} & \frac{4EI}{L}
\end{bmatrix}$$

**Ventajas:**
✅ Computacionalmente eficiente  
✅ Exacto para análisis lineal elástico  
✅ No requiere convergencia iterativa  
✅ Ideal para análisis modal

**Limitaciones:**
❌ Solo comportamiento elástico  
❌ No captura plasticidad  
❌ No considera efectos P-Delta (sin geomTransf adecuado)

**Ejemplo 2D:**
```python
# Columna vertical de 3m
ops.node(1, 0.0, 0.0)
ops.node(2, 0.0, 3.0)

# Propiedades de sección W14x90
A = 0.0174   # m²
E = 200e6    # kPa
G = 77e6     # kPa
I = 7.62e-4  # m⁴

# Transformación para columna vertical
ops.geomTransf('Linear', 1)

ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)
```

**Ejemplo 3D:**
```python
# Viga horizontal en X
ops.node(1, 0.0, 0.0, 3.0)
ops.node(2, 5.0, 0.0, 3.0)

# Propiedades
A = 0.0174
E = 200e6
G = 77e6
J = 1.2e-5   # Constante torsional
Iy = 2.5e-4  # Inercia débil
Iz = 7.6e-4  # Inercia fuerte

# Transformación: vecxz para orientar sección
ops.geomTransf('Linear', 2, 0, 0, 1)  # Vector Z global define plano x-z local

ops.element('elasticBeamColumn', 1, 1, 2, A, E, G, J, Iy, Iz, 2)
```

---

### 2. Force-Based Beam-Column

**Comando:**
```python
ops.element('forceBeamColumn', eleTag, *eleNodes, transfTag, integrationTag,
            '-mass', mass, '-iter', maxIter, tol)
```

**Requiere definir integración de Gauss:**
```python
ops.beamIntegration('Lobatto', integrationTag, secTag, numIntPts)
# o
ops.beamIntegration('Legendre', integrationTag, secTag, numIntPts)
```

**Parámetros de integración:**
- `Lobatto`: Gauss-Lobatto (incluye extremos del elemento)
- `Legendre`: Gauss-Legendre (puntos interiores)
- `numIntPts`: Número de puntos de integración (típicamente 3-5)

**Teoría:**

**Formulación basada en fuerzas:**
1. Interpola fuerzas (fuerzas básicas son exactas en equilibrio)
2. Determina deformaciones de compatibilidad
3. Estado de la sección calculado en puntos de integración

**Ventaja clave:** Captura plasticidad distribuida con **UN SOLO ELEMENTO** por miembro.

$$\mathbf{q} = \mathbf{F} \cdot \mathbf{Q}$$

Donde:
- $\mathbf{q}$ = deformaciones básicas del elemento
- $\mathbf{F}$ = matriz de flexibilidad del elemento
- $\mathbf{Q}$ = fuerzas básicas

**Puntos de integración:**

```
Elemento con 5 puntos Lobatto:

  i  ●───●───●───●───●  j
     1   2   3   4   5

     └─────── L ───────┘
```

La plasticidad puede desarrollarse en cualquier punto de integración.

**Ventajas:**
✅ Muy preciso para análisis no-lineal  
✅ Captura plasticidad distribuida  
✅ 1-2 elementos por miembro suficiente  
✅ Equilibrio exacto

**Limitaciones:**
❌ Más lento que displacement-based  
❌ Requiere iteración a nivel de elemento  
❌ Puede no converger en casos extremos

**Ejemplo:**
```python
# Definir material y sección
ops.uniaxialMaterial('Steel02', 1, 250e3, 200e6, 0.01)
ops.section('Fiber', 1)
# ... agregar fibras ...

# Integración Lobatto con 5 puntos
ops.beamIntegration('Lobatto', 1, 1, 5)

# Transformación
ops.geomTransf('PDelta', 1)

# Elemento force-based
ops.element('forceBeamColumn', 1, 1, 2, 1, 1)
```

---

### 3. Displacement-Based Beam-Column

**Comando:**
```python
ops.element('dispBeamColumn', eleTag, *eleNodes, transfTag, integrationTag,
            '-mass', mass, '-cMass')
```

**Teoría:**

**Formulación basada en desplazamientos:**
1. Interpola desplazamientos a lo largo del elemento
2. Deriva curvatura de desplazamientos interpolados
3. Calcula fuerzas de sección

**Desventaja:** Requiere **múltiples elementos** para capturar plasticidad localizada.

**Curvatura interpolada:**
$$\kappa(x) = \mathbf{B}(x) \cdot \mathbf{u}_e$$

Donde $\mathbf{B}$ deriva de funciones de forma.

**Ventajas:**
✅ Más rápido que force-based  
✅ Siempre converge a nivel de elemento  
✅ Bueno para plasticidad distribuida

**Limitaciones:**
❌ Necesita 4-8 elementos por miembro para plasticidad localizada  
❌ Menos preciso para rotulas plásticas

**Cuándo usar?**
- Análisis con plasticidad distribuida (plastificación gradual de sección)
- Cuando la velocidad es crítica
- Problemas donde force-based no converge

**Ejemplo:**
```python
# Discretizar columna en 5 elementos
L_col = 3.0
num_ele = 5
dL = L_col / num_ele

for i in range(num_ele):
    ops.element('dispBeamColumn', i+1, i+1, i+2, 1, 1)
```

---

### Comparación: Force-Based vs Displacement-Based

| Aspecto | Force-Based | Displacement-Based |
|---------|-------------|-------------------|
| **Formulación** | Fuerzas exactas | Desplazamientos interpolados |
| **Elementos por miembro** | 1-2 | 4-8 |
| **Precisión (rótula plástica)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Velocidad** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Convergencia** | Puede fallar | Siempre converge |
| **Plasticidad distribuida** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Recomendado para** | Pushover, análisis sísmico | Análisis rápidos, preliminares |

**Recomendación general:**
- Para análisis no-lineal con rótulas plásticas → **forceBeamColumn**
- Para análisis elástico → **elasticBeamColumn**
- Para análisis muy no-lineal con problemas de convergencia → **dispBeamColumn**

---

## Elementos Truss

### Comando Básico

```python
ops.element('Truss', eleTag, *eleNodes, A, matTag, 
            '-rho', rho, '-cMass', cFlag, '-doRayleigh', rFlag)
```

**Parámetros:**
- `A`: Área de la sección transversal
- `matTag`: Material uniaxial
- `rho`: Densidad de masa (opcional)
- `cFlag`: Flag para masa consistente (opcional)
- `rFlag`: Flag para amortiguamiento Rayleigh (opcional)

**Teoría:**

Elemento que **solo resiste fuerzas axiales** (tensión/compresión):

$$F = \frac{EA}{L} \cdot \Delta L$$

**Matriz de rigidez (2D, coordenadas globales):**

$$\mathbf{K} = \frac{EA}{L} \begin{bmatrix}
c^2 & cs & -c^2 & -cs \\
cs & s^2 & -cs & -s^2 \\
-c^2 & -cs & c^2 & cs \\
-cs & -s^2 & cs & s^2
\end{bmatrix}$$

Donde:
- $c = \cos\theta$ (componente en X)
- $s = \sin\theta$ (componente en Z)

**Características:**
- 2 DOF por nodo en 2D (ux, uz)
- 3 DOF por nodo en 3D (ux, uy, uz)
- Sin rigidez a flexión ni corte
- Ideal para: armaduras, arriostramientos, cables

**Ejemplo de armadura 2D:**
```python
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 2)  # Solo traslaciones

# Nodos de armadura simple
ops.node(1, 0.0, 0.0)
ops.node(2, 2.0, 0.0)
ops.node(3, 1.0, 1.5)

# Apoyos
ops.fix(1, 1, 1)
ops.fix(2, 0, 1)

# Material
E = 200e6  # kPa
ops.uniaxialMaterial('Elastic', 1, E)

# Área de barras
A = 0.001  # m² (sección circular 35mm diám aprox)

# Elementos de armadura
ops.element('Truss', 1, 1, 3, A, 1)  # Diagonal izq
ops.element('Truss', 2, 2, 3, A, 1)  # Diagonal der
ops.element('Truss', 3, 1, 2, A, 1)  # Horizontal

# Carga en nodo superior
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)
ops.load(3, 0.0, -50.0)  # 50 kN hacia abajo

# Análisis...
```

### Truss Corotacional

```python
ops.element('corotTruss', eleTag, *eleNodes, A, matTag)
```

**Diferencia:** Considera grandes deformaciones (formulación corotacional).

**Cuándo usar:**
- Cables que puedan aflojarse
- Deformaciones muy grandes
- Análisis de colapso

---

## Elementos Shell

### Shell MITC4

**Comando:**
```python
ops.element('ShellMITC4', eleTag, *eleNodes, secTag)
```

**Parámetros:**
- `eleNodes`: 4 nodos en orden **antihorario**
- `secTag`: Sección tipo plateFiber o elasticMembranePlate

**Teoría:**

Elemento de **cascarón cuadrilateral de 4 nodos**:
- Combina comportamiento de membrana (in-plane) y placa (out-of-plane)
- 6 DOF por nodo (3 traslaciones + 3 rotaciones)
- Basado en teoría de Mindlin-Reissner (incluye deformación por corte)

**MITC** = Mixed Interpolation of Tensorial Components
- Evita "shear locking" (bloqueo por corte)
- Mejor precisión en elementos delgados

**Aplicaciones:**
- Muros de corte
- Losas
- Tanques
- Cascarones

**Definir sección para shell:**
```python
# Sección elástica
ops.section('ElasticMembranePlateSection', secTag, E, nu, h, rho)
```

O sección de fibra:
```python
ops.section('PlateFiber', secTag, matTag, h)
```

**Ejemplo: Muro de corte**
```python
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Nodos del panel (2m x 2m)
ops.node(1, 0.0, 0.0, 0.0)
ops.node(2, 2.0, 0.0, 0.0)
ops.node(3, 2.0, 0.0, 2.0)
ops.node(4, 0.0, 0.0, 2.0)

# Fijar base
ops.fix(1, 1, 1, 1, 1, 1, 1)
ops.fix(2, 1, 1, 1, 1, 1, 1)

# Sección del muro (20cm espesor)
E = 25e6    # kPa (concreto 25 MPa aprox)
nu = 0.2    # Relación de Poisson
h = 0.20    # m (espesor)
rho = 0.0   # Densidad (si no interesa dinámica)

ops.section('ElasticMembranePlateSection', 1, E, nu, h, rho)

# Elemento shell (nodos en sentido antihorario)
ops.element('ShellMITC4', 1, 1, 2, 3, 4, 1)
```

**Importante:** El orden de nodos define la normal del elemento (regla mano derecha).

---

## Comparación y Selección

### Guía de Selección de Elementos

```
┌─────────────────────────────────────────────┐
│ ¿Tu estructura es?                          │
└─────────────────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
┌────────┐         ┌──────────┐
│ Barras │         │ Superficies│
│ 1D     │         │ 2D           │
└────────┘         └──────────┘
    │                    │
    │                    └──→ ShellMITC4
    │
    ├──→ Solo axial? ──→ Truss
    │
    └──→ Flexión?
            │
            ├──→ Elástico? ──→ elasticBeamColumn
            │
            └──→ No-lineal?
                    │
                    ├──→ Rótulas plásticas? ──→ forceBeamColumn
                    │
                    └──→ Distributed plasticity? ──→ dispBeamColumn
```

### Tabla Resumen

| Elemento | Tipo | DOF/nodo | Lineal | No-lineal | Uso Principal |
|----------|------|----------|--------|-----------|---------------|
| `elasticBeamColumn` | Frame | 3(2D) 6(3D) | ✅ | ❌ | Análisis elástico |
| `forceBeamColumn` | Frame | 3(2D) 6(3D) | ✅ | ✅ | Pushover, plasticidad |
| `dispBeamColumn` | Frame | 3(2D) 6(3D) | ✅ | ✅ | Alternativa a force |
| `Truss` | Axial | 2(2D) 3(3D) | ✅ | ✅ | Armaduras, arriostres |
| `ShellMITC4` | Surface | 6 | ✅ | ✅ | Muros, losas, shells |

---

## Puntos Clave

✅ **elasticBeamColumn** para análisis modal y lineal  
✅ **forceBeamColumn** es gold standard para análisis sísmico no-lineal  
✅ **Truss** solo para elementos que trabajan a axial puro  
✅ **ShellMITC4** para muros de corte y losas  
✅ Siempre definir **geomTransf** antes de crear elementos frame

---

## Próximo Capítulo

Continúa con **[Construcción de Modelos 3D](04-modelo-3d.md)** para aprender a ensamblar estos elementos en estructuras tridimensionales.
