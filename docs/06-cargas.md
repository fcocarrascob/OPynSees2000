# Cargas y Patrones de Carga en OpenSees

## Índice
1. [Conceptos Fundamentales](#conceptos-fundamentales)
2. [Time Series](#time-series)
3. [Load Patterns](#load-patterns)
4. [Tipos de Cargas](#tipos-de-cargas)
5. [Combinaciones de Carga](#combinaciones-de-carga)

---

## Conceptos Fundamentales

En OpenSees, las cargas se definen mediante:

```
Carga Real = Pattern × TimeSeries × Factor
```

**Componentes:**
1. **TimeSeries:** Define variación temporal
2. **Pattern:** Agrupa cargas relacionadas
3. **Carga individual:** Fuerza/momento específico

---

## Time Series

Define cómo varía la carga en el "pseudo-tiempo" o tiempo real.

### Constant

```python
ops.timeSeries('Constant', tag)
```

- Carga constante (no varía)
- **Uso:** Cargas muertas, cargas vivas estáticas

### Linear

```python
ops.timeSeries('Linear', tag, '-factor', factor)
```

- Rampa lineal desde 0
- **Uso:** Aplicar carga gradualmente

### Path

```python
ops.timeSeries('Path', tag, '-dt', dt, '-values', *values)
# o
ops.timeSeries('Path', tag, '-dt', dt, '-filePath', filePath, '-factor', factor)
```

- Serie de valores arbitrarios
- **Uso:** Acelerogramas, cargas variables en el tiempo

**Ejemplo:**
```python
# Desde archivo
ops.timeSeries('Path', 1, '-dt', 0.01, '-filePath', 'earthquake.txt', '-factor', 9.81)

# Desde lista
values = [0, 0.5, 1.0, 0.8, 0.3, 0]
ops.timeSeries('Path', 2, '-dt', 1.0, '-values', *values)
```

---

## Load Patterns

Agrupa cargas y las asocia con un TimeSeries.

### Plain Pattern

```python
ops.pattern(patternType, patternTag, tsTag, '-fact', factor)
```

**Parámetros:**
- `patternType`: `'Plain'`, `'UniformExcitation'`, `'MultipleSupport'`
- `patternTag`: ID único
- `tsTag`: ID del TimeSeries
- `factor`: Factor multiplicador adicional (opcional)

**Ejemplo básico:**
```python
# TimeSeries constante
ops.timeSeries('Constant', 1)

# Pattern de carga muerta
ops.pattern('Plain', 100, 1)
# Ahora definir cargas...
ops.load(node, Fx, Fy, Fz, Mx, My, Mz)
```

### UniformExcitation (Sismo)

```python
ops.pattern('UniformExcitation', patternTag, dir, '-accel', tsTag)
```

- `dir`: Dirección (1=X, 2=Y, 3=Z)
- `-accel`: Asocia acelerograma

**Ejemplo:**
```python
# Acelerograma
ops.timeSeries('Path', 10, '-dt', 0.01, '-filePath', 'eq.txt', '-factor', 9.81)

# Excitación en dirección X
ops.pattern('UniformExcitation', 200, 1, '-accel', 10)
```

---

## Tipos de Cargas

### Cargas Nodales Puntuales

```python
ops.load(nodeTag, Fx, Fy, Fz, Mx, My, Mz)
```

**Ejemplo 2D:**
```python
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

# Carga de 50 kN hacia abajo en nodo 5
ops.load(5, 0.0, -50.0, 0.0)
```

**Ejemplo 3D:**
```python
ops.load(10, Px, Py, Pz, Tx, Ty, Tz)
# Px, Py, Pz: Fuerzas en X, Y, Z
# Tx, Ty, Tz: Momentos sobre X, Y, Z
```

### Cargas Distribuidas en Elementos

```python
ops.eleLoad('-ele', *eleTags, '-type', loadType, *loadValues)
```

**Tipos comunes:**

#### Carga uniforme en viga (beam)
```python
# Debe estar dentro de un pattern
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

# Carga uniforme en elementos 1, 2, 3
# En dirección local y (perpendicular al eje)
w_y = -10.0  # kN/m
ops.eleLoad('-ele', 1, 2, 3, '-type', '-beamUniform', w_y)
```

**Para 3D:**
```python
ops.eleLoad('-ele', eleTag, '-type', '-beamUniform', Wy, Wz, Wx)
# Wy: carga en dirección local y
# Wz: carga en dirección local z  
# Wx: carga en dirección local x (axial distribuida)
```

#### Carga de presión en superficie
```python
# Para elementos shell
ops.eleLoad('-ele', *elements, '-type', '-surfaceLoad', pressure)
```

### Cargas Gravitacionales

**Opción 1: Cargas nodales equivalentes**
```python
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

for node in nodes:
    weight = tributary_mass * 9.81  # kN
    ops.load(node, 0, 0, -weight, 0, 0, 0)
```

**Opción 2: Usando masas + UniformExcitation**
```python
# 1. Asignar masas a nodos
ops.mass(node, mass, mass, mass, 0, 0, 0)

# 2. "Acelerograma" constante = gravedad
ops.timeSeries('Constant', 1)
ops.pattern('UniformExcitation', 1, 3, '-accel', 1)  # Dirección Z

# 3. Factor de gravedad en integrador (método avanzado)
```

---

## Combinaciones de Carga

OpenSees **NO tiene comando directo** para combinaciones. Hay dos enfoques:

### Enfoque 1: Patterns Separados + loadConst

```python
# PASO 1: Aplicar carga muerta
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 100, 1)
for node in nodes:
    ops.load(node, 0, 0, -dead_load, 0, 0, 0)

ops.analyze(1)

# PASO 2: Congelar cargas muertas
ops.loadConst('-time', 0.0)

# PASO 3: Aplicar carga viva
ops.timeSeries('Constant', 2)
ops.pattern('Plain', 200, 2)
for node in nodes:
    ops.load(node, 0, 0, -live_load, 0, 0, 0)

ops.analyze(1)
```

### Enfoque 2: Aplicar Combinación Directamente

```python
# Combinación LRFD: 1.2D + 1.6L
factor_dead = 1.2
factor_live = 1.6

ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

for node in nodes:
    combined_load = factor_dead * dead_load + factor_live * live_load
    ops.load(node, 0, 0, -combined_load, 0, 0, 0)

ops.analyze(1)
```

### Enfoque 3: Múltiples Análisis

```python
# Analizar cada caso por separado
cases = {
    '1.4D': {'D': 1.4, 'L': 0.0},
    '1.2D+1.6L': {'D': 1.2, 'L': 1.6},
    '1.2D+1.0L+1.0E': {'D': 1.2, 'L': 1.0, 'E': 1.0}
}

results = {}

for case_name, factors in cases.items():
    ops.wipe()
    # Construir modelo...
    
    # Aplicar cargas con factores
    ops.timeSeries('Constant', 1)
    ops.pattern('Plain', 1, 1)
    
    total_load = (factors.get('D', 0) * dead_load +
                  factors.get('L', 0) * live_load +
                  factors.get('E', 0) * earthquake_load)
    
    ops.load(node, 0, 0, -total_load, 0, 0, 0)
    
    ops.analyze(1)
    
    # Guardar resultados
    results[case_name] = ops.nodeDisp(critical_node, dof)

# Encontrar caso crítico
critical_case = max(results, key=lambda k: abs(results[k]))
print(f"Caso crítico: {critical_case}")
print(f"Desplazamiento: {results[critical_case]*1000:.2f} mm")
```

---

## Ejemplos Completos

### Ejemplo 1: Estructura con D + L

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# ... (crear modelo) ...

# ============================================
# CASO 1: Solo Carga Muerta
# ============================================
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 100, 1)

dead_load = 30.0  # kN
ops.load(10, 0, -dead_load, 0)

ops.analyze(1)
disp_dead = ops.nodeDisp(10, 2)

ops.loadConst('-time', 0.0)

# ============================================
# CASO 2: Agregar Carga Viva
# ============================================
ops.timeSeries('Constant', 2)
ops.pattern('Plain', 200, 2)

live_load = 20.0  # kN
ops.load(10, 0, -live_load, 0)

ops.analyze(1)
disp_total = ops.nodeDisp(10, 2)

disp_live = disp_total - disp_dead

print(f"Desplazamiento por D: {disp_dead*1000:.2f} mm")
print(f"Desplazamiento por L: {disp_live*1000:.2f} mm")
print(f"Desplazamiento total: {disp_total*1000:.2f} mm")
```

### Ejemplo 2: Carga Distribuida en Viga

```python
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Nodos
ops.node(1, 0, 0)
ops.node(2, 5, 0)

ops.fix(1, 1, 1, 0)
ops.fix(2, 0, 1, 0)

# Elemento
E = 200e6
A = 0.01
I = 1e-4
ops.geomTransf('Linear', 1)
ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)

# Carga distribuida
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

w = -15.0  # kN/m
ops.eleLoad('-ele', 1, '-type', '-beamUniform', w, 0)  # wy, wx

ops.system('BandSPD')
ops.numberer('Plain')
ops.constraints('Plain')
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

ops.analyze(1)

# Deflexión en centro (aproximada por interpolación)
L = 5.0
disp_center_analytical = (5 * w * L**4) / (384 * E * I)
print(f"Deflexión teórica en centro: {abs(disp_center_analytical)*1000:.2f} mm")

ops.wipe()
```

---

## Resumen

✅ **TimeSeries:** Define variación temporal  
✅ **Pattern:** Agrupa cargas, asocia con TimeSeries  
✅ **load():** Cargas nodales puntuales  
✅ **eleLoad():** Cargas distribuidas en elementos  
✅ **loadConst():** Congela cargas actuales  
✅ **Combinaciones:** Implementar manualmente con factores

---

**Próximo:** [Análisis Estático](07-analisis-estatico.md)
