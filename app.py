import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.io as pio
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Configuración inicial
st.set_page_config(page_title="💰 Finanzas Personales", layout="wide")

# Estilo personalizado para fondo, inputs y botones
st.markdown("""
    <style>
        body, .stApp {
            background-color: #0b1f33;
            color: #f0f0f0;
        }
        .css-18e3th9, .css-1d391kg, .block-container {
            background-color: #0b1f33;
            padding: 20px;
        }
        .stButton>button {
            background-color: #1e88e5;
            color: white;
            border-radius: 8px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #1565c0 !important;
            color: white !important;
        }
        .stButton>button:active {
            background-color: #0d47a1 !important;
            color: white !important;
        }
        .stTextInput>div>div>input,
        .stNumberInput>div>input,
        .stDateInput>div>input,
        .stSelectbox>div>div,
        .stTextArea>div>textarea {
            background-color: #274b6d;
            color: white;
            border-radius: 6px;
            border: 1px solid #274b6d;
        }
        .stTextInput>div>div>input:focus,
        .stNumberInput>div>input:focus,
        .stDateInput>div>input:focus,
        .stSelectbox>div>div:focus,
        .stTextArea>div>textarea:focus {
            border: 1px solid #1e88e5;
            box-shadow: 0 0 5px #1e88e5;
        }
        .stMetric {
            background-color: #1b2d45;
            padding: 10px;
            border-radius: 8px;
            color: #f0f0f0;
        }
        section[data-testid="stSidebar"] > div {
            background-color: #132d4f;
        }
    </style>
""", unsafe_allow_html=True)

# Tema oscuro para Plotly
pio.templates.default = "plotly_dark"

st.title("💰 Aplicación de Finanzas Personales")

# Inicializar Firebase
if "firebase_app" not in st.session_state:
    if not firebase_admin._apps:
        cred_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    st.session_state["firebase_app"] = True

db = firestore.client()

# ----- AUTENTICACIÓN desde Firebase -----
# Guardar usuario autenticado
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None

def verificar_credenciales(usuario, password):
    usuarios_ref = db.collection("usuarios")
    query = usuarios_ref.where("usuario", "==", usuario).where("password", "==", password).stream()
    if any(query):
        st.session_state["usuario_actual"] = usuario
        return True
    return False

def login():
    st.title("🔐 Inicio de Sesión")
    col1, col2 = st.columns([1, 1])
    with col1:
        usuario = st.text_input("👤 Usuario")
    with col2:
        clave = st.text_input("🔒 Contraseña", type="password")

    if st.button("Ingresar"):
        if verificar_credenciales(usuario, clave):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Credenciales inválidas")


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
    st.stop()

# Formas de pago
formas_pago = ["INTERBANK", "BCP", "YAPE", "PLIN", "EFECTIVO", "BBVA"]

# Función para cargar registros desde Firebase
# Función para cargar registros desde Firebase
def cargar_datos():
    docs = db.collection("movimientos").stream()
    registros = []
    for doc in docs:
        data = doc.to_dict()
        for campo in ["Fecha", "Fecha_Registro", "Fecha_Real", "Fecha_Actualizacion"]:
            if campo in data and data[campo] is not None:
                try:
                    dt = pd.to_datetime(data[campo])
                    if dt.tzinfo is not None:
                        dt = dt.tz_localize(None)
                    data[campo] = dt
                except Exception as e:
                    print(f"Error en campo {campo}: {e}")
                    data[campo] = pd.NaT
        data["id"] = doc.id
        registros.append(data)
    return registros

# Ajuste para evitar error al eliminar (solución TypeError: sequence item 1)
def convertir_valores_firebase(row):
    datos = {}
    for col, valor in row.items():
        if pd.isnull(valor):
            datos[col] = None
        elif isinstance(valor, pd.Timestamp):
            datos[col] = valor.to_pydatetime()
        elif isinstance(valor, (float, int, str)):
            datos[col] = valor
        else:
            datos[col] = str(valor)
    return datos

