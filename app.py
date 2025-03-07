import os
import re
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from flask_mail import Mail, Message
import secrets
from flask_login import login_required


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Clave secreta para producción

# ================= Configuración del servidor de correo =================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maiqelmk@gmail.com'
app.config['MAIL_PASSWORD'] = 'yapj iunv knfq hfwq'
app.config['MAIL_DEFAULT_SENDER'] = ('Soporte Admin', 'TU_CORREO@gmail.com')

mail = Mail(app)


# ================= CONFIGURACIÓN DE ARCHIVOS =================
DATA_DIR = "data"
REPORTES_DIR = "reportes"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTES_DIR, exist_ok=True)

EXCEL_ADMINS = os.path.join(DATA_DIR, "administradores.xlsx")
EXCEL_CLIENTES = os.path.join(DATA_DIR, "clientes.xlsx")
EXCEL_CONSUMOS = os.path.join(DATA_DIR, "consumos.xlsx")
EXCEL_PRODUCTOS = os.path.join(DATA_DIR, "productos.xlsx")
INVENTARIO_EXCEL = os.path.join(DATA_DIR, "inventario.xlsx")


# Columnas para consumos
CONSUMOS_COLS = ["Cédula", "Producto", "Cantidad", "Precio", "Método_Pago", "Fecha_Hora", "Estado"]

# ================= INICIALIZACIÓN DE ARCHIVOS =================
def inicializar_archivos():

    if not os.path.exists(EXCEL_PRODUCTOS):
        pd.DataFrame(columns=["Nombre", "Precio", "Categoría", "Existencias"]).to_excel(EXCEL_PRODUCTOS, index=False)

    if not os.path.exists(INVENTARIO_EXCEL):
        pd.DataFrame(columns=["Producto", "Cantidad", "Costo_Unitario", "PVP", "Ganancia"]).to_excel(INVENTARIO_EXCEL, index=False)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(REPORTES_DIR):
        os.makedirs(REPORTES_DIR)
    
    # Administradores
    if not os.path.exists(EXCEL_ADMINS):
        # Creamos el Excel con las columnas Usuario, Correo y Clave
        pd.DataFrame(columns=["Usuario", "Correo", "Clave"]).to_excel(EXCEL_ADMINS, index=False)
    else:
        # Si ya existe, verificamos que tenga la columna Correo
        df_admins = pd.read_excel(EXCEL_ADMINS)
        cambios = False
        if "Correo" not in df_admins.columns:
            df_admins["Correo"] = ""
            cambios = True
        if "Token" not in df_admins.columns:
            df_admins["Token"] = ""
            cambios = True
        if "Token_Expira" not in df_admins.columns:
            df_admins["Token_Expira"] = ""
            cambios = True
        if cambios: 
            df_admins.to_excel(EXCEL_ADMINS, index=False)
    
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
        correo = request.form.get("correo")
        clave_plana = request.form.get("clave")

        # Validaciones básicas
        if not usuario or not correo or not clave_plana:
            return render_template("error.html", mensaje="Todos los campos son obligatorios")

        if "@" not in correo:
            return render_template("error.html", mensaje="Correo inválido")

        # Generar hash de la contraseña
        clave = generate_password_hash(clave_plana)

        # Crear nuevo registro
        nuevo_admin = pd.DataFrame([[usuario, correo, clave]], 
                                   columns=["Usuario", "Correo", "Clave"])
        df = pd.concat([df, nuevo_admin], ignore_index=True)
        df.to_excel(EXCEL_ADMINS, index=False)

        return redirect(url_for('login_admin'))

    return render_template("registro_admin.html")

@app.route("/admin/reset_password/<token>", methods=["GET", "POST"])
def reset_password_admin(token):
    df = pd.read_excel(EXCEL_ADMINS)
    # Buscar al admin con ese token
    admin = df[df["Token"] == token]

    if admin.empty:
        return render_template("error.html", mensaje="Token inválido o ya utilizado.")

    # Verificar expiración
    token_expira_str = admin.iloc[0]["Token_Expira"]
    token_expira = datetime.strptime(token_expira_str, "%Y-%m-%d %H:%M:%S")
    if datetime.now() > token_expira:
        return render_template("error.html", mensaje="El enlace de recuperación ha expirado.")

    if request.method == "POST":
        nueva_clave = request.form.get("nueva_clave")
        confirma_clave = request.form.get("confirma_clave")

        if not nueva_clave or not confirma_clave:
            return render_template("reset_password_admin.html", 
                                   error="Debe llenar ambos campos.", token=token)

        if nueva_clave != confirma_clave:
            return render_template("reset_password_admin.html", 
                                   error="Las contraseñas no coinciden.", token=token)

        # Actualizar la contraseña en Excel
        index_admin = admin.index[0]
        df.at[index_admin, "Clave"] = generate_password_hash(nueva_clave)
        # Limpiar el token para que no se pueda reutilizar
        df.at[index_admin, "Token"] = ""
        df.at[index_admin, "Token_Expira"] = ""
        df.to_excel(EXCEL_ADMINS, index=False)

        return render_template("reset_password_admin.html", 
                               mensaje="Tu contraseña ha sido restablecida. ¡Puedes iniciar sesión!")

    return render_template("reset_password_admin.html", token=token)



