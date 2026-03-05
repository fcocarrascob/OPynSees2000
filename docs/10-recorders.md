# Recorders y Procesamiento de Resultados

## Índice
1. [Conceptos Básicos](#conceptos-básicos)
2. [Node Recorders](#node-recorders)
3. [Element Recorders](#element-recorders)
4. [Procesamiento de Datos](#procesamiento-de-datos)

---

## Conceptos Básicos

Los **recorders** capturan datos durante el análisis y los escriben a archivos.

### Reglas Importantes

⚠️ **Definir ANTES de `ops.analyze()`**  
⚠️ **Los archivos se sobrescriben** en cada ejecución  
⚠️ **Formato columnar** por defecto

---

## Node Recorders

### Desplazamientos

```python
ops.recorder('Node', '-file', 'disp.out', '-time', 
             '-node', *nodeTags, '-dof', *dofs, 'disp')
```

**Ejemplo:**
```python
# Grabar desplazamientos de nodos 1, 2, 3 en DOF 1 y 2
ops.recorder('Node', '-file', 'node_disp.out', '-time',
             '-node', 1, 2, 3, '-dof', 1, 2, 'disp')
```

**Archivo de salida:**
```
time  node1_dof1  node1_dof2  node2_dof1  node2_dof2  node3_dof1  node3_dof2
0.00  0.0000      0.0000      0.0000      0.0000      0.0000      0.0000
1.00  0.0012      -0.0045     0.0023      -0.0067     0.0034      -0.0089
```

### Velocidades

```python
ops.recorder('Node', '-file', 'vel.out', '-time',
             '-node', *nodeTags, '-dof', *dofs, 'vel')
```

### Aceleraciones

```python
ops.recorder('Node', '-file', 'accel.out', '-time',
             '-node', *nodeTags, '-dof', *dofs, 'accel')
```

### Reacciones

```python
ops.recorder('Node', '-file', 'reactions.out', '-time',
             '-node', *supportNodes, '-dof', 1, 2, 3, 4, 5, 6, 'reaction')
```

**Importante:** Solo tiene sentido para nodos con restricciones.

---

## Element Recorders

### Fuerzas Locales

```python
ops.recorder('Element', '-file', 'forces.out', '-time',
             '-ele', *eleTags, 'localForce')
```

**Formato para beam-column 3D:**
```
[Nxi, Vyi, Vzi, Txi, Myi, Mzi, Nxj, Vyj, Vzj, Txj, Myj, Mzj]
```

Donde:
- `N` = axial
- `Vy, Vz` = corte
- `Tx` = torsión
- `My, Mz` = momento flector
- Subíndices `i`, `j` = nodos inicial y final

### Fuerzas Globales

```python
ops.recorder('Element', '-file', 'forces_global.out', '-time',
             '-ele', *eleTags, 'globalForce')
```

### Deformaciones

```python
ops.recorder('Element', '-file', 'defo.out', '-time',
             '-ele', *eleTags, 'deformation')
```

### Fuerzas de Sección (Elementos Force-Based)

```python
ops.recorder('Element', '-file', 'section_force.out', '-time',
             '-ele', eleTag, 'section', secNum, 'force')
```

**Parámetros:**
- `secNum`: Número de punto de integración (1, 2, 3, ... numIntPts)

### Esfuerzo en Fibras

```python
ops.recorder('Element', '-file', 'fiber_stress.out', '-time',
             '-ele', eleTag, 'section', secNum, 
             'fiber', yLoc, zLoc, 'stress')
```

**Útil para:** Verificar fluencia de acero, aplastamiento de concreto.

---

## Procesamiento de Datos

### Leer Archivos con NumPy

```python
import numpy as np
import matplotlib.pyplot as plt

# Leer archivo
data = np.loadtxt('disp.out')

# Extraer columnas
time = data[:, 0]
disp_node1_x = data[:, 1]
disp_node1_y = data[:, 2]

# Graficar
plt.figure(figsize=(10, 6))
plt.plot(time, disp_node1_x*1000, label='Node 1 - X')
plt.xlabel('Tiempo (s)')
plt.ylabel('Desplazamiento (mm)')
plt.title('Historia de Desplazamientos')
plt.legend()
plt.grid(True)
plt.savefig('disp_plot.png', dpi=300)
plt.show()
```

### Encontrar Máximos

```python
# Desplazamiento máximo absoluto
disp_max = np.max(np.abs(disp_node1_x))
time_max = time[np.argmax(np.abs(disp_node1_x))]

print(f"Desplazamiento máximo: {disp_max*1000:.2f} mm")
print(f"Ocurre en tiempo: {time_max:.2f} s")
```

### Deriva de Piso (Drift)

```python
# Para edificio, calcular deriva entre pisos
data_floor1 = np.loadtxt('disp_floor1.out')
data_floor2 = np.loadtxt('disp_floor2.out')

time = data_floor1[:, 0]
disp_floor1 = data_floor1[:, 1]
disp_floor2 = data_floor2[:, 1]

H = 3.5  # m, altura de piso

# Deriva (radianes o %)
drift = (disp_floor2 - disp_floor1) / H

drift_max_percent = np.max(np.abs(drift)) * 100

print(f"Deriva máxima: {drift_max_percent:.2f}%")

# Verificar límite de código (ej. 2% para concreto)
if drift_max_percent > 2.0:
    print("⚠ Excede límite de deriva de código")
```

### Envolvente de Respuesta

```python
# Para análisis tiempo-historia, crear envolvente de máximos
nodes = [1, 2, 3, 4, 5]  # Nodos a graficar
heights = [0, 3.5, 7.0, 10.5, 14.0]  # Alturas

disp_max_envelope = []

for node in nodes:
    # Leer archivo del nodo
    data = np.loadtxt(f'disp_node{node}.out')
    disp = data[:, 1]  # DOF 1 (lateral)
    
    # Máximo absoluto
    disp_max_envelope.append(np.max(np.abs(disp)))

# Graficar
plt.figure(figsize=(6, 8))
plt.plot(np.array(disp_max_envelope)*1000, heights, 'o-', linewidth=2)
plt.xlabel('Desplazamiento máximo (mm)')
plt.ylabel('Altura (m)')
plt.title('Envolvente de Desplazamientos')
plt.grid(True)
plt.show()
```

---

## Recorders Avanzados

### Recorder con Region

```python
# Definir región (grupo de nodos)
ops.region(1, '-node', 1, 2, 3, 4, 5)

# Recorder para toda la región
ops.recorder('Node', '-file', 'region_disp.out', '-region', 1,
             '-dof', 1, 'disp')
```

### Recorder de Energía

```python
ops.recorder('EnvelopeNode', '-file', 'maxDisp.out',
             '-node', *nodes, '-dof', 1, 2, 3, 'disp')
```

**Útil para:** Guardar solo valores máximos (ahorra espacio).

---

## Mejores Prácticas

✅ **Nombrar archivos descriptivamente:** `disp_roof_x.out`, no `output1.out`  
✅ **Incluir `-time`** para tener referencia temporal  
✅ **Limitar nodos grabados** para reducir tamaño de archivos  
✅ **Usar EnvelopeRecorder** si solo interesan máximos  
✅ **Documentar formato** en comentarios del código

---

## Ejemplo Completo

```python
import openseespy.opensees as ops
import numpy as np

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# ... (crear modelo) ...

# ============================================
# RECORDERS
# ============================================

# 1. Desplazamientos de techo
ops.recorder('Node', '-file', 'roof_disp.out', '-time',
             '-node', roof_node, '-dof', 1, 2, 'disp')

# 2. Derivas entre pisos
ops.recorder('Drift', '-file', 'story_drift.out', '-time',
             '-iNode', floor1_node, '-jNode', floor2_node,
             '-dof', 1, '-perpDirn', 2)

# 3. Reacciones en base
ops.recorder('Node', '-file', 'base_reactions.out', '-time',
             '-node', *base_nodes, '-dof', 1, 2, 3, 'reaction')

# 4. Fuerzas en elementos críticos
critical_columns = [1, 5, 10]
ops.recorder('Element', '-file', 'column_forces.out', '-time',
             '-ele', *critical_columns, 'localForce')

# 5. Envolvente de desplazamientos máximos
ops.recorder('EnvelopeNode', '-file', 'max_disp.out',
             '-node', *all_nodes, '-dof', 1, 'disp')

# Análisis...
ops.analyze(num_steps, dt)

# ============================================
# POST-PROCESAMIENTO
# ============================================

# Leer y procesar
roof_data = np.loadtxt('roof_disp.out')
time = roof_data[:, 0]
disp_x = roof_data[:, 1]

print(f"Desplazamiento máximo: {np.max(np.abs(disp_x))*1000:.2f} mm")

ops.wipe()
```

---

**Próximo:** Revisar [Buenas Prácticas](11-buenas-practicas.md) para optimizar modelos.
