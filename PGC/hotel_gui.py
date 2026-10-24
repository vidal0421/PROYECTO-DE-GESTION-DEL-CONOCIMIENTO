#!/usr/bin/env python3
"""
Sistema de gestión de hotel (versión gráfica, Tkinter)
- Login con usuario y contraseña (hash PBKDF2, igual que la versión de consola)
- Crear N habitaciones con ajuste de comodidad
- Registrar huéspedes y asignarlos a una habitación al instante
- Check-out y administración de usuarios
- Usa el mismo archivo hotel_data.json que hotel.py, así que los datos son compatibles

Solo usa la librería estándar de Python 3.8+. Ejecutar:  python hotel_gui.pyh
"""

import hashlib
import json
import os
import secrets
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

DATA_FILE = "hotel_data.json"

NIVELES = {
    "1": {"nombre": "Básica", "precio": 80_000},
    "2": {"nombre": "Estándar", "precio": 150_000},
    "3": {"nombre": "Premium", "precio": 250_000},
}
CAMAS = {"1": "Sencilla", "2": "Doble", "3": "Queen", "4": "King"}
EXTRAS = {
    "1": {"nombre": "Aire acondicionado", "precio": 30_000},
    "2": {"nombre": "TV", "precio": 10_000},
    "3": {"nombre": "WiFi", "precio": 5_000},
    "4": {"nombre": "Minibar", "precio": 20_000},
    "5": {"nombre": "Jacuzzi", "precio": 50_000},
}


# ----------------------------- Utilidades -----------------------------------
def moneda(valor):
    return f"${valor:,.0f}".replace(",", ".")


def centrar(win, parent=None):
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    if parent is not None:
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    else:
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


# ----------------------------- Persistencia ---------------------------------
def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"usuarios": {}, "habitaciones": [], "huespedes": []}


def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def hashear(password, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 200_000
    ).hex()
    return salt, h


def precio_habitacion(nivel, extras):
    return NIVELES[nivel]["precio"] + sum(EXTRAS[e]["precio"] for e in extras)


