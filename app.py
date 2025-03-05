import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Clave secreta para producción

# ================= CONFIGURACIÓN DE ARCHIVOS =================
DATA_DIR = "data"
REPORTES_DIR = "reportes"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTES_DIR, exist_ok=True)

EXCEL_ADMINS = os.path.join(DATA_DIR, "administradores.xlsx")
EXCEL_CLIENTES = os.path.join(DATA_DIR, "clientes.xlsx")
EXCEL_CONSUMOS = os.path.join(DATA_DIR, "consumos.xlsx")
EXCEL_PRODUCTOS = os.path.join(DATA_DIR, "productos.xlsx")

# Columnas para consumos
CONSUMOS_COLS = ["Cédula", "Producto", "Cantidad", "Precio", "Método_Pago", "Fecha_Hora", "Estado"]

# ================= INICIALIZACIÓN DE ARCHIVOS =================
def inicializar_archivos():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # Administradores
    if not os.path.exists(EXCEL_ADMINS):
        pd.DataFrame(columns=["Usuario", "Clave"]).to_excel(EXCEL_ADMINS, index=False)
    
    # Clientes
    if not os.path.exists(EXCEL_CLIENTES):
        pd.DataFrame(columns=["Cédula", "Nombre"]).to_excel(EXCEL_CLIENTES, index=False)
    
    # Productos
    if not os.path.exists(EXCEL_PRODUCTOS):
        productos_iniciales = [
            {"Producto": "Salchipapas", "Precio": 3.50},
            {"Producto": "Chochos con tostado", "Precio": 2.50},
            {"Producto": "Coca cola pequeña", "Precio": 1.50},
            {"Producto": "Gaseosa de sabores mediana", "Precio": 2.00},
            {"Producto": "Agua sin gas", "Precio": 1.00},
            {"Producto": "Fuze Tea mediano", "Precio": 2.20},
            {"Producto": "Güitig grande", "Precio": 2.50},
            {"Producto": "Coca cola grande", "Precio": 2.50},
            {"Producto": "Gaseosa de sabores grande", "Precio": 2.50},
            {"Producto": "Fuze Tea grande", "Precio": 2.50},
            {"Producto": "Gatorade", "Precio": 2.80},
            {"Producto": "Papas sin marca", "Precio": 1.00},
            {"Producto": "Chifles de Sal", "Precio": 1.20},
            {"Producto": "Chifles de Dulce", "Precio": 1.20},
            {"Producto": "Galletitas", "Precio": 0.80}
        ]
        pd.DataFrame(productos_iniciales).to_excel(EXCEL_PRODUCTOS, index=False)
    
    # Consumos
    if not os.path.exists(EXCEL_CONSUMOS):
        pd.DataFrame(columns=CONSUMOS_COLS).to_excel(EXCEL_CONSUMOS, index=False)

inicializar_archivos()

# ================= DECORADORES DE AUTENTICACIÓN =================
def login_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logueado'):
            return redirect(url_for('login_admin'))
        return f(*args, **kwargs)
    return decorated_function