# Ingresos
ingresos = {
    "Vivienda": {"Cuota Banco": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Mantenimiento": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Luz": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Internet": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Calidda": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Amortización": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"]},
    "Aseo (Limpieza)": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []},
    "Alimentos": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []},
    "Servicios": {"Taxi": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Educación": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Medicina": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"], "Cita Médica": ["Sueldo", "Emprendimiento", "Agora", "Paypal", "Prestamo"]},
    "Entretenimiento": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []},
    "Otros": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []},
    "Ahorros": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []},
    "Manuntención": {"Sueldo": [], "Emprendimiento": [], "Bono": [], "Negocio": [], "Agora": [], "Paypal": [], "Préstamo": []}
}

# Egresos
egresos = {
    "Vivienda": {"Cuota Banco": [], "Mantenimiento": [], "Luz": [], "Internet": [], "Calidda": [], "Amortización": [], "Objetos": []},
    "Aseo (Limpieza)": {"Detergente": [], "Jabón": [], "Aromatizantes": [], "PrestoBarba": [], "Shampoo": [], "Objetos": []},
    "Alimentos": {"Carne": [], "Pollo": [], "Frutas": [], "Verduras": [], "Lácteos": [], "Especería": [], "Abarrotes": [], "Cereales": [], "Panadería": [], "Menú": [], "Restaurante": []},
    "Servicios": {"Taxi": [], "Educación": ["Matrícula", "Libros", "Mensualidad", "Materiales", "Uniforme"], "Medicina": [], "Cita Médica": []},
    "Entretenimiento": {"Viajes": [], "Suscripciones": ["DisneyPlus", "Netflix", "Paramount"]},
    "Otros": {"Regalos": [], "Emergencias": [], "Bebidas": [], "Snacks": []},
    "Ahorros": {"Ahorro General": []},
    "Manuntención": {"Taxi": [], "Educación": ["Matrícula", "Libros", "Mensualidad", "Materiales", "Uniforme"], "Medicina": [], "Cita Médica": [], "Regalos": [], "Juegos": [], "Vestimenta": [], "Dulces": [], "Pasajes": []}
}

meses_es = {
            "Jan": "Ene", "Feb": "Feb", "Mar": "Mar", "Apr": "Abr", "May": "May", "Jun": "Jun",
            "Jul": "Jul", "Aug": "Ago", "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dic"
        }

if "movimientos" not in st.session_state:
    st.session_state["movimientos"] = cargar_datos()
    
  
st.sidebar.title("📂 Navegación")
seccion = st.sidebar.radio("Ir a:", ["Formulario y Movimientos", "Visualización", "Actualizar Registros"])

