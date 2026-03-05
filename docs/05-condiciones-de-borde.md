# Condiciones de Borde en OpenSees

## Índice
1. [Apoyos Fijos (fix)](#apoyos-fijos)
2. [Vínculos Rígidos (equalDOF)](#vínculos-rígidos)
3. [Diafragmas Rígidos](#diafragmas-rígidos)
4. [Ejemplos Prácticos](#ejemplos-prácticos)

---

## Apoyos Fijos

### Comando básico

```python
ops.fix(nodeTag, *constrValues)
```

**Parámetros:**
- `constrValues`: 1 = fijo (restringido), 0 = libre
- Longitud = `ndf` (número de DOF por nodo)

---

### Tipos Comunes de Apoyos en 2D

#### Empotramiento (Fixed Support)
```python
ops.fix(node, 1, 1, 1)
# DOF 1 (X): fijo
# DOF 2 (Y/Z): fijo  
# DOF 3 (rot): fijo
```

```
    │
    ├─── Empotramiento
    │
  Base
```

#### Articulación/Pin (Pinned Support)
```python
ops.fix(node, 1, 1, 0)
# X: fijo
# Y: fijo
# Rotación: libre
```

```
    ○ ← Puede rotar
    │
  Base
```

#### Rodillo/Roller (Roller Support)
```python
# Horizontal (libre en X)
ops.fix(node, 0, 1, 0)

# Vertical (libre en Z)
ops.fix(node, 1, 0, 0)
```

```
   ─○─ ← Puede deslizar
```

---

### Tipos Comunes de Apoyos en 3D

#### Empotramiento 3D
```python
ops.fix(node, 1, 1, 1, 1, 1, 1)
# Todos los DOF fijos
```

#### Articulación 3D
```python
ops.fix(node, 1, 1, 1, 0, 0, 0)
# Traslaciones fijas
# Rotaciones libres
```

---

### Fijar Solo Durante Análisis Estático

```python
# Análisis estático
ops.fix(node, 1, 1, 0)
ops.analyze(1)

# Liberar para análisis dinámico
ops.remove('sp', node, 1)  # Remover restricción en DOF 1
ops.remove('sp', node, 2)  # Remover restricción en DOF 2
```

---

## Vínculos Rígidos

### equalDOF (Multi-Point Constraint)

Fuerza a que un nodo "esclavo" siga a un nodo "maestro":

```python
ops.equalDOF(masterNodeTag, slaveNodeTag, *dofs)
```

**Ejemplo - Conexión viga-columna:**
```python
# Nodo 10 (columna) es maestro
# Nodo 11 (viga) es esclavo  
# Conectar en todos los DOF
ops.equalDOF(10, 11, 1, 2, 3)
```

**Ejemplo - Vínculo parcial:**
```python
# Solo traslaciones (rotación independiente)
ops.equalDOF(master, slave, 1, 2, 3)
```

### rigidLink

```python
ops.rigidLink(linkType, masterNode, slaveNode)
```

**Tipos:**
- `'bar'`: Solo axial (como truss)
- `'beam'`: Completo (todos los DOF)

**Ejemplo:**
```python
ops.rigidLink('beam', column_top, beam_end)
```

---

## Diafragmas Rígidos

Simula losa/techo infinitamente rígido en su plano:

```python
ops.rigidDiaphragm(perpDirn, masterNode, *slaveNodes)
```

**Parámetros:**
- `perpDirn`: Dirección perpendicular al diafragma
  - `1` = perpendicular a X → diafragma en plano YZ
  - `2` = perpendicular a Y → diafragma en plano XZ
  - `3` = perpendicular a Z → diafragma en plano XY (típico para pisos)

### Teoría

Para diafragma en plano XY (perpendicular a Z):

$$U_{slave}^x = U_{master}^x - (Y_{slave} - Y_{master}) \cdot \theta_{master}^z$$

$$U_{slave}^y = U_{master}^y + (X_{slave} - X_{master}) \cdot \theta_{master}^z$$

$$\theta_{slave}^z = \theta_{master}^z$$

**Ventajas:**
- Reduce DOF (menos incógnitas)
- Distribuye carga lateral proporcionalmente
- Representa comportamiento real de losas

---

## Ejemplos Prácticos

### Ejemplo 1: Edificio con Diafragmas

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Geometría
num_bays_x = 3
num_bays_y = 3
Lx = 6.0
Ly = 6.0
num_floors = 3
H = 3.5

# Diccionario de nodos
nodes = {}

# Crear nodos
tag = 1
for floor in range(num_floors + 1):
    z = floor * H
    for i in range(num_bays_x + 1):
        x = i * Lx
        for j in range(num_bays_y + 1):
            y = j * Ly
            
            ops.node(tag, x, y, z)
            nodes[(floor, i, j)] = tag
            
            if floor == 0:
                ops.fix(tag, 1, 1, 1, 1, 1, 1)  # Base empotrada
            
            tag += 1

# Aplicar diafragmas rígidos en cada piso
for floor in range(1, num_floors + 1):
    # Nodo maestro en centro del piso
    master = nodes[(floor, 1, 1)]
    
    # Nodos esclavos (todos los demás del piso)
    slaves = []
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y + 1):
            slave = nodes[(floor, i, j)]
            if slave != master:
                slaves.append(slave)
    
    # Diafragma en plano XY (perpendicular a Z=3)
    ops.rigidDiaphragm(3, master, *slaves)
    
    print(f"Piso {floor}: Diafragma con maestro={master}, {len(slaves)} esclavos")
```

---

### Ejemplo 2: Offset de Conexión

```python
# Modelar excentricidad en conexión viga-columna

# Nodo columna
ops.node(1, 0, 0, 3.0)

# Nodo viga (con offset de 0.5m en X)
ops.node(2, 0.5, 0, 3.0)

# Vínculo rígido entre ellos
ops.rigidLink('beam', 1, 2)

# Ahora la viga puede conectarse al nodo 2
# y la fuerza se transfiere correctamente al nodo 1
```

**Alternativa con geomTransf:**
```python
# Usando joint offsets en transformación geométrica
ops.geomTransf('Linear', 1, 0, 0, 1, 
               '-jntOffset', 0, 0, 0, 0.5, 0, 0)
```

---

### Ejemplo 3: Liberación de Momentos

Para modelar articulación en un extremo de viga:

```python
# Crear nodo auxiliar en misma ubicación
ops.node(10, x, y, z)  # Nodo viga
ops.node(11, x, y, z)  # Nodo auxiliar (misma posición)

# Viga conecta a nodo auxiliar
ops.element('elasticBeamColumn', 1, node_i, 11, ...)

# Conectar nodo auxiliar a real solo en traslaciones
ops.equalDOF(10, 11, 1, 2, 3)  # Solo traslaciones
# Rotaciones quedan libres → articulación
```

---

### Ejemplo 4: Base con Resortes

```python
# En lugar de apoyo fijo, usar elemento zeroLength

# Nodo fijo en el suelo
ops.node(1, 0, 0, 0)
ops.fix(1, 1, 1, 1, 1, 1, 1)

# Nodo de la estructura (sobre el resorte)
ops.node(2, 0, 0, 0)  # Misma posición

# Material del resorte
k_soil = 10000.0  # kN/m (rigidez del suelo)
ops.uniaxialMaterial('Elastic', 1, k_soil)

# Elemento zeroLength (resorte)
ops.element('zeroLength', 1, 1, 2, '-mat', 1, '-dir', 3)

# Ahora nodo 2 se puede mover verticalmente con rigidez k_soil
```

---

## Consejos Prácticos

✅ **Usar `constraints('Transformation')`** cuando hay equalDOF o rigidDiaphragm  
✅ **Diafragmas rígidos:** Gran reducción de DOF en edificios  
✅ **Verificar:** Nodos con misma posición pero tags diferentes para articulaciones  
✅ **Centro de masas:** Nodo maestro de diafragma idealmente en centro de masas

---

**Próximo:** [Cargas y Patrones de Carga](06-cargas.md)
