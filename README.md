# Sistema de Gestión y Administración Hotel Del Rey

Software a la medida para gestionar las operaciones básicas de un hotel: habitaciones, huéspedes y usuarios del sistema. Es una aplicación de escritorio con interfaz gráfica hecha en Python (Tkinter).

**Autor:** Juan David Vidal Delgado
**Universidad de Cundinamarca** – Facultad de Ingeniería de Software
**Gestores del Conocimiento de Ingeniería de Software** – 2026

## Funcionalidades

- Inicio de sesión seguro (contraseñas con hash PBKDF2) y bloqueo tras 3 intentos fallidos.
- Creación de habitaciones (hasta 500 a la vez) con nivel de comodidad, tipo de cama y extras, con cálculo del precio por noche.
- Registro de huéspedes con asignación de habitación y total según las noches.
- Check-out con liberación automática de la habitación.
- Gestión de usuarios (administrador y empleado).

## Módulos

| Módulo | Qué hace |
|---|---|
| Acceso | Login, creación del administrador y usuarios |
| Habitaciones | Alta de habitaciones, precio y estado (libre/ocupada) |
| Huéspedes | Registro, total por noches y check-out |
| Datos | Guarda la información en `hotel_data.json` |

## Contenido del repositorio

La carpeta `PGC` incluye:

- `hotel_gui.py`: código fuente del sistema.
- `Poster_Hotel_Del_Rey_PGCFINAL.pdf`: póster del proyecto.
- `Sistema_de_Gestion_Hotel_Del_Rey_final (1).pdf`: informe del proyecto.

## Cómo ejecutarlo

Requiere Python 3.8 o superior. No necesita instalar librerías, solo usa la librería estándar.

```bash
cd PGC
python hotel_gui.py
```

La primera vez, el programa pide crear la cuenta de administrador. Los datos se guardan en el archivo `hotel_data.json`, que se crea solo.

## Trabajo futuro

- Registro de consumos (comidas, bebidas y otros).
- Generación de facturas.
