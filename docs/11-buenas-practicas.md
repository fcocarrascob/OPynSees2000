# Buenas Prácticas en OpenSees

## Índice
1. [Unidades y Consistencia](#unidades-y-consistencia)
2. [Refinamiento de Malla](#refinamiento-de-malla)
3. [Convergencia](#convergencia)
4. [Validación de Modelos](#validación-de-modelos)
5. [Errores Comunes](#errores-comunes)
6. [Optimización](#optimización)

---

## Unidades y Consistencia

### Importancia Crítica

⚠️ **OpenSees NO tiene unidades predefinidas**. El usuario debe mantener consistencia absoluta.

### Sistemas de Unidades Comunes

#### Sistema 1: kN - m - s (Recomendado)

| Magnitud | Unidad | Derivadas |
|----------|--------|-----------|
| Fuerza | kN | - |
| Longitud | m | - |
| Tiempo | s | - |
| Masa | ton (kN·s²/m) | 1 ton = 1 kN·s²/m ≈ 102 kg |
| Esfuerzo/Presión | kPa | 1 kPa = 1 kN/m² |
| | MPa | 1 MPa = 1000 kPa |
| | GPa | 1 GPa = 1e6 kPa |
| Densidad mass | ton/m³ | - |
| Peso específico | kN/m³ | - |
| Aceleración gravedad | m/s² | g = 9.81 m/s² |

**Ejemplo de consistencia:**
```python
# Constantes base
kN = 1.0
m = 1.0
s = 1.0

# Unidades derivadas
mm = m / 1000
cm = m / 100
ton = kN * s**2 / m

Pa = kN / m**2
kPa = 1000 * Pa
MPa = 1000 * kPa
GPa = 1000 * MPa

g = 9.81 * m / s**2

# Uso
E_steel = 200 * GPa  # = 200e6 kPa
f_c = 30 * MPa       # = 30e3 kPa
mass_slab = 50 * ton  # = 50 kN·s²/m
```

#### Sistema 2: N - mm - s

| Magnitud | Unidad |
|----------|--------|
| Fuerza | N |
| Longitud | mm |
| Masa | N·s²/mm (ton = 1e6 N·s²/mm) |
| Esfuerzo | MPa (= N/mm²) |

**Conversión de masas:**
```python
# Si tienes masa en kg, convertir a sistema kN-m-s:
mass_kg = 5000  # kg
mass_ton = mass_kg / 1000  # ton (kN·s²/m)
ops.mass(node, mass_ton, mass_ton, mass_ton, 0, 0, 0)
```

### Verificación de Unidades

**Test rápido:** Calcular peso de masa y verificar:

```python
# Masa asignada
mass = 100.0  # ton (en sistema kN-m-s)

# Peso = masa × gravedad
weight = mass * 9.81  # kN

# Aplicar peso como carga
ops.load(node, 0, 0, -weight, 0, 0, 0)

# Desplazamiento debe ser consistente
```

---

## Refinamiento de Malla

### Reglas Generales

#### Elementos Elásticos
- **1 elemento por miembro** típicamente suficiente
- Aumentar solo si geometría varía significativamente

#### Elementos No-Lineales - Force-Based
- **1-2 elementos por miembro** para rótulas plásticas
- Puntos de integración (3-5) capturan plasticidad distribuida

#### Elementos No-Lineales - Displacement-Based
- **4-8 elementos por miembro** para capturar plasticidad
- Más elementos donde se espera mayor no-linealidad

#### Elementos Shell
- **Relación de aspecto:** Mantener < 4:1 (idealmente < 2:1)
- **Subdivisiones:** 4-6 elementos por espesor en análisis detallado
- **Refinamiento local:** Cerca de aberturas, bordes, concentraciones de esfuerzo

### Estudio de Convergencia

**Proceso:**
1. Realizar análisis con malla inicial
2. Refinar malla (duplicar número de elementos)
3. Comparar resultados clave (desplazamientos máximos, fuerzas, esfuerzos)
4. Si diferencia > 5%, continuar refinando
5. Elegir malla con balance precisión/costo

**Ejemplo de implementación:**
```python
mesh_sizes = [1, 2, 4, 8]  # Número de elementos por miembro
results = []

for n_elem in mesh_sizes:
    # Construir modelo con n_elem
    build_model(n_elem)
    
    # Analizar
    ops.analyze(1)
    
    # Extraer resultado de interés
    disp_max = ops.nodeDisp(top_node, 1)
    results.append(disp_max)
    
    ops.wipe()

# Calcular convergencia
for i in range(1, len(results)):
    diff_percent = abs((results[i] - results[i-1]) / results[i]) * 100
    print(f"{mesh_sizes[i-1]} → {mesh_sizes[i]} elem: Δ = {diff_percent:.2f}%")
```

**Criterio de aceptación:**
- Diferencia < 5% → Convergencia aceptable
- Diferencia < 2% → Convergencia excelente

---

## Convergencia

### Criterios de Convergencia

#### NormDispIncr
```python
ops.test('NormDispIncr', tol, maxIter, printFlag)
```
- Verifica norma del incremento de desplazamiento
- $\|\Delta \mathbf{U}\| < tol$
- **Usar:** Problemas dominados por desplazamiento

**Valores típicos:** `tol = 1e-6` a `1e-8`

#### NormUnbalance
```python
ops.test('NormUnbalance', tol, maxIter)  
```
- Verifica norma de fuerzas desbalanceadas
- $\|\mathbf{R} - \mathbf{F}_{int}\| < tol$
- **Usar:** Problemas dominados por fuerza

#### EnergyIncr
```python
ops.test('EnergyIncr', tol, maxIter)
```
- Verifica incremento de energía
- $\Delta \mathbf{U}^T \cdot \mathbf{R} < tol$
- **Usar:** Balance entre fuerza y desplazamiento

**Mejor para:** Análisis no-lineal general

#### Tolerancias Recomendadas

| Análisis | Tolerance | maxIter |
|----------|-----------|---------|
| Lineal | 1e-6 | 10 |
| No-lineal suave | 1e-6 | 100 |
| No-lineal severo | 1e-4 a 1e-6 | 200 |
| Pushover | 1e-5 | 300 |

### Estrategias para Mejorar Convergencia

#### 1. Reducir Paso de Carga
```python
# En lugar de:
ops.integrator('LoadControl', 1.0)
ops.analyze(1)

# Usar:
ops.integrator('LoadControl', 0.1)
ops.analyze(10)
```

#### 2. Cambiar Algoritmo
```python
# Secuencia de intentos:
algorithms = ['Newton', 'NewtonLineSearch', 'ModifiedNewton', 'KrylovNewton']

for alg in algorithms:
    ops.algorithm(alg)
    success = ops.analyze(1)
    if success == 0:
        break
```

#### 3. Adaptive Analysis
```python
def adaptive_analyze(num_steps, dt_initial=1.0):
    dt = dt_initial
    for i in range(num_steps):
        ops.integrator('LoadControl', dt)
        success = ops.analyze(1)
        
        if success != 0:
            # No convergió, reducir paso
            dt *= 0.5
            print(f"Reduciendo paso a {dt}")
            ops.analyze(1)
        else:
            # Convergió, puede aumentar paso
            if dt < dt_initial:
                dt = min(dt * 1.5, dt_initial)
```

---

## Validación de Modelos

### Checklist de Validación

#### ✅ **1. Verificar Equilibrio**
```python
# Sumar reacciones
total_reaction = np.zeros(6)
for node in support_nodes:
    for dof in range(1, 7):
        R = ops.nodeReaction(node, dof)
        total_reaction[dof-1] += R

# Sumar cargas aplicadas
total_load = # ... calcular

# Comparar
error = np.linalg.norm(total_reaction - total_load)
assert error < 1e-3, f"Equilibrio no satisfecho: error = {error}"
```

#### ✅ **2. Detectar Mecanismos**
```python
# Analizar eigenvalues
eigenvalues = ops.eigen(10)

if any(ev <= 0 for ev in eigenvalues):
    print("⚠ MECANISMO DETECTADO - Eigenvalues no positivos")
    print("Verificar condiciones de borde")
else:
    print("✓ Estructura estable")
```

#### ✅ **3. Comparar con Solución Analítica**

Para casos simples (viga en voladizo, viga simplemente apoyada):

```python
# Ejemplo: Viga en voladizo con carga puntual en extremo
P = 10.0  # kN
L = 3.0   # m
E = 200e6  # kPa
I = 1e-4  # m⁴

# OpenSees
disp_opensees = abs(ops.nodeDisp(tip_node, 2))

# Solución analítica
disp_analytical = (P * L**3) / (3 * E * I)

error_percent = abs(disp_opensees - disp_analytical) / disp_analytical * 100

print(f"OpenSees:   {disp_opensees:.6f} m")
print(f"Analítico:  {disp_analytical:.6f} m")
print(f"Error:      {error_percent:.2f}%")

assert error_percent < 1.0, "Error excesivo vs solución analítica"
```

#### ✅ **4. Verificar Simetría**

Si modelo es simétrico, respuesta debe serlo:

```python
# Verificar desplazamientos simétricos
disp_left = ops.nodeDisp(node_left, dof)
disp_right = ops.nodeDisp(node_right, dof)

diff = abs(disp_left - disp_right)
assert diff < 1e-6, f"Asimetría detectada: {diff}"
```

#### ✅ **5. Comparar con Software Comercial**

Cross-check con SAP2000, ETABS, Abaqus, etc. para modelos de validación.

---

## Errores Comunes

### 1. **Nodos Duplicados**

**Problema:**
```python
ops.node(1, 0.0, 0.0, 0.0)
ops.node(2, 0.0, 0.0, 0.0)  # Mismo lugar, diferente tag!
```

**Síntoma:** Elementos no conectados, mecanismo.

**Solución:** Verificar coordenadas, usar tolerancia al crear nodos:
```python
def create_node_unique(tag, x, y, z, tol=1e-6):
    for existing_tag in ops.getNodeTags():
        coords = ops.nodeCoord(existing_tag)
        if np.linalg.norm(np.array([x,y,z]) - np.array(coords)) < tol:
            print(f"Nodo {tag} coincide con {existing_tag}")
            return existing_tag
    ops.node(tag, x, y, z)
    return tag
```

### 2. **Transformación Geométrica Incorrecta**

**Problema:**
```python
# Viga horizontal en X, pero vecxz apunta en X también!
ops.geomTransf('Linear', 1, 1, 0, 0)  # INCORRECTO
```

**Síntoma:** Elemento no resiste cargas correctamente, resultados ilógicos.

**Solución:**
```python
# Para viga horizontal, vecxz debe ser vertical
ops.geomTransf('Linear', 1, 0, 0, 1)  # CORRECTO
```

### 3. **Olvidar Masas**

**Problema:**
```python
# Definir nodos sin masa
ops.node(1, 0, 0, 0)

# Intentar análisis modal
eigenvalues = ops.eigen(3)  # ¡Fallará!
```

**Solución:** Siempre asignar masas para análisis dinámico:
```python
ops.mass(1, mass, mass, mass, 0, 0, 0)
```

### 4. **Recorders Después de Analyze**

**Problema:**
```python
ops.analyze(1)
ops.recorder('Node', ...)  # Demasiado tarde!
```

**Solución:** Definir recorders ANTES de analizar:
```python
ops.recorder('Node', ...)
ops.analyze(1)
```

### 5. **No Usar `wipe()`**

**Problema:**
```python
# Segundo modelo sin limpiar el primero
ops.model('basic', '-ndm', 3, '-ndf', 6)
```

**Síntoma:** Tags duplicados, comportamiento impredecible.

**Solución:**
```python
ops.wipe()  # Siempre al inicio
ops.model('basic', '-ndm', 3, '-ndf', 6)
```

### 6. **Unidades Inconsistentes**

**Problema:**
```python
E = 200e9  # Pa (pero modelo en kPa!)
ops.uniaxialMaterial('Elastic', 1, E)
```

**Solución:** Convertir:
```python
E = 200e9  # Pa
E_kPa = E / 1000  # kPa
ops.uniaxialMaterial('Elastic', 1, E_kPa)
```

---

## Optimización

### Consejos para Modelos Grandes

#### 1. Usar Solvers Eficientes
```python
# Para modelos grandes (>1000 DOF)
ops.system('UmfPack')  # Mejor que BandSPD para modelos irregulares
```

#### 2. Reducir Salida de Recorders
```python
# En lugar de todos los pasos:
ops.recorder('Node', '-file', 'disp.out', '-time', '-node', *all_nodes, '-dof', 1, 'disp')

# Solo nodos clave:
key_nodes = [top_node, mid_node, base_node]
ops.recorder('Node', '-file', 'disp.out', '-time', '-node', *key_nodes, '-dof', 1, 'disp')
```

#### 3. Usar Diafragmas Rígidos
```python
# Reduce DOF significativamente
ops.rigidDiaphragm(3, master, *slaves)
```

#### 4. Análisis Paralelo (si disponible)

OpenSees soporta análisis paralelo para modelos muy grandes (requiere compilación especial).

---

## Resumen

✅ **Unidades:** Mantener consistencia absoluta  
✅ **Refinamiento:** Estudios de convergencia de malla  
✅ **Tolerancia:** Ajustar según tipo de análisis  
✅ **Validación:** Verificar equilibrio, eigenvalues, simetría  
✅ **Errores:** Evitar duplicados, transformaciones incorrectas  
✅ **Optimización:** Solvers apropiados, reducir salida

---

**¡Felicitaciones!** Has completado la documentación completa de OpenSeesPy. Ahora estás listo para construir y analizar modelos estructurales complejos.

**Siguiente paso:** Revisar los [ejemplos prácticos](../ejemplos/) para aplicar todo lo aprendido.