# ----------------------------- Diálogos -------------------------------------
class Dialogo(tk.Toplevel):
    """Base para diálogos modales."""

    def __init__(self, parent, titulo):
        super().__init__(parent)
        self.title(titulo)
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        self.cuerpo = ttk.Frame(self, padding=14)
        self.cuerpo.pack(fill="both", expand=True)
        self.parent = parent

    def botones(self, texto_ok="Aceptar"):
        fila = ttk.Frame(self.cuerpo)
        fila.grid(row=99, column=0, columnspan=2, pady=(14, 0), sticky="e")
        ttk.Button(fila, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(fila, text=texto_ok, command=self.aceptar).pack(
            side="right", padx=(0, 8)
        )
        self.bind("<Return>", lambda e: self.aceptar())
        self.bind("<Escape>", lambda e: self.destroy())

    def mostrar(self):
        centrar(self, self.parent)
        self.grab_set()
        self.wait_window(self)
        return self.result

    def aceptar(self):
        raise NotImplementedError


class DialogoComodidad(Dialogo):
    def __init__(self, parent, titulo="Comodidad de la habitación"):
        super().__init__(parent, titulo)
        c = self.cuerpo

        ttk.Label(c, text="Nivel de comodidad:").grid(row=0, column=0, sticky="w", pady=4)
        self.nivel = ttk.Combobox(
            c,
            state="readonly",
            width=34,
            values=[
                f"{n['nombre']} (base {moneda(n['precio'])}/noche)"
                for n in NIVELES.values()
            ],
        )
        self.nivel.current(0)
        self.nivel.grid(row=0, column=1, pady=4, padx=(8, 0))

        ttk.Label(c, text="Tipo de cama:").grid(row=1, column=0, sticky="w", pady=4)
        self.cama = ttk.Combobox(
            c, state="readonly", width=34, values=list(CAMAS.values())
        )
        self.cama.current(0)
        self.cama.grid(row=1, column=1, pady=4, padx=(8, 0))

        marco = ttk.LabelFrame(c, text="Extras (opcional)", padding=8)
        marco.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        self.vars_extras = {}
        for k, e in EXTRAS.items():
            v = tk.BooleanVar(value=False)
            self.vars_extras[k] = v
            ttk.Checkbutton(
                marco,
                text=f"{e['nombre']} (+{moneda(e['precio'])})",
                variable=v,
                command=self.actualizar_precio,
            ).pack(anchor="w")

        self.lbl_precio = ttk.Label(c, font=("TkDefaultFont", 11, "bold"))
        self.lbl_precio.grid(row=3, column=0, columnspan=2, sticky="w")
        self.nivel.bind("<<ComboboxSelected>>", lambda e: self.actualizar_precio())
        self.actualizar_precio()
        self.botones()

    def seleccion(self):
        nivel = list(NIVELES)[self.nivel.current()]
        cama = list(CAMAS)[self.cama.current()]
        extras = [k for k, v in self.vars_extras.items() if v.get()]
        return {"nivel": nivel, "cama": cama, "extras": extras}

    def actualizar_precio(self):
        s = self.seleccion()
        self.lbl_precio.config(
            text=f"Precio por noche: {moneda(precio_habitacion(s['nivel'], s['extras']))}"
        )

    def aceptar(self):
        self.result = self.seleccion()
        self.destroy()


class DialogoCrearHabitaciones(Dialogo):
    def __init__(self, parent):
        super().__init__(parent, "Crear habitaciones")
        c = self.cuerpo
        ttk.Label(c, text="¿Cuántas habitaciones?").grid(row=0, column=0, sticky="w", pady=4)
        self.cantidad = tk.IntVar(value=1)
        ttk.Spinbox(c, from_=1, to=500, textvariable=self.cantidad, width=8).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self.igual = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            c,
            text="Misma comodidad para todas",
            variable=self.igual,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Label(
            c,
            text="Si la desmarcas, configurarás cada habitación una por una.",
            foreground="#666",
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        self.botones("Continuar")

    def aceptar(self):
        try:
            n = int(self.cantidad.get())
        except (tk.TclError, ValueError):
            messagebox.showwarning("Dato inválido", "Escribe un número entero.", parent=self)
            return
        if not 1 <= n <= 500:
            messagebox.showwarning("Dato inválido", "Debe ser entre 1 y 500.", parent=self)
            return
        self.result = {"cantidad": n, "igual": self.igual.get()}
        self.destroy()


class DialogoHuesped(Dialogo):
    def __init__(self, parent, libres):
        super().__init__(parent, "Registrar huésped")
        self.libres = libres
        c = self.cuerpo

        self.nombre = tk.StringVar()
        self.documento = tk.StringVar()
        self.telefono = tk.StringVar()
        self.noches = tk.IntVar(value=1)

        for i, (txt, var) in enumerate(
            [
                ("Nombre completo:", self.nombre),
                ("Documento de identidad:", self.documento),
                ("Teléfono:", self.telefono),
            ]
        ):
            ttk.Label(c, text=txt).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(c, textvariable=var, width=36).grid(row=i, column=1, padx=(8, 0))

        ttk.Label(c, text="Habitación:").grid(row=3, column=0, sticky="w", pady=4)
        self.hab = ttk.Combobox(
            c,
            state="readonly",
            width=34,
            values=[
                f"#{h['numero']} - {h['nivel']}, cama {h['cama']} ({moneda(h['precio'])})"
                for h in libres
            ],
        )
        self.hab.current(0)
        self.hab.grid(row=3, column=1, padx=(8, 0))

        ttk.Label(c, text="Número de noches:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Spinbox(
            c, from_=1, to=365, textvariable=self.noches, width=8,
            command=self.actualizar_total,
        ).grid(row=4, column=1, sticky="w", padx=(8, 0))

        self.lbl_total = ttk.Label(c, font=("TkDefaultFont", 11, "bold"))
        self.lbl_total.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.hab.bind("<<ComboboxSelected>>", lambda e: self.actualizar_total())
        self.noches.trace_add("write", lambda *a: self.actualizar_total())
        self.actualizar_total()
        self.botones("Registrar")

    def noches_validas(self):
        try:
            n = int(self.noches.get())
        except (tk.TclError, ValueError):
            return None
        return n if 1 <= n <= 365 else None

    def actualizar_total(self):
        n = self.noches_validas()
        if n is None:
            self.lbl_total.config(text="Total: —")
            return
        precio = self.libres[self.hab.current()]["precio"]
        self.lbl_total.config(text=f"Total: {moneda(precio * n)}")

    def aceptar(self):
        nombre = self.nombre.get().strip()
        doc = self.documento.get().strip()
        tel = self.telefono.get().strip()
        if not (nombre and doc and tel):
            messagebox.showwarning("Faltan datos", "Completa todos los campos.", parent=self)
            return
        n = self.noches_validas()
        if n is None:
            messagebox.showwarning("Dato inválido", "Noches: entre 1 y 365.", parent=self)
            return
        self.result = {
            "nombre": nombre,
            "documento": doc,
            "telefono": tel,
            "habitacion": self.libres[self.hab.current()]["numero"],
            "noches": n,
        }
        self.destroy()


class DialogoUsuario(Dialogo):
    def __init__(self, parent, existentes):
        super().__init__(parent, "Crear usuario")
        self.existentes = existentes
        c = self.cuerpo
        self.usuario = tk.StringVar()
        self.pw1 = tk.StringVar()
        self.pw2 = tk.StringVar()
        campos = [
            ("Nuevo usuario:", self.usuario, ""),
            ("Contraseña (mín. 6):", self.pw1, "•"),
            ("Repite la contraseña:", self.pw2, "•"),
        ]
        for i, (txt, var, show) in enumerate(campos):
            ttk.Label(c, text=txt).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(c, textvariable=var, show=show, width=28).grid(
                row=i, column=1, padx=(8, 0)
            )
        self.botones("Crear")

    def aceptar(self):
        u = self.usuario.get().strip().lower()
        if not u:
            messagebox.showwarning("Faltan datos", "Escribe un usuario.", parent=self)
        elif u in self.existentes:
            messagebox.showwarning("Usuario", "Ese usuario ya existe.", parent=self)
        elif len(self.pw1.get()) < 6:
            messagebox.showwarning("Contraseña", "Muy corta (mínimo 6).", parent=self)
        elif self.pw1.get() != self.pw2.get():
            messagebox.showwarning("Contraseña", "Las contraseñas no coinciden.", parent=self)
        else:
            self.result = {"usuario": u, "password": self.pw1.get()}
            self.destroy()


# ----------------------------- Aplicación -----------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Hotel")
        self.datos = cargar_datos()
        self.usuario = None
        self.intentos = 0
        style = ttk.Style(self)
        if "clam" in style.theme_names() and os.name != "nt":
            style.theme_use("clam")
        style.configure("Titulo.TLabel", font=("TkDefaultFont", 16, "bold"))
        style.configure("Treeview", rowheight=24)
        self.mostrar_login()

    def limpiar(self):
        for w in self.winfo_children():
            w.destroy()

    # ---------------- Login ----------------
    def mostrar_login(self):
        self.limpiar()
        self.unbind("<Return>")
        self.minsize(0, 0)
        self.geometry("")
        primera_vez = not self.datos["usuarios"]

        f = ttk.Frame(self, padding=24)
        f.pack()
        ttk.Label(f, text="🏨 Sistema de Hotel", style="Titulo.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 6)
        )
        sub = (
            "Primera vez: crea la cuenta de administrador"
            if primera_vez
            else "Inicia sesión"
        )
        ttk.Label(f, text=sub, foreground="#666").grid(row=1, column=0, columnspan=2, pady=(0, 14))

        self.v_user = tk.StringVar()
        self.v_pw = tk.StringVar()
        self.v_pw2 = tk.StringVar()

        ttk.Label(f, text="Usuario:").grid(row=2, column=0, sticky="w", pady=4)
        e_user = ttk.Entry(f, textvariable=self.v_user, width=26)
        e_user.grid(row=2, column=1, padx=(8, 0))
        ttk.Label(f, text="Contraseña:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self.v_pw, show="•", width=26).grid(
            row=3, column=1, padx=(8, 0)
        )
        if primera_vez:
            ttk.Label(f, text="Repite:").grid(row=4, column=0, sticky="w", pady=4)
            ttk.Entry(f, textvariable=self.v_pw2, show="•", width=26).grid(
                row=4, column=1, padx=(8, 0)
            )

        accion = self.crear_admin if primera_vez else self.hacer_login
        ttk.Button(
            f, text="Crear administrador" if primera_vez else "Entrar", command=accion
        ).grid(row=5, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        self.bind("<Return>", lambda e: accion())
        e_user.focus()
        centrar(self)

    def crear_admin(self):
        u = self.v_user.get().strip().lower()
        pw = self.v_pw.get()
        if not u:
            messagebox.showwarning("Usuario", "Escribe un usuario.")
        elif len(pw) < 6:
            messagebox.showwarning("Contraseña", "Muy corta (mínimo 6).")
        elif pw != self.v_pw2.get():
            messagebox.showwarning("Contraseña", "Las contraseñas no coinciden.")
        else:
            salt, h = hashear(pw)
            self.datos["usuarios"][u] = {"salt": salt, "hash": h, "admin": True}
            guardar_datos(self.datos)
            messagebox.showinfo("Listo", f"Administrador '{u}' creado. Ahora inicia sesión.")
            self.mostrar_login()

    def hacer_login(self):
        u = self.v_user.get().strip().lower()
        pw = self.v_pw.get()
        info = self.datos["usuarios"].get(u)
        if info:
            _, h = hashear(pw, info["salt"])
            if secrets.compare_digest(h, info["hash"]):
                self.usuario = u
                self.intentos = 0
                self.mostrar_principal()
                return
        self.intentos += 1
        if self.intentos >= 3:
            messagebox.showerror("Acceso denegado", "Demasiados intentos fallidos. Saliendo.")
            self.destroy()
            return
        messagebox.showerror(
            "Error", f"Usuario o contraseña incorrectos ({self.intentos}/3)."
        )
        self.v_pw.set("")

    # ---------------- Pantalla principal ----------------
    def mostrar_principal(self):
        self.limpiar()
        self.unbind("<Return>")
        es_admin = self.datos["usuarios"][self.usuario].get("admin", False)
        self.minsize(900, 500)
        self.geometry("1000x560")

        top = ttk.Frame(self, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="🏨 Sistema de Hotel", style="Titulo.TLabel").pack(side="left")
        ttk.Button(top, text="Cerrar sesión", command=self.cerrar_sesion).pack(side="right")
        ttk.Label(top, text=f"Usuario: {self.usuario}").pack(side="right", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tab_hab = ttk.Frame(self.nb, padding=8)
        self.tab_hue = ttk.Frame(self.nb, padding=8)
        self.nb.add(self.tab_hab, text="Habitaciones")
        self.nb.add(self.tab_hue, text="Huéspedes")
        self.construir_tab_habitaciones()
        self.construir_tab_huespedes()

        if es_admin:
            self.tab_usr = ttk.Frame(self.nb, padding=8)
            self.nb.add(self.tab_usr, text="Usuarios")
            self.construir_tab_usuarios()

        self.refrescar_todo()
        centrar(self)

    def cerrar_sesion(self):
        self.usuario = None
        self.mostrar_login()

    def refrescar_todo(self):
        self.refrescar_habitaciones()
        self.refrescar_huespedes()
        if hasattr(self, "tab_usr") and self.tab_usr.winfo_exists():
            self.refrescar_usuarios()

    def crear_tabla(self, parent, columnas):
        """columnas: lista de (id, título, ancho, anchor)."""
        marco = ttk.Frame(parent)
        marco.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            marco, columns=[c[0] for c in columnas], show="headings", selectmode="browse"
        )
        for cid, titulo, ancho, anchor in columnas:
            tree.heading(cid, text=titulo)
            tree.column(cid, width=ancho, anchor=anchor)
        sb = ttk.Scrollbar(marco, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    # ---------------- Habitaciones ----------------
    def construir_tab_habitaciones(self):
        barra = ttk.Frame(self.tab_hab)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="➕ Crear habitaciones", command=self.crear_habitaciones).pack(side="left")
        self.lbl_resumen = ttk.Label(barra, foreground="#555")
        self.lbl_resumen.pack(side="right")
        self.tree_hab = self.crear_tabla(
            self.tab_hab,
            [
                ("num", "Nº", 60, "center"),
                ("nivel", "Nivel", 100, "w"),
                ("cama", "Cama", 90, "w"),
                ("precio", "Precio/noche", 120, "e"),
                ("extras", "Extras", 300, "w"),
                ("estado", "Estado", 90, "center"),
            ],
        )
        self.tree_hab.tag_configure("ocupada", background="#fde2e2")
        self.tree_hab.tag_configure("libre", background="#e3f6e3")

    def refrescar_habitaciones(self):
        t = self.tree_hab
        t.delete(*t.get_children())
        libres = 0
        for h in self.datos["habitaciones"]:
            ocupada = bool(h["ocupada_por"])
            libres += 0 if ocupada else 1
            t.insert(
                "",
                "end",
                values=(
                    h["numero"],
                    h["nivel"],
                    h["cama"],
                    moneda(h["precio"]),
                    ", ".join(h["extras"]) if h["extras"] else "sin extras",
                    "OCUPADA" if ocupada else "Libre",
                ),
                tags=("ocupada" if ocupada else "libre",),
            )
        total = len(self.datos["habitaciones"])
        self.lbl_resumen.config(
            text=f"Total: {total}  |  Libres: {libres}  |  Ocupadas: {total - libres}"
        )

    def crear_habitaciones(self):
        info = DialogoCrearHabitaciones(self).mostrar()
        if not info:
            return
        cantidad, igual = info["cantidad"], info["igual"]
        siguiente = max((h["numero"] for h in self.datos["habitaciones"]), default=100) + 1

        comun = None
        if igual:
            comun = DialogoComodidad(self, "Comodidad para todas").mostrar()
            if not comun:
                return

        nuevas = []
        for i in range(cantidad):
            numero = siguiente + i
            cfg = comun
            if not igual:
                cfg = DialogoComodidad(
                    self, f"Habitación {numero} ({i + 1}/{cantidad})"
                ).mostrar()
                if not cfg:
                    messagebox.showinfo("Cancelado", "No se creó ninguna habitación.")
                    return
            nuevas.append(
                {
                    "numero": numero,
                    "nivel": NIVELES[cfg["nivel"]]["nombre"],
                    "cama": CAMAS[cfg["cama"]],
                    "extras": [EXTRAS[e]["nombre"] for e in cfg["extras"]],
                    "precio": precio_habitacion(cfg["nivel"], cfg["extras"]),
                    "ocupada_por": None,
                }
            )
        self.datos["habitaciones"].extend(nuevas)
        guardar_datos(self.datos)
        self.refrescar_todo()
        messagebox.showinfo("Listo", f"Se crearon {cantidad} habitación(es).")

    # ---------------- Huéspedes ----------------
    def construir_tab_huespedes(self):
        barra = ttk.Frame(self.tab_hue)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="➕ Registrar huésped", command=self.registrar_huesped).pack(side="left")
        ttk.Button(barra, text="🚪 Check-out", command=self.check_out).pack(side="left", padx=8)
        self.solo_activos = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            barra,
            text="Solo hospedados",
            variable=self.solo_activos,
            command=self.refrescar_huespedes,
        ).pack(side="right")
        self.tree_hue = self.crear_tabla(
            self.tab_hue,
            [
                ("nombre", "Nombre", 180, "w"),
                ("doc", "Documento", 110, "w"),
                ("tel", "Teléfono", 110, "w"),
                ("hab", "Hab.", 60, "center"),
                ("noches", "Noches", 70, "center"),
                ("total", "Total", 110, "e"),
                ("ingreso", "Ingreso", 130, "center"),
                ("estado", "Estado", 90, "center"),
            ],
        )
        self.tree_hue.tag_configure("hospedado", background="#e3f6e3")

    def refrescar_huespedes(self):
        t = self.tree_hue
        t.delete(*t.get_children())
        for i, g in enumerate(self.datos["huespedes"]):
            if self.solo_activos.get() and g["estado"] != "hospedado":
                continue
            t.insert(
                "",
                "end",
                iid=str(i),  # índice en la lista de datos
                values=(
                    g["nombre"],
                    g["documento"],
                    g["telefono"],
                    g["habitacion"],
                    g["noches"],
                    moneda(g["total"]),
                    g.get("ingreso", ""),
                    g["estado"],
                ),
                tags=("hospedado",) if g["estado"] == "hospedado" else (),
            )

    def registrar_huesped(self):
        libres = [h for h in self.datos["habitaciones"] if not h["ocupada_por"]]
        if not libres:
            messagebox.showwarning(
                "Sin habitaciones", "No hay habitaciones libres. Crea más o haz check-out."
            )
            return
        r = DialogoHuesped(self, libres).mostrar()
        if not r:
            return
        if any(
            g["documento"] == r["documento"] and g["estado"] == "hospedado"
            for g in self.datos["huespedes"]
        ):
            messagebox.showwarning("Duplicado", "Esa persona ya está hospedada.")
            return
        habitacion = next(h for h in libres if h["numero"] == r["habitacion"])
        total = habitacion["precio"] * r["noches"]
        self.datos["huespedes"].append(
            {
                **r,
                "total": total,
                "ingreso": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "estado": "hospedado",
            }
        )
        habitacion["ocupada_por"] = r["documento"]
        guardar_datos(self.datos)
        self.refrescar_todo()
        messagebox.showinfo(
            "Registrado",
            f"{r['nombre']} quedó en la habitación {r['habitacion']}.\nTotal: {moneda(total)}",
        )

    def check_out(self):
        sel = self.tree_hue.selection()
        if not sel:
            messagebox.showinfo("Check-out", "Selecciona un huésped de la lista.")
            return
        g = self.datos["huespedes"][int(sel[0])]
        if g["estado"] != "hospedado":
            messagebox.showinfo("Check-out", "Ese huésped ya salió.")
            return
        if not messagebox.askyesno(
            "Check-out",
            f"¿Hacer check-out de {g['nombre']} (hab. #{g['habitacion']})?\n"
            f"Total a cobrar: {moneda(g['total'])}",
        ):
            return
        g["estado"] = "salió"
        for h in self.datos["habitaciones"]:
            if h["numero"] == g["habitacion"]:
                h["ocupada_por"] = None
        guardar_datos(self.datos)
        self.refrescar_todo()

    # ---------------- Usuarios (admin) ----------------
    def construir_tab_usuarios(self):
        barra = ttk.Frame(self.tab_usr)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="➕ Crear usuario", command=self.crear_usuario).pack(side="left")
        self.tree_usr = self.crear_tabla(
            self.tab_usr,
            [("usuario", "Usuario", 200, "w"), ("rol", "Rol", 120, "center")],
        )

    def refrescar_usuarios(self):
        t = self.tree_usr
        t.delete(*t.get_children())
        for u, info in sorted(self.datos["usuarios"].items()):
            t.insert("", "end", values=(u, "Administrador" if info.get("admin") else "Empleado"))

    def crear_usuario(self):
        r = DialogoUsuario(self, self.datos["usuarios"]).mostrar()
        if not r:
            return
        salt, h = hashear(r["password"])
        self.datos["usuarios"][r["usuario"]] = {"salt": salt, "hash": h, "admin": False}
        guardar_datos(self.datos)
        self.refrescar_usuarios()
        messagebox.showinfo("Listo", f"Usuario '{r['usuario']}' creado.")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
