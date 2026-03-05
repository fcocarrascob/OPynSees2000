"""
Ejemplo 03: Edificio 3D con Diafragmas Rígidos
===============================================

Objetivo:
- Modelar edificio 3D de 2 pisos con 4 columnas
- Implementar diafragmas rígidos en cada piso
- Aplicar carga lateral en ambas direcciones
- Analizar desplazamientos y torsión

Sistema de unidades: kN, m, s
"""

import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt

# ============================================
# LIMPIEZA Y CONFIGURACIÓN INICIAL
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

print("="*60)
print("EJEMPLO 03: EDIFICIO 3D CON DIAFRAGMAS RÍGIDOS")
print("="*60)

# ============================================
# GEOMETRÍA
# ============================================
Lx = 6.0        # Luz en dirección X [m]
Ly = 5.0        # Luz en dirección Y [m]
H1 = 3.5        # Altura piso 1 [m]
H2 = 3.0        # Altura piso 2 [m]

print(f"\nDimensiones:")
print(f"  Lx = {Lx} m")
print(f"  Ly = {Ly} m")
print(f"  H1 = {H1} m")
print(f"  H2 = {H2} m")

# ============================================
# CREACIÓN DE NODOS
# ============================================
# Nomenclatura: 
# Nivel 0 (base): nodos 1-4
# Nivel 1 (piso 1): nodos 11-14
# Nivel 2 (piso 2): nodos 21-24

# Coordenadas de columnas en planta
columnas_xy = [
    (0, 0),      # Columna 1
    (Lx, 0),     # Columna 2
    (Lx, Ly),    # Columna 3
    (0, Ly)      # Columna 4
]

# Crear nodos
nodos_por_nivel = {}

# Nivel 0 (base)
for i, (x, y) in enumerate(columnas_xy, start=1):
    ops.node(i, x, y, 0.0)
    nodos_por_nivel.setdefault(0, []).append(i)
    ops.fix(i, 1, 1, 1, 1, 1, 1)  # Empotrado

# Nivel 1 (piso 1)
for i, (x, y) in enumerate(columnas_xy, start=11):
    ops.node(i, x, y, H1)
    nodos_por_nivel.setdefault(1, []).append(i)

# Nivel 2 (piso 2)
for i, (x, y) in enumerate(columnas_xy, start=21):
    ops.node(i, x, y, H1+H2)
    nodos_por_nivel.setdefault(2, []).append(i)

print(f"\nNodos creados por nivel:")
for nivel, nodos in sorted(nodos_por_nivel.items()):
    print(f"  Nivel {nivel}: {len(nodos)} nodos")

# ============================================
# MATERIALES Y SECCIONES
# ============================================
E_concrete = 25e6   # kN/m² (concreto C25/30)
G_concrete = 10.4e6 # kN/m²

# Secciones de columnas (cuadradas)
b_col = 0.40        # ancho [m]
h_col = 0.40        # alto [m]
A_col = b_col * h_col
I_col = (b_col * h_col**3) / 12
J_col = I_col * 2  # Torsión aproximada

print(f"\nSecciones:")
print(f"  Columnas: {b_col*100:.0f}x{h_col*100:.0f} cm")
print(f"  A = {A_col} m²")
print(f"  I = {I_col:.6f} m⁴")

# ============================================
# TRANSFORMACIONES GEOMÉTRICAS
# ============================================
# Vector local Z apunta hacia arriba (0, 0, 1)
ops.geomTransf('Linear', 1, 0, 0, 1)

# ============================================
# ELEMENTOS (COLUMNAS)
# ============================================
elem_tag = 1

# Columnas piso 1 (base a nivel 1)
for i in range(4):
    node_i = i + 1      # 1, 2, 3, 4
    node_j = i + 11     # 11, 12, 13, 14
    ops.element('elasticBeamColumn', elem_tag, node_i, node_j, 
                A_col, E_concrete, G_concrete, J_col, I_col, I_col, 1)
    elem_tag += 1