def login_caja_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('caja_logueada'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ================= RUTAS PRINCIPALES =================
@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        rol = request.form.get("rol")
        if rol == "admin":
            return redirect(url_for('login_admin'))
        elif rol == "caja":
            return redirect(url_for('login'))
    return render_template("inicio.html")

# ================= SISTEMA ADMINISTRADOR =================
@app.route("/admin/login", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        clave = request.form.get("clave")
        
        df = pd.read_excel(EXCEL_ADMINS)
        admin = df[df["Usuario"] == usuario]
        
        if not admin.empty and check_password_hash(admin.iloc[0]["Clave"], clave):
            session['admin_logueado'] = True
            return redirect(url_for('panel_admin'))
        
        return render_template("login_admin.html", error="Credenciales incorrectas")
    return render_template("login_admin.html")

@app.route("/admin/registro", methods=["GET", "POST"])
def registro_admin():
    df = pd.read_excel(EXCEL_ADMINS)
    if len(df) >= 3:
        return render_template("error.html", mensaje="Máximo de 3 administradores alcanzado")
    
    if request.method == "POST":
        usuario = request.form.get("usuario")
        clave = generate_password_hash(request.form.get("clave"))
        
        nuevo_admin = pd.DataFrame([[usuario, clave]], columns=["Usuario", "Clave"])
        df = pd.concat([df, nuevo_admin], ignore_index=True)
        df.to_excel(EXCEL_ADMINS, index=False)
        return redirect(url_for('login_admin'))
    
    return render_template("registro_admin.html")

@app.route("/admin/panel")
@login_admin_required
def panel_admin():
    return render_template("panel_admin.html")

@app.route("/admin/productos", methods=["GET", "POST"])
@login_admin_required
def admin_productos():
    df = pd.read_excel(EXCEL_PRODUCTOS)
    
    if request.method == "POST":
        if 'eliminar' in request.form:
            indice = int(request.form.get('indice'))
            df = df.drop(index=indice).reset_index(drop=True)
            df.to_excel(EXCEL_PRODUCTOS, index=False)
            return redirect(url_for('admin_productos'))
        
        if 'guardar' in request.form:
            indice = request.form.get('indice')
            producto = request.form.get('producto')
            precio = float(request.form.get('precio'))
            
            if indice and indice != 'None':
                indice = int(indice)
                df.at[indice, 'Producto'] = producto
                df.at[indice, 'Precio'] = precio
            else:
                nuevo = pd.DataFrame([[producto, precio]], columns=["Producto", "Precio"])
                df = pd.concat([df, nuevo], ignore_index=True)
            
            df.to_excel(EXCEL_PRODUCTOS, index=False)
            return redirect(url_for('admin_productos'))
    
    return render_template("admin_productos.html", 
                         productos=df.to_dict("records"), 
                         enumerate=enumerate)

@app.route("/admin/clientes", methods=["GET", "POST"])
@login_admin_required
def admin_clientes():
    df = pd.read_excel(EXCEL_CLIENTES)
    
    if request.method == "POST":
        if 'eliminar' in request.form:
            indice = int(request.form.get('indice'))
            df = df.drop(index=indice).reset_index(drop=True)
            df.to_excel(EXCEL_CLIENTES, index=False)
            return redirect(url_for('admin_clientes'))
        
        if 'guardar' in request.form:
            indice = request.form.get('indice')
            cedula = request.form.get('cedula')
            nombre = request.form.get('nombre')
            
            if indice and indice != 'None':
                indice = int(indice)
                df.at[indice, 'Cédula'] = str(cedula)
                df.at[indice, 'Nombre'] = nombre
            else:
                if str(cedula) in df['Cédula'].astype(str).values:
                    return render_template("error.html", mensaje="La cédula ya está registrada")
                nuevo = pd.DataFrame([[str(cedula), nombre]], columns=["Cédula", "Nombre"])
                df = pd.concat([df, nuevo], ignore_index=True)
            
            df.to_excel(EXCEL_CLIENTES, index=False)
            return redirect(url_for('admin_clientes'))
    
    return render_template("admin_clientes.html", 
                         clientes=df.to_dict("records"), 
                         enumerate=enumerate)

@app.route("/admin/reportes", methods=["GET", "POST"])
@login_admin_required
def generar_reportes():
    if request.method == "POST":
        try:
            fecha = datetime.strptime(request.form.get("fecha"), "%Y-%m-%d")
            fecha_str = fecha.strftime("%d/%m/%Y")
        except:
            return render_template("error.html", mensaje="Formato de fecha inválido")
        
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        
        # Generar reporte
        reporte_path = os.path.join(REPORTES_DIR, f"reporte_{fecha_str.replace('/', '-')}.xlsx")
        with pd.ExcelWriter(reporte_path) as writer:
            df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
            df_consumos[df_consumos['Fecha_Hora'].str.contains(fecha_str)].to_excel(writer, sheet_name='Consumos', index=False)
        
        return send_file(reporte_path, as_attachment=True)
    
    return render_template("generar_reporte.html")

# ================= SISTEMA CAJA =================
@app.route("/caja/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session['caja_logueada'] = True
        seccion = request.form.get("seccion")
        
        if seccion == "bar":
            return redirect(url_for('clientes'))
        elif seccion == "entradas":
            return redirect(url_for('venta_entradas'))  # Nueva función a crear
        elif seccion == "cocina":
            return redirect(url_for('cocina'))
    
    return render_template("login.html")

@app.route("/caja/entradas")
@login_caja_required
def venta_entradas():
    # Lógica para venta de entradas (implementar según necesidades)
    return render_template("venta_entradas.html")

@app.route("/caja/clientes", methods=["GET", "POST"])
@login_caja_required
def clientes():
    # Leer clientes y consumos
    df_clientes = pd.read_excel(EXCEL_CLIENTES)
    df_consumos = pd.read_excel(EXCEL_CONSUMOS)
    
    # Convertir cédulas a string para comparaciones
    df_clientes["Cédula"] = df_clientes["Cédula"].astype(str)
    df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
    
    # Registrar nuevo cliente (POST)
    if request.method == "POST":
        cedula = request.form.get("cedula")
        nombre = request.form.get("nombre")
        
        if cedula not in df_clientes["Cédula"].values:
            nuevo_cliente = pd.DataFrame([[str(cedula), nombre]], columns=["Cédula", "Nombre"])
            df_clientes = pd.concat([df_clientes, nuevo_cliente], ignore_index=True)
            df_clientes.to_excel(EXCEL_CLIENTES, index=False)
    
    # Preparar datos para la plantilla
    clientes_con_estado = []
    for _, row in df_clientes.iterrows():
        cedula = str(row["Cédula"])
        tiene_pendientes = not df_consumos[
            (df_consumos["Cédula"] == cedula) & 
            (df_consumos["Estado"] == "Pendiente")
        ].empty
        
        clientes_con_estado.append({
            "Cédula": cedula,
            "Nombre": row["Nombre"],
            "tiene_pendientes": tiene_pendientes
        })
    
    return render_template("clientes.html", clientes=clientes_con_estado)

@app.route("/caja/consumos/<cedula>", methods=["GET", "POST"])
@login_caja_required
def consumos(cedula):
    try:
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        df_clientes["Cédula"] = df_clientes["Cédula"].astype(str)
        cliente = df_clientes[df_clientes["Cédula"] == cedula].iloc[0].to_dict()
    except:
        return redirect(url_for('clientes'))
    
    df_productos = pd.read_excel(EXCEL_PRODUCTOS)
    
    if request.method == "POST":
        producto = request.form.get("producto")
        cantidad = int(request.form.get("cantidad"))
        fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Obtener precio del producto
        precio = df_productos[df_productos["Producto"] == producto]["Precio"].values[0]
        
        # Crear registro sin método de pago
        nuevo_consumo = pd.DataFrame([[
            cedula,
            producto,
            cantidad,
            precio,
            "",  # Método_Pago vacío inicialmente
            fecha_hora,
            "Pendiente"
        ]], columns=CONSUMOS_COLS)
        
        # Guardar en Excel
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_consumos = pd.concat([df_consumos, nuevo_consumo], ignore_index=True)
        df_consumos.to_excel(EXCEL_CONSUMOS, index=False)
    
    # Calcular total
    df_consumos = pd.read_excel(EXCEL_CONSUMOS)
    df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
    consumos_cliente = df_consumos[df_consumos["Cédula"] == cedula]
    total = sum(consumos_cliente["Cantidad"] * consumos_cliente["Precio"])
    
    return render_template("consumos.html",
                         cliente=cliente,
                         productos=df_productos.to_dict("records"),
                         consumos=consumos_cliente.to_dict("records"),
                         total=total)

@app.route("/cierre_cuenta/<cedula>")
@login_caja_required
def cierre_cuenta(cedula):
    try:
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        df_clientes["Cédula"] = df_clientes["Cédula"].astype(str)
        cliente_df = df_clientes[df_clientes["Cédula"] == cedula]
        
        if cliente_df.empty:
            return redirect(url_for('clientes'))
        
        cliente = cliente_df.iloc[0].to_dict()
        
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
        consumos = df_consumos[(df_consumos["Cédula"] == cedula) & 
                              (df_consumos["Estado"] != "CANCELADO")]
        
        total = sum(row["Cantidad"] * row["Precio"] for _, row in consumos.iterrows())
        
        return render_template("cierre_cuenta.html",
                             cliente=cliente,
                             consumos=consumos.to_dict("records"),
                             total=total)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return redirect(url_for('clientes'))

@app.route("/marcar_pagado/<cedula>", methods=["POST"])
@login_caja_required
def marcar_pagado(cedula):
    try:
        # Obtener método de pago
        metodo_pago = request.form.get("metodo_pago")
        
        # Actualizar consumos
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
        
        mask = (df_consumos["Cédula"] == cedula) & (df_consumos["Estado"] == "Pendiente")
        df_consumos.loc[mask, "Estado"] = "CANCELADO"
        df_consumos.loc[mask, "Método_Pago"] = metodo_pago
        df_consumos.to_excel(EXCEL_CONSUMOS, index=False)
        
        # Eliminar cliente de la lista
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        df_clientes["Cédula"] = df_clientes["Cédula"].astype(str)
        df_clientes = df_clientes[df_clientes["Cédula"] != cedula]
        df_clientes.to_excel(EXCEL_CLIENTES, index=False)
        
        return redirect(url_for('clientes'))
    
    except Exception as e:
        print(f"Error al procesar pago: {str(e)}")
        return redirect(url_for('cierre_cuenta', cedula=cedula))

@app.route("/cerrar_caja")
@login_caja_required
def cerrar_caja():
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    
    df = pd.read_excel(EXCEL_CONSUMOS)
    try:
        consumos_hoy = df[df["Fecha_Hora"].str.contains(fecha_actual)]
    except:
        consumos_hoy = pd.DataFrame(columns=CONSUMOS_COLS)
    
    resumen_general = {
        "total_cancelado": 0,
        "total_pendiente": 0,
        "detalle": []
    }
    
    clientes_unico = df["Cédula"].unique()
    resumen_clientes = []
    
    for cedula in clientes_unico:
        cliente_consumos = df[(df["Cédula"] == cedula) & 
                             (df["Fecha_Hora"].str.contains(fecha_actual))]
        
        total_cliente = sum(row["Cantidad"] * row["Precio"] 
                           for _, row in cliente_consumos.iterrows())
        
        estado = "CANCELADO" if all(cliente_consumos["Estado"] == "CANCELADO") else "PENDIENTE"
        
        resumen_clientes.append({
            "cedula": cedula,
            "total": total_cliente,
            "estado": estado
        })
        
        if estado == "CANCELADO":
            resumen_general["total_cancelado"] += total_cliente
        else:
            resumen_general["total_pendiente"] += total_cliente
    
    resumen_general["total_general"] = resumen_general["total_cancelado"] + resumen_general["total_pendiente"]
    
    return render_template("cierre_caja.html",
                         fecha=fecha_actual,
                         resumen_clientes=resumen_clientes,
                         resumen_general=resumen_general)

# ================= SISTEMA COCINA =================
@app.route("/cocina")
def cocina():
    df = pd.read_excel(EXCEL_CONSUMOS)
    df["Cédula"] = df["Cédula"].astype(str)
    pedidos = df[df["Estado"] == "Pendiente"].to_dict("records")
    return render_template("cocina.html", pedidos=pedidos)

@app.route("/completar/<int:index>")
def completar(index):
    df = pd.read_excel(EXCEL_CONSUMOS)
    if index < len(df):
        df.at[index, "Estado"] = "Completado"
        df.to_excel(EXCEL_CONSUMOS, index=False)
    return redirect(url_for('cocina'))

# ================= FUNCIONES GENERALES =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)