# Materiales y Secciones en OpenSees

## Índice
1. [Introducción](#introducción)
2. [Materiales Uniaxiales](#materiales-uniaxiales)
3. [Secciones](#secciones)
4. [Teoría Constitutiva](#teoría-constitutiva)
5. [Ejemplos Prácticos](#ejemplos-prácticos)

---

## Introducción

Los **materiales** definen la relación esfuerzo-deformación (ley constitutiva), mientras que las **secciones** agregan el comportamiento del material sobre una sección transversal completa.

### Jerarquía de Definición

```
Material (σ-ε) → Sección (N-M) → Elemento (F-u)
```

- **Material**: Comportamiento uniaxial (1D): $\sigma = f(\varepsilon)$
- **Sección**: Comportamiento seccional: $N, M = f(\varepsilon, \kappa)$
- **Elemento**: Respuesta global del elemento

---

## Materiales Uniaxiales

### 1. Material Elástico

**Comando:**
```python
ops.uniaxialMaterial('Elastic', matTag, E, eta=0.0, Eneg=None)
```

**Parámetros:**
- `matTag`: Identificador único del material
- `E`: Módulo de elasticidad (Young's modulus)
- `eta`: Tangente de amortiguamiento (opcional, default=0)
- `Eneg`: Módulo en compresión (opcional, default=E)

**Teoría:**

Relación lineal perfecta:
$$\sigma = E \cdot \varepsilon$$

```
    σ (Esfuerzo)
    ↑
    |      ╱
    |     ╱
    |    ╱  Pendiente = E
    |   ╱
    |  ╱
    | ╱
    |╱________________→ ε (Deformación)
```

**Uso típico:**
- Análisis elástico lineal
- Materiales que permanecen elásticos
- Modelos preliminares

**Ejemplo:**
```python
# Acero estructural
E_steel = 200e6  # kPa (200 GPa)
ops.uniaxialMaterial('Elastic', 1, E_steel)

# Concreto (módulo secante)
f_c = 30e3  # kPa (30 MPa)
E_c = 4700 * (f_c**0.5)  # ACI 318
ops.uniaxialMaterial('Elastic', 2, E_c)
```

---

### 2. Material Steel02

**Comando:**
```python
ops.uniaxialMaterial('Steel02', matTag, Fy, E0, b, 
                     R0=15, cR1=0.925, cR2=0.15,
                     a1=0.0, a2=1.0, a3=0.0, a4=1.0,
                     sigInit=0.0)
```

**Parámetros principales:**
- `Fy`: Esfuerzo de fluencia
- `E0`: Módulo elástico inicial
- `b`: Relación de endurecimiento por deformación (strain-hardening ratio) = $E_{sh}/E_0$

**Parámetros de calibración (Giuffre-Menegotto-Pinto):**
- `R0`, `cR1`, `cR2`: Controlan la transición de elástico a plástico
- `a1`, `a2`, `a3`, `a4`: Controlan endurecimiento isótropo

**Teoría:**

Modelo constitutivo de acero con:
- **Efecto Bauschinger**: Material "recuerda" deformación plástica previa
- **Endurecimiento por deformación**: La resistencia aumenta después de fluencia
- **Endurecimiento isótropo**: Cambio de límite elástico con ciclado

```
    σ
    ↑
 Fy |     ╱────── Endurecimiento (pendiente = b·E0)
    |    ╱
    |   ╱
    |  ╱  Elástico (pendiente = E0)
    | ╱
    |╱
    |________________→ ε
    |    ╲
    |     ╲  Efecto Bauschinger
 -Fy|______╲
```

**Ejemplo:**
```python
# Acero A36
Fy = 250e3      # kPa (250 MPa)
E0 = 200e6      # kPa (200 GPa)
b = 0.01        # Endurecimiento 1%

ops.uniaxialMaterial('Steel02', 10, Fy, E0, b)
```

**Valores típicos de `b`:**
- Acero estructural suave: b = 0.001 - 0.01
- Acero de refuerzo: b = 0.01 - 0.03
- Acero de alta resistencia: b = 0.005 - 0.015

---

### 3. Material Concrete01

**Comando:**
```python
ops.uniaxialMaterial('Concrete01', matTag, fpc, epsc0, fpcu, epsU)
```

**Parámetros:**
- `fpc`: Resistencia máxima a compresión (valor **negativo**)
- `epsc0`: Deformación al esfuerzo máximo (valor **negativo**)
- `fpcu`: Resistencia de aplastamiento (valor **negativo**)
- `epsU`: Deformación última (valor **negativo**)

**Teoría:**

Modelo de Kent-Scott-Park para concreto no confinado:

```
    σ
    |
  0 |________________
    |╲              ↘ Tensión (no resiste)
    | ╲
    |  ╲
    |   ╲___
    |       ╲___      Softening
 fpc|           ╲___
    |                ╲___
fpcu|                    ╲___
    |________________________→ ε
        epsc0            epsU
```

**Ecuación de esfuerzo:**

Para $\varepsilon < \varepsilon_{c0}$:
$$\sigma_c = f'_c \left[2\frac{\varepsilon}{\varepsilon_{c0}} - \left(\frac{\varepsilon}{\varepsilon_{c0}}\right)^2\right]$$

Para $\varepsilon_{c0} < \varepsilon < \varepsilon_u$:
$$\sigma_c = f'_c \left[1 - Z(\varepsilon - \varepsilon_{c0})\right]$$

**Ejemplo:**
```python
# Concreto f'c = 30 MPa
fpc = -30e3       # kPa (negativo!)
epsc0 = -0.002    # Deformación típica al pico
fpcu = -0.2*fpc   # 20% de resistencia residual
epsU = -0.005     # Deformación última

ops.uniaxialMaterial('Concrete01', 20, fpc, epsc0, fpcu, epsU)
```

**Valores típicos:**
- $\varepsilon_{c0}$ ≈ -0.002 (concreto no confinado)
- $\varepsilon_{c0}$ ≈ -0.004 a -0.006 (concreto confinado)
- $\varepsilon_u$ ≈ -0.005 a -0.02 (depende del confinamiento)

---

### 4. Material Concrete02

**Comando:**
```python
ops.uniaxialMaterial('Concrete02', matTag, fpc, epsc0, fpcu, epsU,
                     lambda_param, ft, Ets)
```

**Parámetros adicionales:**
- `lambda_param`: Relación entre descarga y pendiente inicial
- `ft`: Resistencia a tensión
- `Ets`: Rigidez de tensión (softening en tensión)

**Mejoras sobre Concrete01:**
- Incluye resistencia a tensión
- Mejor modelado de descarga/recarga
- Más apropiado para análisis cíclico

**Ejemplo:**
```python
# Concreto f'c = 30 MPa con tensión
fpc = -30e3
epsc0 = -0.002
fpcu = -6e3
epsU = -0.005
lambda_param = 0.1
ft = 0.1 * abs(fpc)  # 10% de f'c (aproximación)
Ets = 0.05 * E_c     # Rigidez descarga tensión

ops.uniaxialMaterial('Concrete02', 21, fpc, epsc0, fpcu, epsU,
                     lambda_param, ft, Ets)
```

---

### 5. Otros Materiales Útiles

#### Elastic-Perfectly Plastic (EPP)

```python
ops.uniaxialMaterial('ElasticPP', matTag, E, epsyP, epsyN=epsyP, eps0=0.0)
```

- Elástico hasta fluencia, luego plástico perfecto
- `epsyP`: Deformación de fluencia positiva
- `epsyN`: Deformación de fluencia negativa

#### Hysteretic

```python
ops.uniaxialMaterial('Hysteretic', matTag, *args)
```

- Curva multilineal arbitraria
- Control completo de histéresis
- Útil para dispositivos de disipación

---

## Secciones

### 1. Sección Elástica

**Comando:**
```python
ops.section('Elastic', secTag, E, A, Iz, Iy=0.0, G=0.0, J=0.0, 
            alphaY=0.0, alphaZ=0.0)
```

**Parámetros (para sección 3D):**
- `E`: Módulo de elasticidad
- `A`: Área de la sección
- `Iz`: Momento de inercia sobre eje z local
- `Iy`: Momento de inercia sobre eje y local
- `G`: Módulo de corte
- `J`: Constante torsional
- `alphaY`, `alphaZ`: Factores de forma de corte (opcional)

**Teoría:**

Relaciones constitutivas elásticas:
$$N = EA \cdot \varepsilon$$
$$M_y = EI_y \cdot \kappa_y$$
$$M_z = EI_z \cdot \kappa_z$$
$$T = GJ \cdot \phi$$

Donde:
- $N$ = fuerza axial
- $M$ = momento flector
- $T$ = torque
- $\varepsilon$ = deformación axial
- $\kappa$ = curvatura
- $\phi$ = torsión por unidad de longitud

**Ejemplo para viga IPE 300:**

```python
# Propiedades geométricas IPE 300
h = 0.300   # m (altura)
b = 0.150   # m (ancho de alas)
tw = 0.0071 # m (espesor de alma)
tf = 0.0107 # m (espesor de alas)

# Área y momentos de inercia (de tablas o cálculo)
A = 5.38e-3    # m²
Iz = 8.36e-5   # m⁴ (inercia mayor, flexión fuerte)
Iy = 6.04e-6   # m⁴ (inercia menor, flexión débil)
J = 2.01e-7    # m⁴ (constante torsional)

# Material
E = 200e6   # kPa
G = E / (2*(1+0.3))  # G = E/(2(1+ν)), ν≈0.3 para acero

ops.section('Elastic', 1, E, A, Iz, Iy, G, J)
```

**Para sección 2D:**
```python
# Solo necesitas E, A, I
ops.section('Elastic', 2, E, A, Iz)
```

---

### 2. Sección de Fibra

**Concepto:**

La sección se discretiza en "fibras" (pequeñas áreas), cada una con un material uniaxial.

```
Vista de sección transversal:
    ___________________
   |  ●  ●  ●  ●  ●   |  ← Fibras de acero (refuerzo superior)
   |                  |
   |  ○  ○  ○  ○  ○   |  ← Fibras de concreto
   |  ○  ○  ○  ○  ○   |
   |                  |
   |_ ●  ●  ●  ●  ● __|  ← Fibras de acero (refuerzo inferior)
```

**Comando base:**
```python
ops.section('Fiber', secTag, '-GJ', GJ)
```

**Agregar fibras individuales:**
```python
ops.fiber(yLoc, zLoc, A, matTag)
```
- `yLoc`, `zLoc`: Posición del centroide de la fibra
- `A`: Área de la fibra
- `matTag`: Material asignado

**Agregar parches (patches):**
```python
ops.patch('rect', matTag, numSubdivY, numSubdivZ, yI, zI, yJ, zJ)
```
- `numSubdivY`, `numSubdivZ`: Subdivisiones en Y y Z
- `yI, zI, yJ, zJ`: Coordenadas de esquinas opuestas del rectángulo

**Agregar capas de refuerzo:**
```python
ops.layer('straight', matTag, numFiber, areaFiber, yStart, zStart, yEnd, zEnd)
```

**Teoría:**

**Hipótesis de Bernoulli:** Las secciones planas permanecen planas.

$$\varepsilon(y) = \varepsilon_0 + y \cdot \kappa$$

Donde:
- $\varepsilon_0$ = deformación en el eje neutro
- $\kappa$ = curvatura
- $y$ = distancia desde el eje neutro

**Integración numérica:**
$$N = \sum_{i=1}^{n_{fibras}} \sigma_i \cdot A_i$$
$$M = \sum_{i=1}^{n_{fibras}} \sigma_i \cdot A_i \cdot y_i$$

**Ventajas:**
- Captura comportamiento no-lineal de la sección
- Permite fluencia gradual
- Modela precisamente secciones de concreto reforzado

---

### Ejemplo Completo: Sección de Viga de Concreto Reforzado

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# ============================================
# GEOMETRÍA DE LA SECCIÓN
# ============================================
h = 0.60      # m (altura total)
b = 0.30      # m (ancho)
cover = 0.04  # m (recubrimiento)

# Dimensiones del núcleo (core)
h_core = h - 2*cover
b_core = b - 2*cover

# Coordenadas
y1 = -b/2
y2 = b/2
z1 = -h/2
z2 = h/2

y1_core = -b_core/2
y2_core = b_core/2
z1_core = -h_core/2
z2_core = h_core/2

# ============================================
# MATERIALES
# ============================================
# Concreto no confinado (cover)
fpc_unconf = -30e3    # kPa
epsc0_unconf = -0.002
fpcu_unconf = -6e3
epsU_unconf = -0.005
ops.uniaxialMaterial('Concrete01', 1, fpc_unconf, epsc0_unconf, 
                     fpcu_unconf, epsU_unconf)

# Concreto confinado (core)
fpc_conf = -36e3      # 20% más resistencia por confinamiento
epsc0_conf = -0.004
fpcu_conf = -7.2e3
epsU_conf = -0.012    # Mayor ductilidad
ops.uniaxialMaterial('Concrete01', 2, fpc_conf, epsc0_conf,
                     fpcu_conf, epsU_conf)

# Acero de refuerzo
Fy = 420e3   # kPa (420 MPa, grado 60)
E0 = 200e6   # kPa
b_steel = 0.02
ops.uniaxialMaterial('Steel02', 3, Fy, E0, b_steel)

# ============================================
# DEFINIR SECCIÓN DE FIBRA
# ============================================
ops.section('Fiber', 1)

# Patch de concreto del núcleo
ops.patch('rect', 2, 10, 10, y1_core, z1_core, y2_core, z2_core)

# Patches de concreto de recubrimiento
# Superior
ops.patch('rect', 1, 10, 2, y1, z2_core, y2, z2)
# Inferior
ops.patch('rect', 1, 10, 2, y1, z1, y2, z1_core)
# Izquierdo
ops.patch('rect', 1, 2, 10, y1, z1_core, y1_core, z2_core)
# Derecho
ops.patch('rect', 1, 2, 10, y2_core, z1_core, y2, z2_core)

# Refuerzo superior (4 barras de 25mm)
numBars_top = 4
d_bar = 0.025  # m (diámetro)
A_bar = 3.14159 * (d_bar/2)**2
y_bar_start = y1_core
y_bar_end = y2_core
z_bar_top = z2_core - 0.01  # 1cm desde cara interior

ops.layer('straight', 3, numBars_top, A_bar,
         y_bar_start, z_bar_top, y_bar_end, z_bar_top)

# Refuerzo inferior (4 barras de 25mm)
z_bar_bot = z1_core + 0.01
ops.layer('straight', 3, numBars_top, A_bar,
         y_bar_start, z_bar_bot, y_bar_end, z_bar_bot)

print("✓ Sección de fibra creada exitosamente")
print(f"  - Núcleo de concreto: {h_core*1000:.0f}x{b_core*1000:.0f} mm")
print(f"  - Refuerzo: {numBars_top*2} barras ϕ{d_bar*1000:.0f}mm")
```

---

## Teoría Constitutiva

### Comportamiento Elástico vs Inelástico

**Elástico:**
- Reversible (path-independent)
- Sin deformación permanente
- $\sigma = E \varepsilon$ (lineal) o $\sigma = f(\varepsilon)$ (no-lineal elástico)

**Inelástico (Plástico):**
- Irreversible (path-dependent)
- Deformación permanente tras descarga
- Requiere criterio de fluencia

### Endurecimiento

**Isótropo:** El límite elástico cambia uniformemente en todas direcciones
**Cinemático:** El centro del límite elástico se mueve (efecto Bauschinger)
**Mixto:** Combinación de ambos (Steel02 usa este)

### Curvas Histeréticas

Para análisis cíclico (sísmico), la forma de los lazos de histéresis es crítica:

```
    σ
    ↑
    |    ╱╲
    |   ╱  ╲     ← Lazo de histéresis
    |  ╱    ╲╱
    | ╱    ╱
    |╱____╱______→ ε
```

**Reglas de histéresis:**
- Masing rules (descarga con 2E)
- Degradación de rigidez
- Pinching (pellizco)

---

## Ejemplos Prácticos

### Comparación de Materiales de Concreto

```python
import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt

ops.wipe()

# Definir materiales
fpc = -30e3
epsc0 = -0.002

# Concrete01
ops.uniaxialMaterial('Concrete01', 1, fpc, epsc0, -0.2*fpc, -0.005)

# Elastic equivalente
E_c = 2*fpc/epsc0
ops.uniaxialMaterial('Elastic', 2, E_c)

# Simular respuesta
strains = np.linspace(0, -0.006, 100)
stress_c01 = []
stress_elastic = []

for eps in strains:
    ops.uniaxialMaterial('Concrete01', 1, fpc, epsc0, -0.2*fpc, -0.005)
    ops.setStrain(1, eps)
    stress_c01.append(ops.getStress(1))
    
    ops.uniaxialMaterial('Elastic', 2, E_c)
    ops.setStrain(2, eps)
    stress_elastic.append(ops.getStress(2))

# Graficar
plt.plot(strains, stress_c01, label='Concrete01')
plt.plot(strains, stress_elastic, '--', label='Elastic')
plt.xlabel('Deformación')
plt.ylabel('Esfuerzo (kPa)')
plt.legend()
plt.grid(True)
plt.title('Comparación de modelos de concreto')
plt.show()
```

---

## Resumen

| Material | Uso Principal | Lineal? | Cíclico? |
|----------|---------------|---------|----------|
| Elastic | Análisis lineal | Sí | N/A |
| Steel02 | Acero estructural/refuerzo | No | Sí |
| Concrete01 | Concreto (monotónico) | No | Limitado |
| Concrete02 | Concreto (cíclico) | No | Sí |

**Próximo capítulo:** [Elementos Estructurales](03-elementos.md)
