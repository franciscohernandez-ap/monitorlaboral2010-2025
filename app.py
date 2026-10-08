import streamlit as st
import pandas as pd
from pathlib import Path
import warnings

# Ocultar advertencias
warnings.filterwarnings('ignore', category=UserWarning)

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard Empleo INE", page_icon="📊", layout="wide")


# ==========================================
# 2. CARGA DE DATOS (Lectura directa CSV)
# ==========================================
@st.cache_data
def cargar_datos():
    """Carga los datasets CSV desde la carpeta data o desde la raíz"""
    base_dir = Path(__file__).resolve().parent

    # Busca en data/ o en la raíz por si acaso
    ruta_gen = base_dir / "data" / "empleo_general.csv"
    if not ruta_gen.exists():
        ruta_gen = base_dir / "empleo_general.csv"

    ruta_sub = base_dir / "data" / "empleo_subutilizacion.csv"
    if not ruta_sub.exists():
        ruta_sub = base_dir / "empleo_subutilizacion.csv"

    try:
        df_gen = pd.read_csv(ruta_gen)
        df_sub = pd.read_csv(ruta_sub)
        return df_gen.round(1), df_sub.round(1)
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame(), pd.DataFrame()


df_general, df_subutilizacion = cargar_datos()

if df_general.empty or df_subutilizacion.empty:
    st.warning("⚠️ No se pudieron cargar los archivos CSV. Verifica que existan en el repositorio.")
    st.stop()

# ==========================================
# 3. BARRA LATERAL (Filtros)
# ==========================================
st.sidebar.header("Filtros Territoriales")

regiones_disponibles = df_general['region'].unique().tolist()
regiones_seleccionadas = st.sidebar.multiselect(
    "Regiones a comparar:",
    options=regiones_disponibles,
    default=["Chile", "La Araucanía"] if "La Araucanía" in regiones_disponibles else [regiones_disponibles[0]]
)

anio_max = int(df_general['anio'].max())
anio_seleccionado = st.sidebar.slider("Año de análisis", 2010, anio_max, anio_max)

st.sidebar.markdown("---")
st.sidebar.header("Filtros Demográficos")
st.sidebar.caption("Nota: Estos filtros solo aplican a la pestaña de Empleo General.")

# Filtros dependientes
sexos_disp = df_general['sexo'].unique().tolist()
index_sexo = sexos_disp.index("Ambos") if "Ambos" in sexos_disp else 0
sexo_seleccionado = st.sidebar.selectbox("Sexo:", sexos_disp, index=index_sexo)

edades_disp = df_general[df_general['sexo'] == sexo_seleccionado]['grupo_etario'].unique().tolist()
index_defecto = edades_disp.index("Total") if "Total" in edades_disp else 0
edad_seleccionada = st.sidebar.selectbox("Grupo Etario:", edades_disp, index=index_defecto)

# ==========================================
# 4. FILTRADO DE DATOS
# ==========================================
df_general = df_general.drop_duplicates(subset=['anio', 'region', 'sexo', 'grupo_etario'])
df_subutilizacion = df_subutilizacion.drop_duplicates(subset=['anio', 'region'])

df_gen_filtrado = df_general[
    (df_general['anio'] == anio_seleccionado) &
    (df_general['region'].isin(regiones_seleccionadas)) &
    (df_general['sexo'] == sexo_seleccionado) &
    (df_general['grupo_etario'] == edad_seleccionada)
    ]

df_gen_historico = df_general[
    (df_general['region'].isin(regiones_seleccionadas)) &
    (df_general['sexo'] == sexo_seleccionado) &
    (df_general['grupo_etario'] == edad_seleccionada)
    ]

df_sub_filtrado = df_subutilizacion[
    (df_subutilizacion['anio'] == anio_seleccionado) &
    (df_subutilizacion['region'].isin(regiones_seleccionadas))
    ]

df_sub_historico = df_subutilizacion[
    (df_subutilizacion['region'].isin(regiones_seleccionadas))
]

# ==========================================
# 5. LIENZO PRINCIPAL
# ==========================================
st.title("📊 Monitor de Empleo Nacional y Regional (Chile)")
st.markdown(
    "Plataforma interactiva de indicadores laborales basada en datos del Instituto Nacional de Estadística (INE).")

if len(regiones_seleccionadas) == 0:
    st.warning("👈 Por favor, selecciona al menos una región en la barra lateral para visualizar los datos.")