@app.route('/admin/panel')
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
            existencias = int(request.form.get('existencias'))
            categoria = request.form.get('categoria')
            
            if indice and indice != 'None':
                indice = int(indice)
                df.at[indice, 'Nombre'] = producto
                df.at[indice, 'Precio'] = precio
                df.at[indice, 'Existencias'] = existencias
                df.at[indice, 'Categoría'] = categoria
            else:
                nuevo = pd.DataFrame([[producto, precio, categoria, existencias]], 
                                   columns=["Nombre", "Precio", "Categoría", "Existencias"])
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
            # Obtener la fecha del formulario
            fecha = request.form.get("fecha")
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")  # Convertir a objeto datetime
            fecha_str = fecha_obj.strftime("%d/%m/%Y")  # Formatear como dd/mm/yyyy
            
            # Leer archivos Excel
            df_clientes = pd.read_excel(EXCEL_CLIENTES)
            df_consumos = pd.read_excel(EXCEL_CONSUMOS)
            
            # Filtrar consumos por fecha
            consumos_filtrados = df_consumos[
                df_consumos["Fecha_Hora"].str.contains(fecha_str)
            ]
            
            # Crear el archivo de reporte
            reporte_path = os.path.join(REPORTES_DIR, f"reporte_{fecha_str.replace('/', '-')}.xlsx")
            with pd.ExcelWriter(reporte_path, engine='openpyxl') as writer:
                df_clientes.to_excel(writer, sheet_name='Clientes', index=False)
                consumos_filtrados.to_excel(writer, sheet_name='Consumos', index=False)
            
            # Enviar el archivo como descarga
            return send_file(reporte_path, as_attachment=True)
        
        except Exception as e:
            return render_template("error.html", mensaje=f"Error al generar el reporte: {str(e)}")
    
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
    try:
        # Leer archivos Excel
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        
        # Inicializar listas vacías
        clientes_abiertos = []
        clientes_cerrados = []
        
        if request.method == "POST":
            cedula = request.form.get("cedula")
            nombre = request.form.get("nombre")
            
            # Validaciones
            if not cedula.isdigit() or len(cedula) != 10:
                return render_template("error.html", mensaje="Cédula inválida: debe tener 10 dígitos")
                
            if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
                return render_template("error.html", mensaje="Nombre inválido: solo letras y espacios")
                
            if cedula in df_clientes["Cédula"].astype(str).values:
                return render_template("error.html", mensaje="La cédula ya está registrada")
                
            # Registrar nuevo cliente
            nuevo_cliente = pd.DataFrame([[cedula, nombre]], columns=["Cédula", "Nombre"])
            df_clientes = pd.concat([df_clientes, nuevo_cliente], ignore_index=True)
            df_clientes.to_excel(EXCEL_CLIENTES, index=False)
            
            # Recargar datos actualizados
            df_clientes = pd.read_excel(EXCEL_CLIENTES)

        # Clasificar clientes
        for _, cliente in df_clientes.iterrows():
            cedula = str(cliente["Cédula"])
            consumos_pendientes = df_consumos[
                (df_consumos["Cédula"] == cedula) & 
                (df_consumos["Estado"] == "Pendiente")
            ]
            
            if not consumos_pendientes.empty:
                clientes_abiertos.append(cliente.to_dict())
            else:
                clientes_cerrados.append(cliente.to_dict())
        
        return render_template("clientes.html", 
                            clientes_abiertos=clientes_abiertos,
                            clientes_cerrados=clientes_cerrados)
                            
    except Exception as e:
        return render_template("error.html", mensaje=f"Error crítico: {str(e)}")