# Columnas piso 2 (nivel 1 a nivel 2)
for i in range(4):
    node_i = i + 11     # 11, 12, 13, 14
    node_j = i + 21     # 21, 22, 23, 24
    ops.element('elasticBeamColumn', elem_tag, node_i, node_j, 
                A_col, E_concrete, G_concrete, J_col, I_col, I_col, 1)
    elem_tag += 1

print(f"\nElementos creados: {elem_tag-1} columnas")

# ============================================
# DIAFRAGMAS RÍGIDOS
# ============================================
print("\nAplicando diafragmas rígidos...")

# Piso 1: Nodo maestro en centro (aproximado = nodo 11)
master_1 = 11
slaves_1 = [12, 13, 14]
ops.rigidDiaphragm(3, master_1, *slaves_1)  # 3 = perpendicular a Z
print(f"  Piso 1: Maestro={master_1}, Esclavos={slaves_1}")

# Piso 2: Nodo maestro en centro
master_2 = 21
slaves_2 = [22, 23, 24]
ops.rigidDiaphragm(3, master_2, *slaves_2)
print(f"  Piso 2: Maestro={master_2}, Esclavos={slaves_2}")

# ============================================
# MASAS
# ============================================
# Masa por piso (concentrada en nodo maestro)
masa_piso1 = 50.0   # ton (kN·s²/m)
masa_piso2 = 40.0   # ton

# Solo asignar masa al nodo maestro (el diafragma distribuye)
# Masa rotacional aproximada: I = m * (Lx² + Ly²) / 12
I_rot_1 = masa_piso1 * (Lx**2 + Ly**2) / 12
I_rot_2 = masa_piso2 * (Lx**2 + Ly**2) / 12

ops.mass(master_1, masa_piso1, masa_piso1, masa_piso1, 0, 0, I_rot_1)
ops.mass(master_2, masa_piso2, masa_piso2, masa_piso2, 0, 0, I_rot_2)

print(f"\nMasas:")
print(f"  Piso 1: {masa_piso1} ton")
print(f"  Piso 2: {masa_piso2} ton")

# ============================================
# CARGAS GRAVITACIONALES
# ============================================
print("\n" + "="*60)
print("APLICANDO CARGAS GRAVITACIONALES")
print("="*60)

ops.timeSeries('Constant', 1)
ops.pattern('Plain', 100, 1)

# Cargas por piso (carga muerta + viva)
P_piso1 = 300.0  # kN total
P_piso2 = 250.0  # kN total

ops.load(master_1, 0, 0, -P_piso1, 0, 0, 0)
ops.load(master_2, 0, 0, -P_piso2, 0, 0, 0)

print(f"Carga piso 1: {P_piso1} kN")
print(f"Carga piso 2: {P_piso2} kN")

# Sistema de análisis
ops.system('BandSPD')
ops.numberer('Plain')
ops.constraints('Transformation')  # Importante para rigidDiaphragm
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')

# Analizar
ops.analyze(1)

disp_z_1 = ops.nodeDisp(master_1, 3)
disp_z_2 = ops.nodeDisp(master_2, 3)

print(f"\nDesplazamientos verticales:")
print(f"  Piso 1: {disp_z_1*1000:.2f} mm")
print(f"  Piso 2: {disp_z_2*1000:.2f} mm")

# Congelar gravedad
ops.loadConst('-time', 0.0)

# ============================================
# CARGAS LATERALES
# ============================================
print("\n" + "="*60)
print("APLICANDO CARGAS LATERALES")
print("="*60)

ops.timeSeries('Linear', 2)
ops.pattern('Plain', 200, 2)

# Fuerza en X (simulando viento o sismo)
Fx_piso1 = 50.0  # kN
Fx_piso2 = 40.0  # kN

# Fuerza en Y
Fy_piso1 = 30.0  # kN
Fy_piso2 = 25.0  # kN

ops.load(master_1, Fx_piso1, Fy_piso1, 0, 0, 0, 0)
ops.load(master_2, Fx_piso2, Fy_piso2, 0, 0, 0)

