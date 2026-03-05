# Análisis Sísmico en OpenSees

## Índice
1. [Introducción](#introducción)
2. [Análisis Espectral](#análisis-espectral)
3. [Análisis Tiempo-Historia](#análisis-tiempo-historia)
4. [Implementación Práctica](#implementación-práctica)

---

## Introducción

OpenSees es especialmente potente para análisis sísmico. Existen dos enfoques principales:

1. **Análisis Espectral (Response Spectrum Analysis)**
   - Usa espectro de diseño
   - Resultado: máximos de respuesta
   - Más rápido, menos detallado

2. **Análisis Tiempo-Historia (Time History Analysis)**
   - Usa acelerograma real o sintético
   - Resultado: historia completa de respuesta
   - Más lento, más detallado

---

## Análisis Espectral

### Limitación Importante

⚠️ **OpenSees NO tiene comando incorporado para análisis espectral**. Debe implementarse manualmente usando:
1. Análisis modal → períodos y formas modales
2. Lectura de espectro de diseño
3. Cálculo manual de respuesta modal
4. Combinación modal (SRSS o CQC)

### Procedimiento General

```python
# PASO 1: Análisis Modal
eigenvalues = ops.eigen(num_modes)

# PASO 2: Extraer formas modales y calcular participación
# (Ver Ejemplo en docs/08-analisis-modal.md)

# PASO 3: Interpolate espectro para cada período
Sa_i = interpolate_spectrum(T_i, spectrum)  # Aceleración espectral

# PASO 4: Calcular respuesta modal
for mode in range(num_modes):
    # Desplazamiento modal máximo
    D_i = Gamma_i * Sa_i / omega_i**2
    
    # Combinar con forma modal
    U_i = phi_i * D_i

# PASO 5: Combinar modosen (SRSS o CQC)
# SRSS:
U_total = sqrt(sum(U_i**2))

# CQC (para modos cercanos):
U_total = sqrt(sum(sum(rho_ij * U_i * U_j)))
```

### Ejemplo: Implementación SRSS

```python
import openseespy.opensees as ops
import numpy as np
import math

# Espectro de diseño (períodos y aceleraciones)
spectrum_T = np.array([0.0, 0.5, 1.0, 2.0, 3.0, 4.0])  # s
spectrum_Sa = np.array([0.4, 1.0, 0.8, 0.5, 0.35, 0.25]) * 9.81  # m/s²

def interpolate_spectrum(T, spec_T, spec_Sa):
    """Interpola espectro para período dado"""
    return np.interp(T, spec_T, spec_Sa)

# ... (después de crear modelo y masas)

num_modes = 5
eigenvalues = ops.eigen(num_modes)

# Almacenar respuesta modal
modal_displacements = {}

for i in range(num_modes):
    # Propiedades modales
    omega = math.sqrt(eigenvalues[i])
    T = 2 * math.pi / omega
    
    # Aceleración espectral
    Sa = interpolate_spectrum(T, spectrum_T, spectrum_Sa)
    
    # Factor de participación (simplificado)
    # En realidad debe calcular: Gamma = phi^T * M * r / (phi^T * M * phi)
    Gamma = 1.0  # Aproximación
    
    # Desplazamiento modal
    D_modal = Gamma * Sa / (omega**2)
    
    # Guardar para cada nodo
    for node in node_list:
        phi = ops.nodeEigenvector(node, i+1, dof)
        modal_displ = phi * D_modal
        
        if node not in modal_displacements:
            modal_displacements[node] = []
        modal_displacements[node].append(modal_disp)

# Combinar con SRSS
for node in node_list:
    U_combined = math.sqrt(sum(u**2 for u in modal_displacements[node]))
    print(f"Nodo {node}: Despl. máximo = {U_combined*1000:.2f} mm")
```

---

## Análisis Tiempo-Historia

### Configuración

```python
# 1. Definir acelerograma
ops.timeSeries('Path', tag, '-dt', dt, '-filePath', 'earthquake.txt', 
               '-factor', g)

# 2. Patrón de excitación uniforme
ops.pattern('UniformExcitation', tag, direction, '-accel', tsTag)
```

**Parámetros:**
- `dt`: Paso de tiempo del acelerograma (s)
- `direction`: 1=X, 2=Y, 3=Z
- `-factor`: Factor de escala (típicamente `g = 9.81` para convertir de g's a m/s²)

### Integrador de Newmark

```python
ops.integrator('Newmark', gamma, beta)
```

**Valores típicos:**
- `gamma = 0.5`, `beta = 0.25` → Aceleración promedio (incondicionalmente estable)
- `gamma = 0.5`, `beta = 0.1667` → Aceleración lineal

### Análisis Transient

```python
ops.analysis('Transient')

# Ejecutar
dt = 0.01  # Paso de tiempo
num_steps = 1000
ops.analyze(num_steps, dt)
```

### Amortiguamiento de Rayleigh

**Crítico para análisis dinámico:**

```python
# Definir amortiguamiento en dos modos
xi = 0.05  # 5% de amortiguamiento crítico
omega_1 = math.sqrt(eigenvalues[0])  # Primer modo
omega_2 = math.sqrt(eigenvalues[2])  # Tercer modo (o segundo)

# Calcular coeficientes
alphaM = xi * (2 * omega_1 * omega_2) / (omega_1 + omega_2)
betaK = xi * 2 / (omega_1 + omega_2)

ops.rayleigh(alphaM, 0.0, 0.0, betaK)
```

---

## Implementación Práctica

### Ejemplo Completo: Tiempo-Historia

```python
import openseespy.opensees as ops
import numpy as np
import math

# ============================================
# MODELO (simplificado)
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Edificio de 3 pisos (modelo simplificado tipo shear building)
num_floors = 3
H = 3.0  # m por piso
mass_per_floor = 100.0  # ton

# Nodos
for i in range(num_floors + 1):
    ops.node(i+1, 0.0, i*H)
    if i == 0:
        ops.fix(i+1, 1, 1, 1)
    else:
        ops.mass(i+1, mass_per_floor, mass_per_floor, 0.0)

# Elementos (columnas muy rígidas)
E = 30e6
A = 1.0
I = 0.5

ops.geomTransf('Linear', 1)

for i in range(num_floors):
    ops.element('elasticBeamColumn', i+1, i+1, i+2, A, E, I, 1)

# ============================================
# AMORTIGUAMIENTO
# ============================================
eigenvalues = ops.eigen(2)
omega1 = math.sqrt(eigenvalues[0])
omega2 = math.sqrt(eigenvalues[1])

xi = 0.05  # 5%
alphaM = xi * (2 * omega1 * omega2) / (omega1 + omega2)
betaK = xi * 2 / (omega1 + omega2)

ops.rayleigh(alphaM, 0.0, 0.0, betaK)

# ============================================
# CARGAS GRAVITACIONALES
# ============================================
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

for i in range(1, num_floors + 1):
    W = mass_per_floor * 9.81  # kN
    ops.load(i+1, 0.0, -W, 0.0)

# Análisis estático para gravedad
ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')
ops.analyze(1)

# Mantener cargas gravitacionales constantes
ops.loadConst('-time', 0.0)

# ============================================
# SISITERIORAMA (Ejemplo sintético)
# ============================================
# Generar sismo sintético simple
dt_eq = 0.01  # s
duration = 10.0  # s
num_pts = int(duration / dt_eq)

# Sismo sinusoidal simple (en realidad usar acelerograma real)
t = np.linspace(0, duration, num_pts)
accel = 0.3 * np.sin(2*np.pi*1.5*t) * np.exp(-0.3*t)  # g's

# Guardar en archivo
np.savetxt('accel.txt', accel)

# Definir time series del sismo
g = 9.81  # Para convertir g's a m/s²
ops.timeSeries('Path', 2, '-dt', dt_eq, '-filePath', 'accel.txt', '-factor', g)

# Patrón de excitación uniforme en dirección X
ops.pattern('UniformExcitation', 2, 1, '-accel', 2)

# ============================================
# RECORDERS
# ============================================
ops.recorder('Node', '-file', 'disp_time_history.out', '-time',
             '-node', num_floors+1, '-dof', 1, 'disp')

ops.recorder(' Node', '-file', 'accel_time_history.out', '-time',
             '-node', num_floors+1, '-dof', 1, 'accel')

# ============================================
# ANÁLISIS DINÁMICO
# ============================================
ops.wipeAnalysis()

ops.system('UmfPack')
ops.numberer('RCM')
ops.constraints('Transformation')

ops.test('NormDispIncr', 1.0e-6, 100)
ops.algorithm('Newton')

# Integrador de Newmark
gamma = 0.5
beta = 0.25
ops.integrator('Newmark', gamma, beta)

ops.analysis('Transient')

# Ejecutar análisis
print("Ejecutando análisis dinámico...")
num_steps = num_pts
dt_analysis = dt_eq

for i in range(num_steps):
    success = ops.analyze(1, dt_analysis)
    
    if success != 0:
        print(f"Convergencia falló en paso {i}")
        break
    
    # Progreso
    if i % 100 == 0:
        print(f"  Paso {i}/{num_steps}")

print("Análisis completado!")

# Leer resultados
disp_history = np.loadtxt('disp_time_history.out')
t_out = disp_history[:, 0]
d_out = disp_history[:, 1]

disp_max = np.max(np.abs(d_out))
print(f"\nDesplazamiento máximo en techo: {disp_max*1000:.2f} mm")

ops.wipe()
```

---

## Resumen Comparativo

| Aspecto | Espectral | Tiempo-Historia |
|---------|-----------|-----------------|
| **Resultado** | Máximos | Historia completa |
| **Tiempo computo** | Rápido | Lento |
| **Complejidad** | Media | Alta |
| **Detalle** | Bajo | Alto |
| **Uso típico** | Diseño preliminar | Diseño final, investigación |
| **Implementación OpenSees** | Manual | Directa |

---

## Recursos

- Acelerogramas reales: PEER Ground Motion Database
- Espectros de diseño: ASCE 7, Eurocode 8, códigos nacionales

**Próximo:** Revisar [Recorders](10-recorders.md) para capturar resultados de análisis sísmico.