@app.route("/ver_consumos/<cedula>")
@login_caja_required
def ver_consumos_cliente(cedula):
    try:
        df_clientes = pd.read_excel(EXCEL_CLIENTES)
        cliente = df_clientes[df_clientes["Cédula"].astype(str) == cedula].iloc[0].to_dict()
        
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        consumos = df_consumos[df_consumos["Cédula"].astype(str) == cedula].to_dict("records")
        
        return render_template("consumos_cliente.html",
                             cliente=cliente,
                             consumos=consumos)
    except Exception as e:
        return render_template("error.html", mensaje=f"Error al obtener datos: {str(e)}")

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
    
    # Filtrar consumos del día actual y pendientes
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    df_consumos = pd.read_excel(EXCEL_CONSUMOS)
    df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
    consumos_cliente = df_consumos[
        (df_consumos["Cédula"] == cedula) & 
        (df_consumos["Fecha_Hora"].str.contains(fecha_actual)) & 
        (df_consumos["Estado"] == "Pendiente")
    ]
    
    # Calcular total solo para los consumos pendientes del día actual
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
        cliente = df_clientes[df_clientes["Cédula"] == cedula].iloc[0].to_dict()

        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)

        # Filtrar consumos pendientes del cliente
        consumos_cliente = df_consumos[(df_consumos["Cédula"] == cedula) & (df_consumos["Estado"] == "Pendiente")]

        if consumos_cliente.empty:
            return render_template("error.html", mensaje="El cliente no tiene consumos pendientes.")

        # Calcular total de la cuenta
        total = sum(consumos_cliente["Cantidad"] * consumos_cliente["Precio"])

        return render_template("cierre_cuenta.html",
                               cliente=cliente,
                               consumos=consumos_cliente.to_dict("records"),
                               total=total)
    except Exception as e:
        return render_template("error.html", mensaje=f"Error al cerrar la cuenta: {str(e)}")

@app.route("/marcar_pagado/<cedula>", methods=["POST"])
@login_caja_required
def marcar_pagado(cedula):
    try:
        metodo_pago = request.form.get("metodo_pago")
        monto_recibido = request.form.get("monto_recibido")
        referencia = request.form.get("referencia")

        # Leer archivo de consumos
        df_consumos = pd.read_excel(EXCEL_CONSUMOS)
        df_consumos["Cédula"] = df_consumos["Cédula"].astype(str)
        
        # Filtrar consumos pendientes del cliente
        mask = (df_consumos["Cédula"] == cedula) & (df_consumos["Estado"] == "Pendiente")
        
        # Actualizar consumos
        df_consumos.loc[mask, "Estado"] = "CANCELADO"
        df_consumos.loc[mask, "Método_Pago"] = metodo_pago
        
        # Guardar datos adicionales según el método de pago
        if metodo_pago == "Efectivo":
            df_consumos.loc[mask, "Monto_Recibido"] = float(monto_recibido)
            df_consumos.loc[mask, "Cambio"] = float(monto_recibido) - sum(
                df_consumos.loc[mask, "Cantidad"] * df_consumos.loc[mask, "Precio"]
            )
        elif metodo_pago == "Transferencia":
            df_consumos.loc[mask, "Referencia"] = referencia
        
        # Guardar cambios (agregar engine='openpyxl' si es necesario)
        df_consumos.to_excel(EXCEL_CONSUMOS, index=False, engine='openpyxl')  # <-- Asegurar guardado
        
        return redirect(url_for('clientes'))
    
    except Exception as e:
        return render_template("error.html", mensaje=f"Error: {str(e)}")
    
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