if seccion == "Formulario y Movimientos":
    
    tipo = st.radio("Selecciona el tipo de movimiento", ["Ingreso", "Egreso"])
    detalle = "-"
    subdetalle = "-"
    fecha_registro = datetime.now()
    if tipo == "Ingreso":
        categoria = st.selectbox("Categoría de ingreso", list(ingresos.keys()))
        fecha = st.date_input("Fecha", value=date.today())
        primero_mes_siguiente = (fecha.replace(day=1) + timedelta(days=32)).replace(day=1)
        fecha_real = fecha if (primero_mes_siguiente - fecha).days >= 7 else primero_mes_siguiente
        
        if categoria in ["Vivienda", "Servicios"]:
            tipos_ingreso = list(ingresos[categoria].keys())
            tipo_ingreso = st.selectbox("Tipo", tipos_ingreso) if tipos_ingreso else "-"
            detalle_lista = ingresos[categoria][tipo_ingreso] if tipo_ingreso else []
            subdetalle = st.selectbox("Detalle", detalle_lista) if detalle_lista else "-"
            detalle = tipo_ingreso
        else:
            tipos_ingreso = list(ingresos[categoria].keys())
            subdetalle = st.selectbox("Tipo", tipos_ingreso) if tipos_ingreso else "-"
            detalle = "-"
    else:
        categoria = st.selectbox("Categoría de egreso", list(egresos.keys()))
        tipos_egreso = list(egresos[categoria].keys())
        tipo_egreso = st.selectbox("Tipo", tipos_egreso) if tipos_egreso else "-"
        detalle_lista = egresos[categoria][tipo_egreso] if tipo_egreso else []
        subdetalle = st.selectbox("Detalle", detalle_lista) if detalle_lista else "-"
        detalle = tipo_egreso
        fecha = st.date_input("Fecha", value=date.today())
        fecha_real = fecha

    forma_pago = st.selectbox("Forma de pago", formas_pago)
    monto = st.number_input("Monto (S/.)", min_value=0.0, format="%.2f")
    comentario = st.text_input("Comentario")
    
    if st.button("Registrar movimiento"):
        nuevo = {
            "Fecha": datetime.combine(fecha, datetime.min.time()),
            "Fecha_Registro": fecha_registro,
            "Fecha_Real": datetime.combine(fecha_real, datetime.min.time()),
            "Fecha_Actualizacion": None,
            "Tipo": tipo,
            "Categoría": categoria,
            "Detalle": detalle,
            "Subdetalle": subdetalle,
            "Forma de pago": forma_pago,
            "Monto": monto,
            "Comentario": comentario,
            "Usuario": st.session_state["usuario_actual"]
        }
        st.session_state["movimientos"].append(nuevo)
        db.collection("movimientos").add(nuevo)
        st.success("✅ Movimiento registrado correctamente")
    
    if st.session_state["movimientos"]:
        df = pd.DataFrame(st.session_state["movimientos"])
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        df["Fecha_Real"] = pd.to_datetime(df["Fecha_Real"])
        orden_meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        df["Mes_Label"] = df["Fecha_Real"].dt.strftime("%b %Y")
        df["Mes_Label"] = df["Mes_Label"].apply(lambda x: x.replace(x[:3], meses_es.get(x[:3], x[:3])))
        df["Mes_Label"] = pd.Categorical(
            df["Mes_Label"],
            categories=sorted(df["Mes_Label"].unique(), key=lambda x: (int(x[-4:]), orden_meses_es.index(x[:3]))),
            ordered=True
        )

        # Filtros interactivos
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            mes_seleccionado = st.selectbox("📅 Filtrar por mes", ["Todos"] + list(df["Mes_Label"].unique()), index=0)
        with colf2:
            tipo_seleccionado = st.selectbox("🔁 Filtrar por tipo", ["Todos"] + list(df["Tipo"].unique()), index=0)
        with colf3:
            categoria_seleccionada = st.selectbox("📂 Filtrar por categoría", ["Todos"] + list(df["Categoría"].unique()), index=0)
    
        # Aplicar filtros
        df_filtrado = df.copy()
        if mes_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Mes_Label"] == mes_seleccionado]
        if tipo_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == tipo_seleccionado]
        if categoria_seleccionada != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Categoría"] == categoria_seleccionada]
    
        def color_columna_tipo(val):
            if val == "Ingreso":
                return "background-color: #d4edda; color: green;"
            elif val == "Egreso":
                return "background-color: #f8d7da; color: red;"
            return ""
    
        st.markdown("---")
        st.subheader("📊 Movimientos registrados")
    
        columnas_visibles = ["Fecha_Real", "Tipo", "Categoría", "Detalle", "Subdetalle", "Forma de pago", "Monto", "Comentario"]
        styled_df = df_filtrado[columnas_visibles].style.applymap(color_columna_tipo, subset=["Tipo"])
        st.dataframe(styled_df, use_container_width=True)

