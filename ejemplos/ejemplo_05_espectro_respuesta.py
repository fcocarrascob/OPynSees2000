"""
Ejemplo 05: Análisis de Espectro de Respuesta
==============================================

Objetivo:
- Implementar análisis de espectro de respuesta sísmico
- Usar espectro de diseño según normativa
- Calcular desplazamientos y fuerzas modales
- Combinar respuesta modal (CQC o SRSS)
- Obtener envolvente de resultados

Sistema de unidades: kN, m, s
"""

import openseespy.opensees as ops
import numpy as np
import matplotlib.pyplot as plt

# ============================================
# LIMPIEZA Y CONFIGURACIÓN
# ============================================
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

print("="*60)
print("EJEMPLO 05: ANÁLISIS DE ESPECTRO DE RESPUESTA")
print("="*60)

# ============================================
# PARÁMETROS SÍSMICOS
# ============================================
# Espectro según Eurocódigo 8 (EC8) o similar
ag = 0.25           # Aceleración pico del suelo (g)
S = 1.2             # Factor de suelo (tipo C)
eta = 1.0           # Factor de corrección de amortiguamiento
TB = 0.15           # Periodo esquina (s)
TC = 0.50           # Periodo esquina (s)
TD = 2.0            # Periodo esquina (s)

# Factor de importancia y comportamiento
gamma_I = 1.0       # Edificio normal
q = 3.5             # Factor de reducción (ductilidad media)

# Gravedad
g = 9.81            # m/s²

print(f"\nParámetros sísmicos:")
print(f"  ag = {ag:.2f}g")
print(f"  S = {S}")
print(f"  q = {q}")
print(f"  Tipo de suelo: C (TC = {TC} s)")

# ============================================
# GEOMETRÍA - EDIFICIO DE 4 PISOS
# ============================================
num_pisos = 4
L = 6.0
H = 3.0

nodos_por_piso = {}

# Base
ops.node(1, 0.0, 0.0)
ops.node(2, L, 0.0)
ops.fix(1, 1, 1, 1)
ops.fix(2, 1, 1, 1)
nodos_por_piso[0] = [1, 2]

# Pisos
tag = 3
for piso in range(1, num_pisos + 1):
    y = piso * H
    ops.node(tag, 0.0, y)
    ops.node(tag+1, L, y)
    nodos_por_piso[piso] = [tag, tag+1]
    tag += 2

# ============================================
# MATERIALES Y ELEMENTOS
# ============================================
E = 25e6
I_col = (0.40**4) / 12
A_col = 0.40 * 0.40
I_viga = (0.30 * 0.50**3) / 12
A_viga = 0.30 * 0.50

ops.geomTransf('Linear', 1)

elem_tag = 1
for piso in range(num_pisos):
    n1 = nodos_por_piso[piso][0]
    n2 = nodos_por_piso[piso][1]
    n3 = nodos_por_piso[piso+1][0]
    n4 = nodos_por_piso[piso+1][1]
    
    ops.element('elasticBeamColumn', elem_tag, n1, n3, A_col, E, I_col, 1)
    elem_tag += 1
    ops.element('elasticBeamColumn', elem_tag, n2, n4, A_col, E, I_col, 1)
    elem_tag += 1

for piso in range(1, num_pisos + 1):
    n_izq = nodos_por_piso[piso][0]
    n_der = nodos_por_piso[piso][1]
    ops.element('elasticBeamColumn', elem_tag, n_izq, n_der, A_viga, E, I_viga, 1)
    elem_tag += 1

# ============================================
# MASAS
# ============================================
masa_nodo = 15.0  # ton

for piso in range(1, num_pisos + 1):
    for node in nodos_por_piso[piso]:
        ops.mass(node, masa_nodo, masa_nodo, 0.0)

masa_total = 2 * num_pisos * masa_nodo
print(f"\nMasa total: {masa_total} ton")