else:
    tab1, tab2 = st.tabs(["👥 Empleo General", "📉 Subutilización Laboral"])

    # --- PESTAÑA 1: EMPLEO GENERAL ---
    with tab1:
        st.subheader(f"Panorama Laboral {anio_seleccionado} ({sexo_seleccionado} | {edad_seleccionada})")
        st.caption(
            "Indicadores principales del mercado laboral, midiendo el volumen y la proporción de personas insertas o buscando insertarse en la economía.")

        columnas_kpi = st.columns(len(regiones_seleccionadas))
        for i, region in enumerate(regiones_seleccionadas):
            dato_region = df_gen_filtrado[df_gen_filtrado['region'] == region]
            with columnas_kpi[i]:
                if not dato_region.empty:
                    tasa_des = dato_region['tasa_desocupacion'].values[0]
                    fuerza = dato_region['fuerza_trabajo'].values[0]
                    st.metric(
                        label=f"Tasa de Desocupación - {region}",
                        value=f"{tasa_des}%",
                        help="Porcentaje de la Fuerza de Trabajo que se encuentra desocupada."
                    )
                    fuerza_real = fuerza * 1000
                    st.caption(f"Fuerza de trabajo: {fuerza_real:,.0f} personas")
                else:
                    st.metric(label=region, value="Sin datos")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Evolución Histórica Tasa Desocupación (%)**")
            if not df_gen_historico.empty:
                df_linea = df_gen_historico.pivot(index='anio', columns='region', values='tasa_desocupacion')
                st.line_chart(df_linea)
            else:
                st.info("No hay suficientes datos históricos para esta combinación.")

        with col2:
            st.markdown(f"**Volumen de Ocupados vs Desocupados ({anio_seleccionado})**")
            if not df_gen_filtrado.empty:
                df_barras = df_gen_filtrado.set_index('region')[['ocupados', 'desocupados']]
                df_barras = df_barras * 1000
                st.bar_chart(df_barras)
            else:
                st.info("No hay datos disponibles para la combinación seleccionada.")

        with st.expander("ℹ️ Glosario INE: ¿Cómo se componen estos indicadores?"):
            st.markdown("""
            **Conceptos Clave del Mercado Laboral:**
            * **Población en Edad de Trabajar (PET):** Todas las personas de 15 años y más. Es la base demográfica sobre la cual se calcula el resto de los indicadores.
            * **Fuerza de Trabajo (Activos):** Suma de todas las personas Ocupadas y Desocupadas. Representa a todos los que están participando en el mercado laboral.
            * **Ocupados:** Personas en edad de trabajar que durante la semana de referencia trabajaron al menos 1 hora a cambio de un pago o beneficio.
            * **Desocupados:** Personas sin trabajo, que están disponibles para trabajar y que han buscado activamente empleo durante las últimas cuatro semanas. 
            * **Inactivos (Fuera de la Fuerza de Trabajo):** Personas que no están ocupadas ni desocupadas (ej. estudiantes a tiempo completo, jubilados, labores de cuidado no remuneradas).
            """)

    # --- PESTAÑA 2: SUBUTILIZACIÓN ---
    with tab2:
        st.subheader(f"Presión y Subutilización {anio_seleccionado}")
        st.info(
            "📌 **Nota metodológica:** Los indicadores de esta pestaña representan los totales a nivel nacional o regional. Los filtros demográficos (Sexo y Grupo Etario) no alteran estos resultados.")
        st.caption(
            "Indicadores complementarios que miden la precariedad y el déficit de empleo más allá de la desocupación tradicional.")

        col_kpi_sub = st.columns(len(regiones_seleccionadas))
        for i, region in enumerate(regiones_seleccionadas):
            dato_sub = df_sub_filtrado[df_sub_filtrado['region'] == region]
            with col_kpi_sub[i]:
                if not dato_sub.empty:
                    su4 = dato_sub['su4'].values[0]
                    tpi = dato_sub['ocupados_tiempo_parcial_involuntario'].values[0]
                    st.metric(
                        label=f"Tasa Global (SU4) - {region}",
                        value=f"{su4}%",
                        help="El SU4 suma a los desocupados, a los que trabajan part-time por obligación (TPI) y a los inactivos que ya se cansaron de buscar empleo."
                    )
                    tpi_real = tpi * 1000
                    st.caption(f"Tiempo Parcial Involuntario: {tpi_real:,.0f} personas")
                else:
                    st.metric(label=region, value="Sin datos")

        st.markdown("---")

        st.markdown("**Evolución Histórica Tasa Global de Subutilización (SU4 %)**")
        if not df_sub_historico.empty:
            df_linea_sub = df_sub_historico.pivot(index='anio', columns='region', values='su4')
            st.line_chart(df_linea_sub)
        else:
            st.info("No hay suficientes datos históricos de subutilización para graficar.")

        with st.expander("ℹ️ ¿Qué significa este gráfico y cómo se interpreta?"):
            st.markdown("""
            **La Tasa Global de Subutilización (SU4)** es el indicador más amplio de déficit laboral. 
            A diferencia de la Desocupación tradicional (que solo cuenta a quienes no tienen trabajo y están buscando uno), el SU4 incluye a:
            * **Desocupados:** Personas sin trabajo buscando activamente.
            * **Tiempo Parcial Involuntario:** Personas que trabajan menos de 30 horas semanales, pero quieren y están disponibles para trabajar más.
            * **Fuerza de Trabajo Potencial:** Personas que quieren trabajar pero no buscan activamente (por desaliento, responsabilidades familiares, etc.).

            *Si el SU4 es significativamente mayor que la tasa de desocupación, indica una alta precarización en la calidad del empleo regional.*
            """)