elif seccion == "Actualizar Registros":
    st.subheader("🖉 Editar o eliminar registros existentes")
    
    df = pd.DataFrame(st.session_state["movimientos"])
    df = df.sort_values("Fecha_Registro", ascending=False).reset_index(drop=True)

    if df.empty:
        st.info("No hay registros para actualizar.")
        st.stop()

    # Seleccionar índice visible para edición
    seleccion = st.selectbox("Selecciona un registro para editar o eliminar", df.index)
    seleccionado = df.loc[seleccion]

    # Mostrar formulario para editar
    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"], index=["Ingreso", "Egreso"].index(seleccionado["Tipo"]))
            categoria = st.text_input("Categoría", seleccionado["Categoría"])
            detalle = st.text_input("Detalle", seleccionado["Detalle"])
            subdetalle = st.text_input("Subdetalle", seleccionado["Subdetalle"])
        with col2:
            forma_pago = st.selectbox("Forma de pago", formas_pago, index=formas_pago.index(seleccionado["Forma de pago"]))
            monto = st.number_input("Monto (S/.)", value=float(seleccionado["Monto"]))
            fecha = st.date_input("Fecha", value=seleccionado["Fecha"].date())
            comentario = st.text_input("Comentario", seleccionado["Comentario"])

        guardar = st.form_submit_button("Guardar cambios")
        eliminar = st.form_submit_button("Eliminar registro")

    doc_id = seleccionado.get("id", None)
    if not doc_id:
        st.error("Error: El registro seleccionado no tiene un ID válido.")
        st.stop()

    if guardar:
        if tipo == "Ingreso":
            fecha_real = fecha if (fecha.replace(day=1) + timedelta(days=32)).replace(day=1) - fecha >= timedelta(days=5) else (fecha.replace(day=1) + timedelta(days=32)).replace(day=1)
        else: 
            fecha_real = fecha
            
        actualizado = {
            "Fecha": datetime.combine(fecha, datetime.min.time()),
            "Fecha_Actualizacion": datetime.now(),
            "Fecha_Real": datetime.combine(fecha_real, datetime.min.time()),
            "Tipo": tipo,
            "Categoría": categoria,
            "Detalle": detalle,
            "Subdetalle": subdetalle,
            "Forma de pago": forma_pago,
            "Monto": monto,
            "Comentario": comentario,
            "Usuario": st.session_state["usuario_actual"]
        }
        db.collection("movimientos").document(doc_id).update(actualizado)
        st.success("✅ Registro actualizado correctamente")
        st.session_state["movimientos"] = cargar_datos()
        st.rerun()

    if eliminar:
        db.collection("movimientos").document(doc_id).delete()
        st.success("✅ Registro eliminado correctamente")
        st.session_state["movimientos"] = cargar_datos()
        st.rerun()
            
    st.markdown("---")
    st.dataframe(df.drop(columns=["id", "Fecha_Registro", "Fecha_Actualizacion"])[["Tipo", "Fecha_Real", "Fecha", "Categoría", "Monto", "Detalle", "Subdetalle", "Usuario", "Forma de pago", "Comentario"]], use_container_width=True)