@app.route("/admin/inventario", methods=["GET", "POST"])
@login_admin_required
def admin_inventario():
    # Leer el archivo de inventario y restablecer el índice
    df_inv = pd.read_excel(INVENTARIO_EXCEL)
    df_inv.reset_index(inplace=True)
    df_inv.rename(columns={"index": "IndiceReal"}, inplace=True)
    inventario = df_inv.to_dict("records")

    df_prod = pd.read_excel(EXCEL_PRODUCTOS)

    if request.method == "POST":
        try:
            # Acción: Crear nuevo producto
            if 'guardar' in request.form:
                producto = request.form.get("producto")
                cantidad = int(request.form.get("cantidad"))
                costo_unitario = float(request.form.get("costo_unitario"))
                pvp = float(request.form.get("pvp"))
                ganancia = round(pvp - costo_unitario, 2)

                nuevo_inv = pd.DataFrame([{
                    "Producto": producto,
                    "Cantidad": cantidad,
                    "Costo_Unitario": costo_unitario,
                    "PVP": pvp,
                    "Ganancia": ganancia
                }])
                
                # Guardar en inventario
                df_inv = pd.concat([df_inv, nuevo_inv], ignore_index=True)
                df_inv.to_excel(INVENTARIO_EXCEL, index=False)

                # Actualizar productos
                if producto in df_prod["Nombre"].values:
                    df_prod.loc[df_prod["Nombre"] == producto, "Existencias"] += cantidad
                else:
                    nuevo_prod = pd.DataFrame([{
                        "Nombre": producto,
                        "Precio": pvp,
                        "Categoría": "Bebidas" if "gaseosa" in producto.lower() else "General",
                        "Existencias": cantidad
                    }])
                    df_prod = pd.concat([df_prod, nuevo_prod], ignore_index=True)
                df_prod.to_excel(EXCEL_PRODUCTOS, index=False)

                return redirect(url_for('admin_inventario'))

            # Acción: Eliminar producto
            elif 'eliminar' in request.form:
                indice = int(request.form.get("indice"))
                
                # Leer el archivo actualizado para evitar índices obsoletos
                df_inv_actual = pd.read_excel(INVENTARIO_EXCEL)
                df_inv_actual = df_inv_actual.drop(index=indice)
                df_inv_actual.to_excel(INVENTARIO_EXCEL, index=False)
                return redirect(url_for('admin_inventario'))

            # Acción: Editar producto
            elif 'editar' in request.form:
                indice = int(request.form.get("indice"))
                producto = request.form.get("producto")
                cantidad = int(request.form.get("cantidad"))
                costo_unitario = float(request.form.get("costo_unitario"))
                pvp = float(request.form.get("pvp"))
                ganancia = round(pvp - costo_unitario, 2)

                # Leer el archivo actualizado
                df_inv_actual = pd.read_excel(INVENTARIO_EXCEL)
                
                # Actualizar valores en el inventario
                df_inv_actual.at[indice, "Cantidad"] = cantidad
                df_inv_actual.at[indice, "Costo_Unitario"] = costo_unitario
                df_inv_actual.at[indice, "PVP"] = pvp
                df_inv_actual.at[indice, "Ganancia"] = ganancia
                df_inv_actual.to_excel(INVENTARIO_EXCEL, index=False)

                # Actualizar productos
                df_prod_actual = pd.read_excel(EXCEL_PRODUCTOS)
                if producto in df_prod_actual["Nombre"].values:
                    df_prod_actual.loc[df_prod_actual["Nombre"] == producto, "Precio"] = pvp
                    df_prod_actual.loc[df_prod_actual["Nombre"] == producto, "Existencias"] = cantidad
                    df_prod_actual.to_excel(EXCEL_PRODUCTOS, index=False)
                else:
                    return render_template("error.html", mensaje="Producto no encontrado en la lista de productos.")

                return redirect(url_for('admin_inventario'))

        except Exception as e:
            return render_template("error.html", mensaje=f"Error: {str(e)}")

    return render_template(
        "admin_inventario.html", 
        inventario=inventario,
        enumerate=enumerate
    )


@app.route("/bar/registrar_consumo", methods=["POST"])
@login_required
def registrar_consumo():
    producto = request.form.get("producto")
    cantidad = int(request.form.get("cantidad"))

    df_prod = pd.read_excel(EXCEL_PRODUCTOS)

    # Verificar si hay suficiente stock
    if producto in df_prod["Nombre"].values:
        existencias_actuales = df_prod.loc[df_prod["Nombre"] == producto, "Existencias"].values[0]
        if existencias_actuales >= cantidad:
            df_prod.loc[df_prod["Nombre"] == producto, "Existencias"] -= cantidad
            df_prod.to_excel(EXCEL_PRODUCTOS, index=False)
            flash("Consumo registrado correctamente.", "success")
        else:
            flash("No hay suficiente stock para este producto.", "danger")
    else:
        flash("El producto no existe en el sistema.", "danger")

    return redirect(url_for("bar"))




@app.route("/admin/recuperar_password", methods=["GET", "POST"])
def recuperar_password_admin():
    if request.method == "POST":
        email = request.form.get("email")
        
        df = pd.read_excel(EXCEL_ADMINS)
        # Buscar admin por correo
        admin = df[df["Correo"] == email]

        if admin.empty:
            return render_template("recuperar_password_admin.html", 
                                   error="No se encontró un administrador con ese correo.")

        # Generar token aleatorio
        token = secrets.token_urlsafe(32)

        # Definir fecha/hora de expiración (ej. 30 minutos)
        expira = datetime.now() + timedelta(minutes=30)
        expira_str = expira.strftime("%Y-%m-%d %H:%M:%S")

        # Actualizar el registro en Excel
        index_admin = admin.index[0]
        df.at[index_admin, "Token"] = token
        df.at[index_admin, "Token_Expira"] = expira_str
        df.to_excel(EXCEL_ADMINS, index=False)

        # Enviar correo con Flask-Mail
        reset_url = url_for('reset_password_admin', token=token, _external=True)
        msg = Message("Complejo Recreacional Maria Victoria - Recuperación de Contraseña",
                      recipients=[email])
        msg.body = f"""Hola,

Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace (o pégalo en tu navegador) para continuar:

{reset_url}

Este enlace expirará en 30 minutos.

Si no solicitaste restablecer tu contraseña, ignora este correo.
"""
        mail.send(msg)

        return render_template("recuperar_password_admin.html", 
                               mensaje="Se envió un enlace de recuperación a tu correo.")
    
    return render_template("recuperar_password_admin.html")


# ================= FUNCIONES GENERALES =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == "__main__":
    app.run(debug=False)