# ============================================
# FUNCIÓN DE ESPECTRO DE RESPUESTA (EC8)
# ============================================
def espectro_EC8(T, ag, S, eta, TB, TC, TD, q):
    """
    Calcula la aceleración espectral según Eurocódigo 8
    
    Se(T) = ag * S * η * (función del periodo)
    
    Retorna: Sa en m/s²
    """
    ag_ms2 = ag * g  # Convertir a m/s²
    
    if T <= TB:
        # Rango de periodo corto
        beta = max(2.5 / q, 0.2)
        Se = ag_ms2 * S * eta * (1 + (T/TB) * (beta * eta - 1))
    elif T <= TC:
        # Meseta
        beta = max(2.5 / q, 0.2)
        Se = ag_ms2 * S * eta * beta
    elif T <= TD:
        # Descenso
        beta = max(2.5 / q, 0.2)
        Se = ag_ms2 * S * eta * beta * (TC / T)
    else:
        # Periodo largo
        beta = max(2.5 / q, 0.2)
        Se = ag_ms2 * S * eta * beta * (TC * TD / (T**2))
    
    return Se

# ============================================
# ANÁLISIS MODAL
# ============================================
print("\n" + "="*60)
print("ANÁLISIS MODAL")
print("="*60)

num_modos = num_pisos * 2  # Suficientes modos
eigenvalues = ops.eigen(num_modos)

periodos = []
frecuencias = []
omega_n = []
Sa_list = []

print(f"\n{'Modo':<6} {'T [s]':<10} {'ω [rad/s]':<12} {'Sa [m/s²]':<12} {'Sa [g]':<10}")
print("-" * 60)

for i, eigenvalue in enumerate(eigenvalues, start=1):
    omega_i = np.sqrt(eigenvalue)
    freq_i = omega_i / (2 * np.pi)
    T_i = 1.0 / freq_i if freq_i > 0 else 0.0
    
    # Aceleración espectral para este periodo
    Sa_i = espectro_EC8(T_i, ag, S, eta, TB, TC, TD, q)
    Sa_g = Sa_i / g
    
    omega_n.append(omega_i)
    frecuencias.append(freq_i)
    periodos.append(T_i)
    Sa_list.append(Sa_i)
    
    print(f"{i:<6} {T_i:<10.4f} {omega_i:<12.4f} {Sa_i:<12.4f} {Sa_g:<10.4f}")

# ============================================
# FACTORES DE PARTICIPACIÓN MODAL
# ============================================
print("\n" + "="*60)
print("FACTORES DE PARTICIPACIÓN")
print("="*60)

factores_gamma = []
masa_efectiva = []

print(f"\n{'Modo':<6} {'Γ':<12} {'Meff [ton]':<14} {'% Masa':<10}")
print("-" * 46)

for modo in range(1, num_modos + 1):
    numerador = 0.0
    denominador = 0.0
    
    for piso in range(1, num_pisos + 1):
        for node in nodos_por_piso[piso]:
            phi = ops.nodeEigenvector(node, modo, 1)  # Dirección X
            m = masa_nodo
            numerador += m * phi
            denominador += m * phi * phi
    
    gamma_i = numerador / denominador if denominador != 0 else 0.0
    m_eff = (numerador**2) / denominador if denominador != 0 else 0.0
    
    factores_gamma.append(gamma_i)
    masa_efectiva.append(m_eff)
    
    percent = (m_eff / masa_total) * 100
    print(f"{modo:<6} {gamma_i:<12.6f} {m_eff:<14.2f} {percent:<10.2f}")

# ============================================
# RESPUESTA MODAL
# ============================================
print("\n" + "="*60)
print("RESPUESTA MODAL")
print("="*60)

# Calcular desplazamientos y fuerzas modales
desplazamientos_modales = {}  # {modo: {node: disp}}
fuerzas_modales = {}          # {modo: {node: fuerza}}

print(f"\n{'Modo':<6} {'Disp máx [mm]':<15} {'Fuerza base [kN]':<18}")
print("-" * 42)

