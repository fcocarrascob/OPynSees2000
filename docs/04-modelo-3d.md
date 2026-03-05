# Construcción de Modelos 3D en OpenSees

## Índice
1. [Sistemas de Coordenadas 3D](#sistemas-de-coordenadas-3d)
2. [Definición de Nodos 3D](#definición-de-nodos-3d)
3. [Transformaciones Geométricas](#transformaciones-geométricas)
4. [Orientación de Elementos](#orientación-de-elementos)
5. [Ejemplo Completo: Edificio 3D](#ejemplo-completo-edificio-3d)

---

## Sistemas de Coordenadas 3D

### Sistema Global

OpenSees utiliza un sistema de coordenadas **cartesiano derecho**:

```
        Z (vertical) ↑
                     |
                     |
                     |
                     |________→ Y (transversal)
                    /
                   /
                  /
                 ↙
                X (longitudinal)
```

**Convención estándar:**
- **X**: Dirección longitudinal (eje principal del edificio)
- **Y**: Dirección transversal
- **Z**: Dirección vertical (gravedad actúa en -Z)

### Regla de la Mano Derecha

Para verificar orientación:
1. Apunta tu **pulgar derecho** en dirección +X
2. Tu **índice** apunta en dirección +Y
3. Tu **dedo medio** (perpendicular) apunta en dirección +Z

---

## Definición de Nodos 3D

### Comando Básico

```python
ops.model('basic', '-ndm', 3, '-ndf', 6)
ops.node(nodeTag, x, y, z)
```

**Grados de libertad (ndf=6):**

| DOF | Descripción | Símbolo |
|-----|-------------|---------|
| 1 | Traslación en X | $u_x$ |
| 2 | Traslación en Y | $u_y$ |
| 3 | Traslación en Z | $u_z$ |
| 4 | Rotación sobre X | $\theta_x$ |
| 5 | Rotación sobre Y | $\theta_y$ |
| 6 | Rotación sobre Z | $\theta_z$ |

### Nodos con Masa

Para análisis dinámico, asignar masa en cada DOF:

```python
ops.node(tag, x, y, z, '-mass', mx, my, mz, Imx, Imy, Imz)
```

- `mx, my, mz`: Masas traslacionales
- `Imx, Imy, Imz`: Inercias rotacionales (generalmente pequeñas o cero)

**Ejemplo:**
```python
# Masa de 100 ton concentrada en un nodo
mass = 100.0  # toneladas (en sistema kN-m-s: 1 ton = 1 kN·s²/m)
ops.node(10, 5.0, 5.0, 3.5, '-mass', mass, mass, mass, 0.0, 0.0, 0.0)
```

### Generación Automática de Grilla de Nodos

**Ejemplo: Edificio de 3 pisos, grilla 3x3**

```python
import openseespy.opensees as ops

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Parámetros de grilla
num_bays_x = 3
num_bays_y = 3
num_stories = 3

bay_width_x = 6.0  # m
bay_width_y = 6.0  # m
story_height = 3.5 # m

# Generar nodos
node_tag = 1

for floor in range(num_stories + 1):  # +1 para incluir base
    z = floor * story_height
    
    for row in range(num_bays_y + 1):
        y = row * bay_width_y
        
        for col in range(num_bays_x + 1):
            x = col * bay_width_x
            
            # Crear nodo
            ops.node(node_tag, x, y, z)
            
            # Fijar nodos de la base (piso 0)
            if floor == 0:
                ops.fix(node_tag, 1, 1, 1, 1, 1, 1)
            
            node_tag += 1

print(f"Total de nodos creados: {node_tag - 1}")
# Output: Total de nodos creados: 64 (4x4 nodos por piso, 4 pisos)
```

### Nomenclatura de Nodos

**Estrategia recomendada:** Usar esquema sistemático para facilitar referencia.

**Opción 1: Tag = Piso × 1000 + Fila × 10 + Columna**
```python
# Piso 2, Fila 3, Columna 4 → Tag = 2034
tag = floor * 1000 + row * 10 + col
```

**Opción 2: Tag secuencial con diccionario**
```python
node_dict = {}
for floor in range(num_stories + 1):
    for row in range(num_bays_y + 1):
        for col in range(num_bays_x + 1):
            tag = node_tag
            node_dict[(floor, row, col)] = tag
            ops.node(tag, x, y, z)
            node_tag += 1

# Acceso posterior
tag_needed = node_dict[(2, 1, 3)]  # Piso 2, fila 1, col 3
```

---

## Transformaciones Geométricas

### Concepto

La **transformación geométrica** relaciona el sistema de coordenadas **local del elemento** (ejes 1-2-3) con el sistema **global** (X-Y-Z).

```
Sistema Local del Elemento:        Sistema Global:
                                         Z ↑
    3 (local z)                          |
    ↑                                    |
    |                                    |________→ Y
    |________→ 2 (local y)              /
   /                                   /
  /                                   ↙
 ↙                                   X
1 (local x = eje del elemento)
```

### Tipos de Transformación

#### 1. Linear

```python
ops.geomTransf('Linear', transfTag, *vecxz)
```

- Para análisis de **primer orden** (pequeñas deformaciones)
- No considera efectos P-Delta
- Más rápido

#### 2. PDelta

```python
ops.geomTransf('PDelta', transfTag, *vecxz)
```

- Considera **efectos P-Delta** (geometría de segundo orden)
- Importante para análisis con cargas verticales significativas
- Recomendado para análisis sísmico de edificios

#### 3. Corotational

```python
ops.geomTransf('Corotational', transfTag, *vecxz)
```

- Para **grandes deformaciones/rotaciones**
- Más costoso computacionalmente
- Necesario para análisis de colapso

### Vector `vecxz`

El vector `vecxz` define el **plano local x-z** del elemento:

**Regla:** `vecxz` debe ser un vector en la dirección del eje local z (o cercano).

```
         z_local (eje débil)
         ↑
         |
         |________→ y_local (eje fuerte)
        /
       /
      ↙
   x_local (eje del elemento)
```

### Cálculo de `vecxz` para Diferentes Orientaciones

#### Columnas Verticales

Elemento va de (x1, y1, z1) a (x1, y1, z2) - vertical en Z:

```python
# vecxz apunta en dirección X global → eje débil local paralelo a X
ops.geomTransf('PDelta', 1, 1, 0, 0)
```

O apuntando en Y global:
```python
ops.geomTransf('PDelta', 2, 0, 1, 0)
```

#### Vigas Horizontales en Dirección X

Elemento va de (x1, y, z) a (x2, y, z) - horizontal en X:

```python
# vecxz apunta en Z global → plano x-z local es vertical
ops.geomTransf('Linear', 3, 0, 0, 1)
```

#### Vigas Horizontales en Dirección Y

Elemento va de (x, y1, z) a (x, y2, z) - horizontal en Y:

```python
# vecxz también apunta en Z global
ops.geomTransf('Linear', 4, 0, 0, 1)
```

#### Ejemplo Visual

**Edificio con vigas y columnas:**

```
Vista en planta (piso):

    Y
    ↑
    |
    |   ● ────── ● ────── ●
    |   │ Beam-Y │        │
    |   │        │        │
    |   ● ────── ● ────── ●  Beam-X →
    |      Col      Col
    |
    └──────────────────────→ X

Columnas: vecxz = (1, 0, 0) o (0, 1, 0)
Beam-X:   vecxz = (0, 0, 1)
Beam-Y:   vecxz = (0, 0, 1)  ← Mismo!
```

---

## Orientación de Elementos

### Método para Determinar `vecxz`

**Paso 1:** Identificar el eje del elemento (del nodo i al nodo j)

**Paso 2:** Decidir cómo quieres orientar el eje local "fuerte" (eje z local)

**Paso 3:** El vecxz debe ser perpendicular al eje del elemento y apuntar aproximadamente hacia donde quieres el eje z local

**Regla práctica:**
- Para **columnas verticales**: vecxz horizontal (usualmente (1,0,0) o (0,1,0))
- Para **vigas horizontales**: vecxz vertical (0, 0, 1)

### Verificación de Orientación

```python
# Función auxiliar para verificar sistema local
def print_element_orientation(eleTag):
    """Imprime orientación de ejes locales de un elemento"""
    from openseespy.opensees import eleResponse
    
    # Obtener orientación (no disponible directamente en OpenSeesPy)
    # Alternativa: calcular manualmente basado en geometría
    
    # Por ahora, verificar con fuerzas aplicadas conocidas
    pass
```

### Ejemplo de Rotación Explícita

Si necesitas rotar una sección (ej. columna con sección rectangular inclinada):

```python
# NO hay comando directo para rotar sección en OpenSees
# Solución: Definir la sección con fibras ya rotadas
# O usar múltiples transformaciones geométricas

# Para casos simples, ajustar vecxz es suficiente
```

---

## Ejemplo Completo: Edificio 3D de 2 Pisos

```python
import openseespy.opensees as ops
import numpy as np

# ============================================
# PARÁMETROS DEL EDIFICIO
# ============================================
num_bays_x = 2  # 2 crujías en X
num_bays_y = 2  # 2 crujías en Y
num_floors = 2  # 2 pisos

Lx = 6.0        # m, longitud de crujía en X
Ly = 6.0        # m, longitud de crujía en Y
H = 3.5         # m, altura de entrepiso

# ============================================
# INICIALIZACIÓN
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# ============================================
# CREAR NODOS
# ============================================
nodeTag = 1
node_matrix = {}  # Diccionario: (floor, i, j) -> nodeTag

for floor in range(num_floors + 1):
    z = floor * H
    for i in range(num_bays_x + 1):
        x = i * Lx
        for j in range(num_bays_y + 1):
            y = j * Ly
            
            ops.node(nodeTag, x, y, z)
            node_matrix[(floor, i, j)] = nodeTag
            
            # Fijar base
            if floor == 0:
                ops.fix(nodeTag, 1, 1, 1, 1, 1, 1)
            
            nodeTag += 1

print(f"Nodos creados: {nodeTag - 1}")

# ============================================
# DEFINIR MATERIALES
# ============================================
E_conc = 25e6   # kPa (Concreto 25 MPa)
E_steel = 200e6 # kPa (Acero 200 GPa)

ops.uniaxialMaterial('Elastic', 1, E_conc)

# ============================================
# DEFINIR SECCIONES
# ============================================
# Columna: 40x40 cm
b_col = 0.40
h_col = 0.40
A_col = b_col * h_col
I_col = (b_col * h_col**3) / 12
J_col = I_col  # Aproximación para sección cuadrada

ops.section('Elastic', 1, E_conc, A_col, I_col, I_col)

# Viga: 30x60 cm (h=60 en dirección vertical)
b_beam = 0.30
h_beam = 0.60
A_beam = b_beam * h_beam
Iz_beam = (b_beam * h_beam**3) / 12  # Inercia fuerte (vertical)
Iy_beam = (h_beam * b_beam**3) / 12  # Inercia débil (horizontal)

ops.section('Elastic', 2, E_conc, A_beam, Iz_beam, Iy_beam)

# ============================================
# TRANSFORMACIONES GEOMÉTRICAS
# ============================================
# Trans 1: Para columnas (eje local z paralelo a X global)
ops.geomTransf('PDelta', 1, 1, 0, 0)

# Trans 2: Para vigas en X (eje local z paralelo a Z global)
ops.geomTransf('Linear', 2, 0, 0, 1)

# Trans 3: Para vigas en Y (eje local z paralelo a Z global)
ops.geomTransf('Linear', 3, 0, 0, 1)

# ============================================
# CREAR ELEMENTOS - COLUMNAS
# ============================================
eleTag = 1

for floor in range(num_floors):
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y + 1):
            node_i = node_matrix[(floor, i, j)]
            node_j = node_matrix[(floor + 1, i, j)]
            
            ops.element('elasticBeamColumn', eleTag, node_i, node_j,
                       A_col, E_conc, E_conc/(2*(1+0.2)), J_col, I_col, I_col, 1)
            eleTag += 1

print(f"Columnas creadas: {eleTag - 1}")

# ============================================
# CREAR ELEMENTOS - VIGAS EN X
# ============================================
for floor in range(1, num_floors + 1):
    for i in range(num_bays_x):  # num_bays, no +1
        for j in range(num_bays_y + 1):
            node_i = node_matrix[(floor, i, j)]
            node_j = node_matrix[(floor, i+1, j)]
            
            ops.element('elasticBeamColumn', eleTag, node_i, node_j,
                       A_beam, E_conc, E_conc/(2*(1+0.2)), 
                       Iy_beam*10, Iy_beam, Iz_beam, 2)  # Trans 2
            eleTag += 1

print(f"Vigas en X agregadas. Total elementos: {eleTag - 1}")

# ============================================
# CREAR ELEMENTOS - VIGAS EN Y
# ============================================
for floor in range(1, num_floors + 1):
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y):  # num_bays, no +1
            node_i = node_matrix[(floor, i, j)]
            node_j = node_matrix[(floor, i, j+1)]
            
            ops.element('elasticBeamColumn', eleTag, node_i, node_j,
                       A_beam, E_conc, E_conc/(2*(1+0.2)),
                       Iy_beam*10, Iy_beam, Iz_beam, 3)  # Trans 3
            eleTag += 1

print(f"Vigas en Y agregadas. Total elementos: {eleTag - 1}")

# ============================================
# DIAFRAGMAS RÍGIDOS (Opcional)
# ============================================
for floor in range(1, num_floors + 1):
    # Nodo maestro en el centro del piso
    master_node = node_matrix[(floor, 1, 1)]  # Centro geométrico
    
    # Nodos esclavos: todos los demás nodos del piso
    slave_nodes = []
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y + 1):
            node = node_matrix[(floor, i, j)]
            if node != master_node:
                slave_nodes.append(node)
    
    # Aplicar diafragma rígido en plano XY (perpendicular a Z = 3)
    ops.rigidDiaphragm(3, master_node, *slave_nodes)

print("Diafragmas rígidos aplicados")

# ============================================
# MASAS (Para análisis modal)
# ============================================
mass_per_node = 50.0  # toneladas

for floor in range(1, num_floors + 1):
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y + 1):
            node = node_matrix[(floor, i, j)]
            ops.mass(node, mass_per_node, mass_per_node, mass_per_node,
                    0.0, 0.0, 0.0)

print("Masas asignadas")

# ============================================
# CARGAS GRAVITACIONALES
# ============================================
W_per_node = 500.0  # kN por nodo

ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)

for floor in range(1, num_floors + 1):
    for i in range(num_bays_x + 1):
        for j in range(num_bays_y + 1):
            node = node_matrix[(floor, i, j)]
            ops.load(node, 0.0, 0.0, -W_per_node, 0.0, 0.0, 0.0)

print("Cargas gravitacionales aplicadas")

# ============================================
# ANÁLISIS ESTÁTICO
# ============================================
ops.system('BandSPD')
ops.numberer('RCM')
ops.constraints('Transformation')  # Para diafragmas rígidos
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

ops.analyze(1)

print("\nAnálisis completado!")

# ============================================
# RESULTADOS
# ============================================
# Desplazamiento del nodo de techo en el centro
top_center_node = node_matrix[(num_floors, 1, 1)]
disp_z = ops.nodeDisp(top_center_node, 3)

print(f"Desplazamiento vertical nodo techo central: {disp_z*1000:.2f} mm")

# Reacciones en la base
total_Rz = 0.0
for i in range(num_bays_x + 1):
    for j in range(num_bays_y + 1):
        base_node = node_matrix[(0, i, j)]
        total_Rz += ops.nodeReaction(base_node, 3)

print(f"Reacción total vertical en base: {total_Rz:.2f} kN")
print(f"Carga total aplicada: {W_per_node * (num_bays_x+1) * (num_bays_y+1) * num_floors:.2f} kN")

ops.wipe()
```

---

## Resumen de Puntos Clave

✅ **Sistema global:** X (long), Y (trans), Z (vert)  
✅ **Nodos 3D:** `ops.node(tag, x, y, z)`  
✅ **6 DOF por nodo:** 3 traslaciones + 3 rotaciones  
✅ **Transformación geométrica:** Define orientación local del elemento  
✅ **vecxz para columnas:** Vector horizontal (1,0,0) o (0,1,0)  
✅ **vecxz para vigas:** Vector vertical (0,0,1)  
✅ **Diafragmas rígidos:** `ops.rigidDiaphragm(perpDirn, master, *slaves)`  
✅ **Generación sistemática:** Usar loops y diccionarios

---

## Próximo Capítulo

Continúa con **[Condiciones de Borde](05-condiciones-de-borde.md)** para aprender a aplicar apoyos y restricciones.