print(f"\nFuerzas laterales:")
print(f"  Piso 1: Fx={Fx_piso1} kN, Fy={Fy_piso1} kN")
print(f"  Piso 2: Fx={Fx_piso2} kN, Fy={Fy_piso2} kN")

# Analizar
ops.analyze(1)

# ============================================
# RESULTADOS
# ============================================
print("\n" + "="*60)
print("DESPLAZAMIENTOS Y ROTACIONES")
print("="*60)

# Desplazamientos de nodos maestros
disp_x_1 = ops.nodeDisp(master_1, 1)
disp_y_1 = ops.nodeDisp(master_1, 2)
rot_z_1 = ops.nodeDisp(master_1, 6)

disp_x_2 = ops.nodeDisp(master_2, 1)
disp_y_2 = ops.nodeDisp(master_2, 2)
rot_z_2 = ops.nodeDisp(master_2, 6)

print(f"\nPiso 1 (nodo {master_1}):")
print(f"  Dx = {disp_x_1*1000:.2f} mm")
print(f"  Dy = {disp_y_1*1000:.2f} mm")
print(f"  Rz = {np.degrees(rot_z_1):.4f}°")

print(f"\nPiso 2 (nodo {master_2}):")
print(f"  Dx = {disp_x_2*1000:.2f} mm")
print(f"  Dy = {disp_y_2*1000:.2f} mm")
print(f"  Rz = {np.degrees(rot_z_2):.4f}°")

# Derivas
drift_x_1 = abs(disp_x_1) / H1
drift_y_1 = abs(disp_y_1) / H1
drift_x_2 = abs(disp_x_2 - disp_x_1) / H2
drift_y_2 = abs(disp_y_2 - disp_y_1) / H2

print(f"\nDerivas de entrepiso:")
print(f"  Piso 1 - X: {drift_x_1*100:.3f}%")
print(f"  Piso 1 - Y: {drift_y_1*100:.3f}%")
print(f"  Piso 2 - X: {drift_x_2*100:.3f}%")
print(f"  Piso 2 - Y: {drift_y_2*100:.3f}%")

# ============================================
# VERIFICACIÓN DE DIAFRAGMA
# ============================================
print("\n" + "="*60)
print("VERIFICACIÓN DE DIAFRAGMA RÍGIDO")
print("="*60)

# Todos los nodos del piso 1 deben tener misma rotación Z
print("\nPiso 1 - Rotaciones Rz:")
for node in [11, 12, 13, 14]:
    rot = ops.nodeDisp(node, 6)
    print(f"  Nodo {node}: {np.degrees(rot):.6f}°")

print("\nPiso 2 - Rotaciones Rz:")
for node in [21, 22, 23, 24]:
    rot = ops.nodeDisp(node, 6)
    print(f"  Nodo {node}: {np.degrees(rot):.6f}°")

# Desplazamientos de esquinas del piso 2
print("\nDesplazamientos en esquinas del piso 2:")
for i, node in enumerate([21, 22, 23, 24], start=1):
    dx = ops.nodeDisp(node, 1)
    dy = ops.nodeDisp(node, 2)
    print(f"  Columna {i} (nodo {node}): Dx={dx*1000:.2f} mm, Dy={dy*1000:.2f} mm")

# ============================================
# REACCIONES
# ============================================
print("\n" + "="*60)
print("REACCIONES EN BASE")
print("="*60)

reacciones = {}
for node in [1, 2, 3, 4]:
    Rx = ops.nodeReaction(node, 1)
    Ry = ops.nodeReaction(node, 2)
    Rz = ops.nodeReaction(node, 3)
    reacciones[node] = (Rx, Ry, Rz)
    print(f"\nColumna en nodo {node}:")
    print(f"  Rx = {Rx:.2f} kN")
    print(f"  Ry = {Ry:.2f} kN")
    print(f"  Rz = {Rz:.2f} kN")

# Equilibrio
sum_Rx = sum(r[0] for r in reacciones.values())
sum_Ry = sum(r[1] for r in reacciones.values())
sum_Rz = sum(r[2] for r in reacciones.values())