for modo in range(1, num_modos + 1):
    Sa = Sa_list[modo - 1]
    omega = omega_n[modo - 1]
    gamma = factores_gamma[modo - 1]
    T = periodos[modo - 1]
    
    # Desplazamiento espectral: Sd = Sa / ω²
    Sd = Sa / (omega**2) if omega > 0 else 0.0
    
    # Desplazamiento modal: u_i = Γ_i * Sd * φ_i
    desps = {}
    fuerzas = {}
    max_disp = 0.0
    
    for piso in range(1, num_pisos + 1):
        for node in nodos_por_piso[piso]:
            phi = ops.nodeEigenvector(node, modo, 1)
            
            # Desplazamiento
            disp_modal = gamma * Sd * phi
            desps[node] = disp_modal
            max_disp = max(max_disp, abs(disp_modal))
            
            # Fuerza inercial: F = m * Sa * Γ * φ
            fuerza_modal = masa_nodo * Sa * gamma * phi
            fuerzas[node] = fuerza_modal
    
    desplazamientos_modales[modo] = desps
    fuerzas_modales[modo] = fuerzas
    
    # Cortante basal modal
    V_modal = sum(fuerzas.values())
    
    print(f"{modo:<6} {max_disp*1000:<15.2f} {abs(V_modal):<18.2f}")

# ============================================
# COMBINACIÓN MODAL: SRSS
# ============================================
print("\n" + "="*60)
print("COMBINACIÓN MODAL (SRSS)")
print("="*60)

# SRSS: Square Root of Sum of Squares
desplazamientos_SRSS = {}
fuerzas_SRSS = {}

# Para cada nodo, combinar respuesta de todos los modos
for piso in range(1, num_pisos + 1):
    for node in nodos_por_piso[piso]:
        # Desplazamientos
        suma_cuadrados_disp = sum(
            desplazamientos_modales[modo].get(node, 0.0)**2 
            for modo in range(1, num_modos + 1)
        )
        desplazamientos_SRSS[node] = np.sqrt(suma_cuadrados_disp)
        
        # Fuerzas
        suma_cuadrados_fuerza = sum(
            fuerzas_modales[modo].get(node, 0.0)**2 
            for modo in range(1, num_modos + 1)
        )
        fuerzas_SRSS[node] = np.sqrt(suma_cuadrados_fuerza)

print(f"\n{'Piso':<6} {'Nodo':<6} {'Desp [mm]':<12} {'Fuerza [kN]':<12}")
print("-" * 40)

for piso in range(1, num_pisos + 1):
    for node in nodos_por_piso[piso]:
        disp = desplazamientos_SRSS[node]
        fuerza = fuerzas_SRSS[node]
        print(f"{piso:<6} {node:<6} {disp*1000:<12.2f} {fuerza:<12.2f}")

# Cortante basal total
V_basal_SRSS = np.sqrt(sum(
    (sum(fuerzas_modales[modo].values()))**2 
    for modo in range(1, num_modos + 1)
))

print(f"\nCortante basal (SRSS): {V_basal_SRSS:.2f} kN")

# ============================================
# DERIVAS DE ENTREPISO
# ============================================
print("\n" + "="*60)
print("DERIVAS DE ENTREPISO")
print("="*60)

derivas = []

print(f"\n{'Piso':<6} {'Δ [mm]':<12} {'Deriva [%]':<12} {'Estado':<10}")
print("-" * 44)

for piso in range(1, num_pisos + 1):
    # Desplazamiento del piso
    node_piso = nodos_por_piso[piso][0]
    disp_piso = desplazamientos_SRSS[node_piso]
    
    # Desplazamiento del piso inferior
    if piso == 1:
        disp_inferior = 0.0
    else:
        node_inferior = nodos_por_piso[piso-1][0]
        disp_inferior = desplazamientos_SRSS[node_inferior]
    
    # Deriva de entrepiso
    delta = disp_piso - disp_inferior
    deriva = delta / H
    deriva_pct = deriva * 100
    
    derivas.append(deriva)
    
    # Criterio de aceptación (0.7% típico)
    estado = "✓ OK" if deriva <= 0.007 else "✗ EXCEDE"
    
    print(f"{piso:<6} {delta*1000:<12.2f} {deriva_pct:<12.3f} {estado:<10}")

# ============================================
# VISUALIZACIÓN
# ============================================
print("\n" + "="*60)
print("GENERANDO GRÁFICAS...")
print("="*60)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# ---------------------------
# GRÁFICA 1: Espectro de diseño
# ---------------------------
ax1 = axes[0, 0]

T_plot = np.logspace(-2, 1, 200)  # De 0.01 a 10 s
Sa_plot = [espectro_EC8(T, ag, S, eta, TB, TC, TD, q) / g for T in T_plot]

