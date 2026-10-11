import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Cotizador Expoclean Ecuador 2026",
    page_icon="🧹",
    layout="wide"
)

st.title("🧹 Cotizador Inteligente Expoclean Ecuador 2026")
st.subheader("Plataforma Multivariable y Trazabilidad Operativa")

# Función auxiliar para convertir valores de Excel a número decimal de forma segura
def limpiar_numero(val, valor_defecto=0.0):
    if pd.isna(val):
        return valor_defecto
    if isinstance(val, (int, float)):
        return float(val)
    # Limpiar cadenas con $, % u otros caracteres de formato
    val_str = str(val).replace('$', '').replace('%', '').strip()
    try:
        return float(val_str)
    except Exception:
        return valor_defecto

# Cargar datos desde el Excel (4 pestañas)
@st.cache_data
def cargar_datos():
    excel_path = "data/base_datos.xlsx"
    df_rendimientos = pd.read_excel(excel_path, sheet_name="rendimientos")
    df_insumos = pd.read_excel(excel_path, sheet_name="insumos")
    df_herramientas = pd.read_excel(excel_path, sheet_name="herramientas_y_epp")
    df_costos = pd.read_excel(excel_path, sheet_name="costos_operativos")
    return df_rendimientos, df_insumos, df_herramientas, df_costos