print(f"\nEquilibrio:")
print(f"  ΣRx = {sum_Rx:.2f} kN (Aplicado: {-(Fx_piso1+Fx_piso2):.2f} kN)")
print(f"  ΣRy = {sum_Ry:.2f} kN (Aplicado: {-(Fy_piso1+Fy_piso2):.2f} kN)")
print(f"  ΣRz = {sum_Rz:.2f} kN (Aplicado: {-(P_piso1+P_piso2):.2f} kN)")

# ============================================
# VISUALIZACIÓN
# ============================================
print("\n" + "="*60)
print("GENERANDO VISUALIZACIÓN...")
print("="*60)

fig = plt.figure(figsize=(15, 5))

# Vista en planta del piso 2 con deformación
ax1 = fig.add_subplot(131, projection='3d')
ax1.set_title('Edificio 3D - Deformada')
ax1.set_xlabel('X [m]')
ax1.set_ylabel('Y [m]')
ax1.set_zlabel('Z [m]')

scale = 100  # Factor de escala

# Dibujar columnas deformadas
for nivel in range(2):
    for i in range(4):
        if nivel == 0:
            node_i = i + 1
            node_j = i + 11
        else:
            node_i = i + 11
            node_j = i + 21
        
        # Coordenadas originales
        xi, yi, zi = ops.nodeCoord(node_i)
        xj, yj, zj = ops.nodeCoord(node_j)
        
        # Deformaciones
        dxi = ops.nodeDisp(node_i, 1) * scale
        dyi = ops.nodeDisp(node_i, 2) * scale
        dzi = ops.nodeDisp(node_i, 3) * scale
        
        dxj = ops.nodeDisp(node_j, 1) * scale
        dyj = ops.nodeDisp(node_j, 2) * scale
        dzj = ops.nodeDisp(node_j, 3) * scale
        
        ax1.plot([xi+dxi, xj+dxj], [yi+dyi, yj+dyj], [zi+dzi, zj+dzj], 
                 'r-', linewidth=2)

# Derivas en X
ax2 = fig.add_subplot(132)
ax2.set_title('Derivas en Dirección X')
ax2.set_xlabel('Deriva [%]')
ax2.set_ylabel('Piso')
ax2.grid(True, alpha=0.3)

derivas_x = [drift_x_1*100, drift_x_2*100]
ax2.barh(['Piso 1', 'Piso 2'], derivas_x, color='steelblue', alpha=0.7)
ax2.axvline(0.7, color='red', linestyle='--', label='Límite 0.7%')
ax2.legend()

# Derivas en Y
ax3 = fig.add_subplot(133)
ax3.set_title('Derivas en Dirección Y')
ax3.set_xlabel('Deriva [%]')
ax3.set_ylabel('Piso')
ax3.grid(True, alpha=0.3)

derivas_y = [drift_y_1*100, drift_y_2*100]
ax3.barh(['Piso 1', 'Piso 2'], derivas_y, color='darkorange', alpha=0.7)
ax3.axvline(0.7, color='red', linestyle='--', label='Límite 0.7%')
ax3.legend()

plt.tight_layout()
plt.savefig('ejemplo_03_resultados.png', dpi=150)
print("\nGráfica guardada: ejemplo_03_resultados.png")
plt.show()

# ============================================
# RESUMEN
# ============================================
print("\n" + "="*60)
print("RESUMEN")
print("="*60)
print(f"Deriva máxima en X: {max(drift_x_1, drift_x_2)*100:.3f}%")
print(f"Deriva máxima en Y: {max(drift_y_1, drift_y_2)*100:.3f}%")
print(f"Rotación máxima: {max(abs(rot_z_1), abs(rot_z_2))*180/np.pi:.4f}°")

max_drift = max(drift_x_1, drift_x_2, drift_y_1, drift_y_2)
if max_drift <= 0.007:
    print("\n✓ Estructura cumple con criterio de deriva (< 0.7%)")
else:
    print("\n✗ Estructura excede límite de deriva")

print("\n" + "="*60)
print("FIN DEL ANÁLISIS")
print("="*60)