elif seccion == "Visualización":
    if st.session_state["movimientos"]:
        df = pd.DataFrame(st.session_state["movimientos"])
        df["Fecha_Real"] = pd.to_datetime(df["Fecha_Real"], errors='coerce')
        df["Mes"] = df["Fecha_Real"].dt.to_period("M").astype(str)
        df["Mes_Ordenado"] = df["Fecha_Real"].dt.to_period("M").dt.to_timestamp()
        orden_meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        df["Mes_Label"] = df["Fecha_Real"].dt.strftime("%b %Y")
        df["Mes_Label"] = df["Mes_Label"].apply(lambda x: x.replace(x[:3], meses_es.get(x[:3], x[:3])))
        df["Mes_Label"] = pd.Categorical(
            df["Mes_Label"],
            categories=sorted(df["Mes_Label"].unique(), key=lambda x: (int(x[-4:]), orden_meses_es.index(x[:3]))),
            ordered=True
        )

        st.subheader("📈 Indicadores Generales")
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            tipos_seleccionados = st.multiselect("🔁 Filtrar por tipo", ["Ingreso", "Egreso", "Ahorros"], default=["Ingreso", "Egreso"])
        with colf2:
            fechas_unicas = sorted(df["Mes"].unique())
            fechas_seleccionadas = st.multiselect("📅 Filtrar por periodo (YYYY-MM)", fechas_unicas, default=fechas_unicas)
        with colf3:
            categorias = ["Todas"] + sorted(df["Categoría"].dropna().unique())
            filtro_categoria = st.selectbox("Filtrar por categoría", categorias)

        #df_viz = df[df["Mes"].isin(fechas_seleccionadas)].copy()
        df_viz = df.copy()
        
        filtro_subdetalle = "Todas"
        if filtro_categoria != "Todas":
            df_viz = df_viz[df_viz["Categoría"] == filtro_categoria]
            subcategorias = ["Todas"] + sorted(df_viz["Detalle"].dropna().unique())
            filtro_subdetalle = st.selectbox("📂 Filtrar por categoría", subcategorias)
            if filtro_subdetalle != "Todas":
                df_viz = df_viz[df_viz["Detalle"] == filtro_subdetalle]

        if "Ahorros" in tipos_seleccionados:
            df_ahorro = df_viz[(df_viz["Tipo"] == "Egreso") & (df_viz["Categoría"] == "Ahorros")]
        else:
            df_ahorro = pd.DataFrame(columns=df_viz.columns)

        df_viz = df_viz[(df_viz["Tipo"].isin(tipos_seleccionados)) | ("Ahorros" in tipos_seleccionados and df_viz["Categoría"] == "Ahorros")]
        df_viz_ff = df_viz[df["Mes"].isin(fechas_seleccionadas)].copy()
        
        ingresos_df = df_viz_ff[df_viz_ff["Tipo"] == "Ingreso"]
        egresos_df = df_viz_ff[(df_viz_ff["Tipo"] == "Egreso") & (df_viz_ff["Categoría"] != "Ahorros")]
        ahorro_total = df_ahorro["Monto"].sum()
        total_egresos_sin_ahorro = egresos_df["Monto"].sum()
        total_ingresos = ingresos_df["Monto"].sum()
        variacion = total_ingresos - total_egresos_sin_ahorro
        if total_ingresos == 0 or total_ingresos is None:
            total_ingresos = 0
        porcentaje = (variacion / total_ingresos) * 100 if total_ingresos else -100
            
        c1, c2 = st.columns(2)
        with c1:
            st.metric("💚 Ingresos", f"S/ {total_ingresos:,.2f}")
            st.metric("❤️ Egresos", f"S/ {total_egresos_sin_ahorro:,.2f}")
            st.metric("🔄 Variación", f"S/ {variacion:,.2f}", delta=f"{porcentaje:.1f}%")
        with c2:
            st.metric("💰 Ahorros", f"S/ {ahorro_total:,.2f}")

        st.markdown("---")
        df_group = df_viz.groupby(["Mes_Label", "Tipo"])["Monto"].sum().reset_index()
        fig = px.line(df_group, x="Mes_Label", y="Monto", color="Tipo", markers=True,
                    title="📊 Evolutivo de Ingresos vs Egresos",
                     color_discrete_map = {
                      "Ingreso": "#0cb7f2",  # Morado
                      "Egreso": "#ff69b4"    # Rosado tenue
                      })
        fig.update_layout(xaxis_title="Mes Año", yaxis_title="Monto (S/.)", legend_title="Tipo")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 Distribución por Categoría")
        df_categoria = df_viz_ff.groupby(["Tipo", "Categoría"])["Monto"].sum().reset_index()
        fig_cat = px.bar(df_categoria, x="Categoría", y="Monto", color="Tipo", barmode="group",
                         title="Distribución de Montos por Categoría",
                        color_discrete_map={
                            "Ingreso": "#0cb7f2",  # Morado
                            "Egreso": "#ff69b4"    # Rosado tenue
                        })
        st.plotly_chart(fig_cat, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 Variación Mensual")
        df_mes_cat = df_viz.pivot_table(index=["Mes_Label"], columns="Tipo", values="Monto", aggfunc="sum", fill_value=0).reset_index()
        df_mes_cat["Variación"] = df_mes_cat.get("Ingreso", 0) - df_mes_cat.get("Egreso", 0)
        df_mes_cat["Color"] = df_mes_cat["Variación"].apply(lambda x: "Variación Positiva" if x >= 0 else "Variación Negativa")
        fig_var_mes = px.bar(df_mes_cat, x="Mes_Label", y="Variación", color="Color", barmode="group",
                             title="Variación Mensual", color_discrete_map={
                                 "Variación Positiva": "lightgreen",
                                 "Variación Negativa": "red"
                             })
        fig_var_mes.update_layout(xaxis_title="Mes Año", height=400)
        st.plotly_chart(fig_var_mes, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 Variación total por Categoría")
        df_cat = df_viz_ff.pivot_table(index="Categoría", columns="Tipo", values="Monto", aggfunc="sum", fill_value=0).reset_index()
        df_cat["Variación"] = df_cat.get("Ingreso", 0) - df_cat.get("Egreso", 0)
        df_cat["Color"] = df_cat["Variación"].apply(lambda x: "Positiva" if x >= 0 else "Negativa")
        fig_var_cat = px.bar(df_cat, x="Categoría", y="Variación", color="Color", barmode="group",
                             title="Variación total por categoría", color_discrete_map={
                                 "Positiva": "lightgreen",
                                 "Negativa": "red"
                             })
        st.plotly_chart(fig_var_cat, use_container_width=True)

        if filtro_categoria == "Vivienda":
            st.markdown("---")
            st.subheader("📊 Comparativa Ingresos vs Egresos en Vivienda")
            df_viv = df_viz_ff[df_viz_ff["Categoría"] == "Vivienda"]
            df_viv_group = df_viv.groupby(["Detalle", "Tipo"])["Monto"].sum().reset_index()

            fig_viv = px.bar(df_viv_group, x="Detalle", y="Monto", color="Tipo", barmode="group",
                             title="Comparativa por Subcategoría en Vivienda",
                             color_discrete_map = {
                                  "Ingreso": "#0cb7f2",  # Morado
                                  "Egreso": "#ff69b4"    # Rosado tenue
                                  })

            # Añadir las etiquetas con el valor total
            for index, row in df_viv_group.iterrows():
                fig_viv.add_annotation(
                    x=row["Detalle"],
                    y=row["Monto"],
                    text=f"${row['Monto']:,.2f}",
                    xanchor='center',
                    yanchor='top',
                    yref='y',  # Asegurarse de que la referencia vertical sea el eje y
                    yshift=5,  # Desplazar ligeramente hacia arriba (ajusta este valor si es necesario)
                    showarrow=False,
                    font=dict(size=18, color='white')
                )
            st.plotly_chart(fig_viv, use_container_width=True)
            
        if filtro_categoria == "Servicios":
            st.markdown("---")
            st.subheader("📊 Comparativa Ingresos vs Egresos en Servicios")
            df_viv = df_viz_ff[df_viz_ff["Categoría"] == "Servicios"]
            df_viv_group = df_viv.groupby(["Detalle", "Tipo"])["Monto"].sum().reset_index()
            fig_viv = px.bar(df_viv_group, x="Detalle", y="Monto", color="Tipo", barmode="group",
                             title="Comparativa por Subcategoría en Servicios")
            st.plotly_chart(fig_viv, use_container_width=True)
            
        
            
    else:
        st.info("🔄 Aún no has registrado movimientos para visualizar.")
