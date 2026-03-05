# Análisis Modal en OpenSees

## Índice
1. [Introducción](#introducción)
2. [Teoría de Análisis Modal](#teoría-de-análisis-modal)
3. [Configuración en OpenSees](#configuración-en-opensees)
4. [Extracción de Propiedades Modales](#extracción-de-propiedades-modales)
5. [Ejemplos Completos](#ejemplos-completos)

---

## Introducción

El **análisis modal** (análisis de valores propios o eigenvalue analysis) calcula:
- **Frecuencias naturales** de vibración
- **Períodos** fundamentales y superiores
- **Formas modales** (mode shapes)
- **Participación modal** (modal mass participation)

### Aplicaciones

- Verificar períodos fundamentales para diseño sísmico
- Identificar modos que contribuyen a la respuesta sísmica
- Input para análisis espectral
- Validación del modelo (comparar con fórmulas empíricas)

---

## Teoría de Análisis Modal

### Ecuación de Movimiento Libre

Sin amortiguamiento ni fuerzas externas:

$$\mathbf{M} \ddot{\mathbf{U}} + \mathbf{K} \mathbf{U} = 0$$

Donde:
- $\mathbf{M}$ = matriz de masa
- $\mathbf{K}$ = matriz de rigidez
- $\ddot{\mathbf{U}}$ = vector de aceleraciones
- $\mathbf{U}$ = vector de desplazamientos

### Solución Armónica

Asumir solución armónica:
$$\mathbf{U}(t) = \boldsymbol{\phi} \sin(\omega t)$$

Sustituyendo:
$$(-\omega^2 \mathbf{M} + \mathbf{K}) \boldsymbol{\phi} = 0$$

### Problema de Valores Propios

$$\mathbf{K} \boldsymbol{\phi}_i = \lambda_i \mathbf{M} \boldsymbol{\phi}_i$$

Donde:
- $\lambda_i = \omega_i^2$ = valor propio (eigenvalue)
- $\boldsymbol{\phi}_i$ = vector propio (eigenvector) = forma modal
- $\omega_i$ = frecuencia angular natural del modo $i$

### Propiedades Modales

**Frecuencia angular (rad/s):**
$$\omega_i = \sqrt{\lambda_i}$$

**Frecuencia cíclica (Hz):**
$$f_i = \frac{\omega_i}{2\pi}$$

**Período (s):**
$$T_i = \frac{1}{f_i} = \frac{2\pi}{\omega_i}$$

### Ortogonalidad de Modos

Los modos son ortogonales respecto a las matrices de masa y rigidez:

$$\boldsymbol{\phi}_i^T \mathbf{M} \boldsymbol{\phi}_j = 
\begin{cases}
M_i & \text{si } i = j \\
0 & \text{si } i \neq j
\end{cases}$$

$$\boldsymbol{\phi}_i^T \mathbf{K} \boldsymbol{\phi}_j = 
\begin{cases}
K_i & \text{si } i = j \\
0 & \text{si } i \neq j
\end{cases}$$

Donde $M_i$ = masa modal, $K_i$ = rigidez modal.

### Normalización

OpenSees normaliza los modos tal que:
$$\boldsymbol{\phi}_i^T \mathbf{M} \boldsymbol{\phi}_i = 1$$

Entonces:
$$\omega_i^2 = \boldsymbol{\phi}_i^T \mathbf{K} \boldsymbol{\phi}_i$$

### Participación Modal

**Factor de participación modal:**
$$\Gamma_i = \frac{\boldsymbol{\phi}_i^T \mathbf{M} \mathbf{r}}{\boldsymbol{\phi}_i^T \mathbf{M} \boldsymbol{\phi}_i}$$

Donde $\mathbf{r}$ = vector de influencia (1's en dirección de excitación, 0's en otras).

**Masa efectiva modal:**
$$m_{eff,i} = \frac{(\boldsymbol{\phi}_i^T \mathbf{M} \mathbf{r})^2}{\boldsymbol{\phi}_i^T \mathbf{M} \boldsymbol{\phi}_i}$$

**Porcentaje de masa modal:**
$$\% m_i = \frac{m_{eff,i}}{\sum m_j} \times 100\%$$

### Criterio de Suficiencia

Los códigos sísmicos típicamente requieren que los modos incluidos sumen al menos **90%** de la masa total en cada dirección.

---

## Configuración en OpenSees

### Paso 1: Definir Masas

**Crítico:** Sin masas, no hay análisis modal.

```python
# Opción 1: Masa en nodos
ops.node(tag, x, y, z, '-mass', mx, my, mz, Ix, Iy, Iz)

# Opción 2: Comando mass separado
ops.mass(nodeTag, mx, my, mz, Ix, Iy, Iz)

# Opción 3: Masa de elementos
ops.element('...', ..., '-mass', massDens)
```

**Importante:** Las masas rotacionales (Ix, Iy, Iz) generalmente son pequeñas o cero para masas concentradas.

### Paso 2: Configurar Sistema de Análisis

```python
# Sistema de ecuaciones para eigenvalues
ops.system('BandGeneral')  # o 'FullGeneral', 'UmfPack'

# Numerador
ops.numberer('RCM')

# Constraints (importante si hay MPC)
ops.constraints('Transformation')
```

### Paso 3: Ejecutar Análisis de Eigenvalues

```python
numModes = 10  # Número de modos a extraer
eigenvalues = ops.eigen(numModes)
```

O especificar solver:

```python
eigenvalues = ops.eigen('-fullGenLapack', numModes)
# o
eigenvalues = ops.eigen('-genBandArpack', numModes)
```

**Retorno:** Lista de eigenvalues $[\lambda_1, \lambda_2, ..., \lambda_n]$

### Solvers Disponibles

| Solver | Uso | Observaciones |
|--------|-----|---------------|
| `-fullGenLapack` | Modelos pequeños | Más robusto |
| `-genBandArpack` | Modelos grandes | Más eficiente |
| `-symmBandLapack` | Matriz simétrica en banda | Rápido para estructuras regulares |

---

## Extracción de Propiedades Modales

### Calcular Períodos y Frecuencias

```python
import math

eigenvalues = ops.eigen(numModes)

for i, eigenvalue in enumerate(eigenvalues, start=1):
    omega = math.sqrt(eigenvalue)      # rad/s
    freq = omega / (2 * math.pi)       # Hz
    period = 1.0 / freq                # s
    
    print(f"Modo {i}:")
    print(f"  ω = {omega:.3f} rad/s")
    print(f"  f = {freq:.3f} Hz")
    print(f"  T = {period:.3f} s")
```

### Extraer Formas Modales

```python
# Para un nodo específico en un modo específico
mode_num = 1
node_tag = 10
dof = 1  # DOF de interés (1 a 6)

phi = ops.nodeEigenvector(node_tag, mode_num, dof)
```

**Uso completo:**
```python
# Almacenar todas las formas modales
node_list = [1, 2, 3, 4]  # Nodos de interés
num_modes = 5
dofs = [1, 2, 3]  # DOFs de interés

mode_shapes = {}

for mode in range(1, num_modes + 1):
    mode_shapes[mode] = {}
    for node in node_list:
        mode_shapes[mode][node] = {}
        for dof in dofs:
            phi = ops.nodeEigenvector(node, mode, dof)
            mode_shapes[mode][node][dof] = phi

# Acceso: mode_shapes[modo][nodo][dof]
print(f"Modo 1, Nodo 2, DOF 1: {mode_shapes[1][2][1]}")
```

### Grabar Formas Modales en Archivo

```python
# Recorder para eigenve ctors
ops.recorder('Node', '-file', f'mode_{mode}.out', '-node', *node_list,
             '-dof', *dofs, 'eigen', mode)
```

---

## Ejemplos Completes

### Ejemplo 1: Pórtico 2D - 1 Piso

```python
import openseespy.opensees as ops
import math

# ============================================
# MODELO
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Geometría
H = 3.0  # m, altura
L = 4.0  # m, luz

# Nodos
ops.node(1, 0.0, 0.0)
ops.node(2, L, 0.0)
ops.node(3, 0.0, H)
ops.node(4, L, H)

# Apoyos
ops.fix(1, 1, 1, 1)
ops.fix(2, 1, 1, 1)

# Masas (solo en nodos superiores)
mass = 50.0  # toneladas (kN·s²/m)
ops.mass(3, mass, mass, 0.0)
ops.mass(4, mass, mass, 0.0)

# Material y sección
E = 200e6  # kPa
A_col = 0.01
I_col = 1e-4
A_beam = 0.008
I_beam = 8e-5

ops.geomTransf('Linear', 1)

# Elementos
ops.element('elasticBeamColumn', 1, 1, 3, A_col, E, I_col, 1)
ops.element('elasticBeamColumn', 2, 2, 4, A_col, E, I_col, 1)
ops.element('elasticBeamColumn', 3, 3, 4, A_beam, E, I_beam, 1)

# ============================================
# ANÁLISIS MODAL
# ============================================
num_modes = 3

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')

eigenvalues = ops.eigen(num_modes)

print("=" * 50)
print("ANÁLISIS MODAL - PÓRTICO 2D")
print("=" * 50)

for i, lam in enumerate(eigenvalues, start=1):
    omega = math.sqrt(lam)
    freq = omega / (2 * math.pi)
    period = 1.0 / freq
    
    print(f"\nModo {i}:")
    print(f"  Eigenvalue (λ):     {lam:.2e}")
    print(f"  Frecuencia angular: {omega:.3f} rad/s")
    print(f"  Frecuencia:         {freq:.3f} Hz")
    print(f"  Período:            {period:.3f} s")

# ============================================
# FORMAS MODALES
# ============================================
print("\n" + "=" * 50)
print("FORMAS MODALES (normalizado por máximo)")
print("=" * 50)

for mode in range(1, num_modes + 1):
    print(f"\nModo {mode}:")
    
    # Extraer amplitudes en DOF 1 (X) para nodos 3 y 4
    phi_3x = ops.nodeEigenvector(3, mode, 1)
    phi_4x = ops.nodeEigenvector(4, mode, 1)
    
    # Normalizar por máximo
    max_val = max(abs(phi_3x), abs(phi_4x))
    if max_val > 0:
        phi_3x_norm = phi_3x / max_val
        phi_4x_norm = phi_4x / max_val
    else:
        phi_3x_norm = phi_3x
        phi_4x_norm = phi_4x
    
    print(f"  Nodo 3 (X): {phi_3x_norm:+.3f}")
    print(f"  Nodo 4 (X): {phi_4x_norm:+.3f}")

ops.wipe()
```

**Salida esperada:**
```
==================================================
ANÁLISIS MODAL - PÓRTICO 2D
==================================================

Modo 1:
  Eigenvalue (λ):     3.78e+01
  Frecuencia angular: 6.147 rad/s
  Frecuencia:         0.978 Hz
  Período:            1.022 s

Modo 2:
  ... (Modos de vibración superiores)

==================================================
FORMAS MODALES
==================================================

Modo 1:
  Nodo 3 (X): +1.000
  Nodo 4 (X): +1.000  ← Ambos nodos se mueven juntos (traslación lateral)
```

---

### Ejemplo 2: Edificio 3D de 3 Pisos con Participación Modal

```python
import openseespy.opensees as ops
import math
import numpy as np

# ============================================
# MODELO
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Parámetros
num_stories = 3
story_height = 3.5  # m
bay_width = 5.0     # m

# Masas por piso (toneladas)
mass_per_floor = 200.0  # kN·s²/m

# Nodos (simplificado: 1 nodo por piso)
for i in range(num_stories + 1):
    z = i * story_height
    ops.node(i+1, 0, 0, z)
    
    if i == 0:
        ops.fix(i+1, 1, 1, 1, 1, 1, 1)  # Base fija
    else:
        # Masa solo en pisos superiores
        ops.mass(i+1, mass_per_floor, mass_per_floor, mass_per_floor,
                 0.0, 0.0, 0.0)

# Propiedades
E = 25e6
A = 0.5
I = 0.05

ops.geomTransf('Linear', 1, 1, 0, 0)

# Elementos (columnas equivalentes)
for i in range(num_stories):
    ops.element('elasticBeamColumn', i+1, i+1, i+2, A, E, I, 1)

# ============================================
# ANÁLISIS MODAL
# ============================================
num_modes = num_stories  # 3 modos para 3 pisos

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')

eigenvalues = ops.eigen(num_modes)

# Almacenar períodos
periods = []
for lam in eigenvalues:
    omega = math.sqrt(lam)
    T = 2 * math.pi / omega
    periods.append(T)

print("=" * 60)
print("PERÍODOS MODALES")
print("=" * 60)
for i, T in enumerate(periods, start=1):
    print(f"Modo {i}: T = {T:.3f} s")

# ============================================
# CALCULAR PARTICIPACIÓN MODAL
# ============================================
# Extraer formas modales en dirección X (DOF 1)
mode_shapes_x = np.zeros((num_stories, num_modes))

for mode in range(1, num_modes + 1):
    for floor in range(1, num_stories + 1):
        node = floor + 1  # Nodos 2, 3, 4 para pisos 1, 2, 3
        mode_shapes_x[floor-1, mode-1] = ops.nodeEigenvector(node, mode, 1)

# Matriz de masa (diagonal para masas concentradas)
M = np.diag([mass_per_floor] * num_stories)

# Vector de influencia (excitación en X)
r = np.ones(num_stories)

print("\n" + "=" * 60)
print("PARTICIPACIÓN MODAL")
print("=" * 60)

total_mass = mass_per_floor * num_stories
cumulative_participation = 0.0

for mode in range(num_modes):
    phi = mode_shapes_x[:, mode]
    
    # Factor de participación
    gamma = (phi.T @ M @ r) / (phi.T @ M @ phi)
    
    # Masa efectiva
    m_eff = (phi.T @ M @ r)**2 / (phi.T @ M @ phi)
    
    # Porcentaje
    percent = (m_eff / total_mass) * 100
    cumulative_participation += percent
    
    print(f"\nModo {mode+1}:")
    print(f"  Período:               {periods[mode]:.3f} s")
    print(f"  Factor participación:  {gamma:.3f}")
    print(f"  Masa efectiva:         {m_eff:.2f} ton")
    print(f"  % Masa modal:          {percent:.1f}%")
    print(f"  % Acumulado:           {cumulative_participation:.1f}%")

if cumulative_participation >= 90:
    print(f"\n✓ Se cumple criterio 90% ({cumulative_participation:.1f}%)")
else:
    print(f"\n✗ NO se cumple criterio 90% ({cumulative_participation:.1f}%)")

ops.wipe()
```

---

### Ejemplo 3: Comparación con Fórmula Empírica

```python
import openseespy.opensees as ops
import math

# Edificio de 5 pisos para comparar con fórmula de código

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

num_stories = 5
H_story = 3.0  # m
mass_per_floor = 150.0  # ton

# Nodos
for i in range(num_stories + 1):
    z = i * H_story
    ops.node(i+1, 0, 0, z)
    
    if i == 0:
        ops.fix(i+1, 1, 1, 1, 1, 1, 1)
    else:
        ops.mass(i+1, mass_per_floor, mass_per_floor, mass_per_floor,
                 0, 0, 0)

# Propiedades (ajustadas para simular edificio típico)
E = 25e6
A = 1.0
I = 0.1

ops.geomTransf('Linear', 1, 1, 0, 0)

for i in range(num_stories):
    ops.element('elasticBeamColumn', i+1, i+1, i+2, A, E, I, 1)

# Análisis modal
ops.system('BandGeneral')
ops.numberer('Plain')
ops.constraints('Plain')

eigenvalues = ops.eigen(1)  # Solo modo fundamental

omega1 = math.sqrt(eigenvalues[0])
T1 = 2 * math.pi / omega1

print("=" * 50)
print("COMPARACIÓN CON FÓRMULA EMPÍRICA")
print("=" * 50)

# Altura total
H_total = num_stories * H_story

# Fórmula empírica ASCE 7-16 para edificios de concreto
T_approx_ASCE = 0.0466 * (H_total ** 0.9)  # en metros

# Fórmula simple T ≈ 0.1 * N (N = número de pisos)
T_approx_simple = 0.1 * num_stories

print(f"\nAltura total:        {H_total} m")
print(f"Número de pisos:     {num_stories}")
print(f"\nPeríodo fundamental (OpenSees):     {T1:.3f} s")
print(f"Período fórmula ASCE 7:             {T_approx_ASCE:.3f} s")
print(f"Período fórmula simple (0.1·N):     {T_approx_simple:.3f} s")

ratio_ASCE = T1 / T_approx_ASCE
print(f"\nRelación OpenSees/ASCE: {ratio_ASCE:.2f}")

ops.wipe()
```

---

## Interpretación de Resultados

### Modos Típicos de Edificios

**Modo 1 (Fundamental):**
- Período más largo
- Mayor participación modal (60-80% típicamente)
- Forma: Traslación lateral predominante

**Modo 2:**
- Período más corto que modo 1
- Forma: Puede ser traslación en dirección ortogonal o torsión

**Modo 3+:**
- Períodos progresivamente más cortos
- Formas más complejas (flexión, torsión combinados)

### Verificaciones

✅ **Suma de % masa modal ≥ 90%** en cada dirección  
✅ **Período fundamental:** Comparar con fórmulas empíricas (±30% razonable)  
✅ **Eigenvalues positivos:** Eigenvalues ≤ 0 indican mecanismo  
✅ **Formas modales razonables:** Verificar visualmente

---

## Puntos Clave

✅ **Masas obligatorias** para análisis modal  
✅ **`ops.eigen(n)`** retorna eigenvalues $\lambda_i = \omega_i^2$  
✅ **Período:** $T_i = 2\pi / \sqrt{\lambda_i}$  
✅ **Participación modal** indica importancia del modo  
✅ **90% de masa** criterio típico de códigos

---

## Próximo Capítulo

Continúa con **[Análisis Sísmico](09-analisis-sismico.md)** para aplicar espectros de respuesta y análisis tiempo-historia.