try:
    df_rendimientos, df_insumos, df_herramientas, df_costos = cargar_datos()
    st.success(" Base de datos multivariable cargada correctamente.")

    # Detectar el nombre exacto de la columna de cobertura en insumos
    col_cobertura = "cobertura_m2_o_uso" if "cobertura_m2_o_uso" in df_insumos.columns else "cobertura_m2_por_unidad"

    # -------------------------------------------------------------
    # 1. PARÁMETROS EN LA BARRA LATERAL
    # -------------------------------------------------------------
    st.sidebar.header("📋 Parámetros del Servicio")
    area_m2 = st.sidebar.number_input("Área en m²:", min_value=10, max_value=50000, value=200, step=50)
    tipologia = st.sidebar.selectbox("Tipo de Espacio / Infraestructura:", df_rendimientos["nombre_area"].tolist())
    es_nocturno = st.sidebar.checkbox("¿Turno Nocturno / Madrugada? (+30% recargo)")
    margen_utilidad_pct = st.sidebar.slider("Margen de Ganancia Objetivo (%):", min_value=20, max_value=60, value=40, step=5)

    # -------------------------------------------------------------
    # 2. CÁLCULOS MATEMÁTICOS Y OPERATIVOS CON CONVERSIÓN SEGURA
    # -------------------------------------------------------------
    datos_area = df_rendimientos[df_rendimientos["nombre_area"] == tipologia].iloc[0]
    
    rendimiento = limpiar_numero(datos_area["rendimiento_m2_hora"], 100.0)
    factor_riesgo = limpiar_numero(datos_area["factor_riesgo"], 1.0)
    tipo_piso = datos_area.get("tipo_piso_predominante", "General")
    nivel_riesgo = datos_area["nivel_riesgo"]

    # A. Tiempo Operativo Estimado
    horas_estimadas = (area_m2 / rendimiento) * factor_riesgo if rendimiento > 0 else 1.0
    num_operarios_recomendado = int(np.ceil(horas_estimadas / 8))  # Jornadas estándar de 8h
    
    # B. Costo de Mano de Obra
    concepto_buscado = "nocturna" if es_nocturno else "base"
    filtro_costo = df_costos[df_costos["concepto"].astype(str).str.contains(concepto_buscado, case=False)]
    
    if not filtro_costo.empty:
        costo_hora_raw = filtro_costo.iloc[0]["costo_hora_usd"]
    else:
        costo_hora_raw = 4.55 if es_nocturno else 3.50
        
    costo_hora = limpiar_numero(costo_hora_raw, 3.50)
    costo_mano_obra = horas_estimadas * costo_hora

    # C. Costo de Insumos Químicos y Consumibles
    df_insumos[col_cobertura] = df_insumos[col_cobertura].apply(limpiar_numero)
    df_insumos["costo_unidad_usd"] = df_insumos["costo_unidad_usd"].apply(limpiar_numero)
    
    cobertura_promedio_m2 = df_insumos[col_cobertura].mean()
    costo_promedio_unidad = df_insumos["costo_unidad_usd"].mean()
    
    if cobertura_promedio_m2 > 0:
        costo_insumos_total = (area_m2 / cobertura_promedio_m2) * costo_promedio_unidad
    else:
        costo_insumos_total = area_m2 * 0.05

    # D. Costo Logístico y Movilización
    transporte_row = df_costos[df_costos["concepto"].astype(str).str.contains("Transporte", case=False)]
    costo_transporte = limpiar_numero(transporte_row.iloc[0]["costo_hora_usd"], 5.0) if not transporte_row.empty else 5.0
    
    depreciacion_row = df_costos[df_costos["concepto"].astype(str).str.contains("Depreciación|Equipos", case=False)]
    costo_depreciacion_base = limpiar_numero(depreciacion_row.iloc[0]["costo_hora_usd"], 2.0) if not depreciacion_row.empty else 2.0
    costo_depreciacion = costo_depreciacion_base * horas_estimadas

    # E. Totales Financieros
    costo_directo_total = costo_mano_obra + costo_insumos_total + costo_transporte + costo_depreciacion
    precio_final = costo_directo_total / (1 - (margen_utilidad_pct / 100))
    utilidad_neta = precio_final - costo_directo_total
    costo_metro_cuadrado = precio_final / area_m2 if area_m2 > 0 else 0

    # -------------------------------------------------------------
    # 3. INTERFAZ Y RESULTADOS PRINCIPALES
    # -------------------------------------------------------------
    st.markdown(f"## 🏢 Resumen Técnico: **{tipologia}**")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📐 Área Total", f"{area_m2} m²")
    col2.metric("🛡️ Nivel de Riesgo", nivel_riesgo)
    col3.metric("⏱️ Tiempo Operativo", f"{horas_estimadas:.2f} hrs")
    col4.metric("👥 Operarios Sugeridos", f"{num_operarios_recomendado} pers.")

    st.divider()

    st.markdown("### 💰 Cotización Final y Desglose Financiero")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    col_fin1.metric(" Costo Operativo Directo", f"${costo_directo_total:.2f} USD")
    col_fin2.metric("📈 Margen de Ganancia (Bruto)", f"${utilidad_neta:.2f} USD", f"{margen_utilidad_pct}%")
    col_fin3.metric("🏷️ PRECIO FINAL COTIZADO", f"${precio_final:.2f} USD")

    st.info(f"💡 **Precio unitario estimado:** **${costo_metro_cuadrado:.2f} USD / m²**")

    # -------------------------------------------------------------
    # 4. TABLAS DETALLADAS EN PESTAÑAS (TABS)
    # -------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["📊 Desglose de Costos Directos", "🧴 Insumos Asignados", "🧰 Equipos, Herramientas y EPP"])

    with tab1:
        df_desglose = pd.DataFrame({
            "Concepto del Gasto": ["Mano de Obra Directa", "Químicos y Consumibles", "Transporte y Logística", "Depreciación de Equipos"],
            "Costo Estimado (USD)": [costo_mano_obra, costo_insumos_total, costo_transporte, costo_depreciacion],
            "Porcentaje del Costo Directo (%)": [
                (costo_mano_obra / costo_directo_total) * 100 if costo_directo_total > 0 else 0,
                (costo_insumos_total / costo_directo_total) * 100 if costo_directo_total > 0 else 0,
                (costo_transporte / costo_directo_total) * 100 if costo_directo_total > 0 else 0,
                (costo_depreciacion / costo_directo_total) * 100 if costo_directo_total > 0 else 0
            ]
        })
        st.dataframe(df_desglose.style.format({"Costo Estimado (USD)": "${:.2f}", "Porcentaje del Costo Directo (%)": "{:.1f}%"}), use_container_width=True)

    with tab2:
        st.write("Catálogo general de insumos químicos dosificados según norma:")
        st.dataframe(df_insumos, use_container_width=True)

    with tab3:
        st.write("Equipos, indumentaria de seguridad e indumentaria asignada:")
        st.dataframe(df_herramientas, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
    st.info("Asegúrate de haber guardado 'base_datos.xlsx' en la carpeta 'data/'.")