ax1.loglog(T_plot, Sa_plot, 'b-', linewidth=2, label='Espectro de diseño')

# Marcar periodos de los modos
for i in range(min(num_modos, 5)):
    T_i = periodos[i]
    Sa_i = Sa_list[i] / g
    ax1.plot(T_i, Sa_i, 'ro', markersize=10)
    ax1.text(T_i, Sa_i*1.1, f'M{i+1}', ha='center', fontsize=9)

ax1.set_xlabel('Periodo [s]')
ax1.set_ylabel('Sa [g]')
ax1.set_title(f'Espectro de Respuesta (ag={ag}g, q={q})')
ax1.grid(True, which='both', alpha=0.3)
ax1.legend()

# ---------------------------
# GRÁFICA 2: Desplazamientos
# ---------------------------
ax2 = axes[0, 1]

alturas = [i * H for i in range(num_pisos + 1)]
desps_plot = [0.0]  # Base

for piso in range(1, num_pisos + 1):
    node = nodos_por_piso[piso][0]
    desps_plot.append(desplazamientos_SRSS[node] * 1000)  # mm

ax2.plot(desps_plot, alturas, 'o-', linewidth=2, markersize=8, color='darkred')
ax2.set_xlabel('Desplazamiento [mm]')
ax2.set_ylabel('Altura [m]')
ax2.set_title('Perfil de Desplazamientos (SRSS)')
ax2.grid(True, alpha=0.3)

# ---------------------------
# GRÁFICA 3: Derivas
# ---------------------------
ax3 = axes[1, 0]

pisos_labels = [f'P{i}' for i in range(1, num_pisos + 1)]
derivas_pct = [d * 100 for d in derivas]

colores = ['green' if d <= 0.7 else 'red' for d in derivas_pct]

ax3.barh(pisos_labels, derivas_pct, color=colores, alpha=0.7)
ax3.axvline(0.7, color='orange', linestyle='--', linewidth=2, label='Límite 0.7%')
ax3.set_xlabel('Deriva [%]')
ax3.set_ylabel('Piso')
ax3.set_title('Derivas de Entrepiso')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='x')

# ---------------------------
# GRÁFICA 4: Contribución modal a desplazamiento
# ---------------------------
ax4 = axes[1, 1]

# Desplazamiento del techo por cada modo
node_techo = nodos_por_piso[num_pisos][0]
contrib_modes = []

for modo in range(1, min(num_modos, 8) + 1):
    disp_modo = abs(desplazamientos_modales[modo][node_techo] * 1000)
    contrib_modes.append(disp_modo)

modos_labels = [f'M{i}' for i in range(1, len(contrib_modes) + 1)]

ax4.bar(modos_labels, contrib_modes, alpha=0.7, color='steelblue')
ax4.set_xlabel('Modo')
ax4.set_ylabel('Desplazamiento techo [mm]')
ax4.set_title('Contribución Modal al Desplazamiento')
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('ejemplo_05_resultados.png', dpi=150)
print("\nGráfica guardada: ejemplo_05_resultados.png")
plt.show()

# ============================================
# RESUMEN FINAL
# ============================================
print("\n" + "="*60)
print("RESUMEN")
print("="*60)

node_techo = nodos_por_piso[num_pisos][0]
disp_max = desplazamientos_SRSS[node_techo]
deriva_max = max(derivas)

print(f"\nPeríodo fundamental:       {periodos[0]:.4f} s")
print(f"Sa (T1):                   {Sa_list[0]/g:.4f}g")
print(f"Cortante basal:            {V_basal_SRSS:.2f} kN")
print(f"Desplazamiento máximo:     {disp_max*1000:.2f} mm")
print(f"Deriva máxima:             {deriva_max*100:.3f}%")

if deriva_max <= 0.007:
    print("\n✓ Estructura cumple con criterio de deriva (< 0.7%)")
else:
    print("\n✗ Deriva excede límite. Considerar:")
    print("  - Aumentar rigidez lateral")
    print("  - Agregar muros de corte o arriostramientos")

print("\n" + "="*60)
print("FIN DEL ANÁLISIS DE ESPECTRO")
print("="*60)
