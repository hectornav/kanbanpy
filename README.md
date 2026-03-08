# 📋 Kanbanpy Pro v2.0

**Kanbanpy Pro** es una aplicación de escritorio premium para la gestión de tareas, inspirada en la estética de Apple (Dark Mode). Diseñada para ofrecer una experiencia fluida, visualmente impactante y altamente funcional.

---

## ✨ Características (Pro v2.0)

- **Diseño Apple "High-Contrast":** Estética minimalista con bordes de color característicos para cada tipo de tarea.
- **Navegación Dual:** Arrastra y suelta tareas o usa los nuevos botones de navegación rápida.
- **Gestión de Fechas:** Calendario integrado con diseño premium.
- **Seguridad:** Sistema de login persistente con cifrado SHA-256.
- **Persistencia Robusta:** Backup automático con base de datos SQLite.
- **Totalmente Portátil:** Se distribuye como un único ejecutable.

---

## 🛠️ Compilación y Ejecución

Si deseas compilar la aplicación tú mismo en Linux:

1. **Compilar con un comando:**
   ```bash
   chmod +x compile.sh
   ./compile.sh
   ```

2. **Ejecutar el binario generado:**
   ```bash
   ./dist/kanbanpy_pro_v2
   ```

---

## 📦 Dependencias (para desarrollo)

- Python 3.12+
- PyQt6
- PyInstaller (para compilación)

Para instalar manualmente:
```bash
pip install -r requirements.txt
```

---

## 🚀 Uso Rápido
1. Inicia sesión o regístrate.
2. Crea tareas en la columna **ToDo**.
3. Muévelas a **Doing** mientras las realizas.
4. Llévalas a **Done** cuando hayas terminado.

---

## 🚀 Instalación y Favoritos

Para usar **Kanbanpy Pro** diariamente con un icono en tus favoritos:

### Opción 1: Instalación del Sistema (Recomendado)
Instala el paquete `.deb` incluido. Esto añadirá el icono automáticamente a tu menú de aplicaciones:
```bash
sudo apt install ./kanban-app_1.0-1_all.deb
```
Luego búscalo como "Kanban App" en tu menú y selecciona **"Añadir a favoritos"**.

### Opción 2: Acceso Directo Manual
Si prefieres no instalar el sistema, usa el archivo `kanbanpy.desktop` incluido:
1. Copia el archivo a tu carpeta de aplicaciones local:
   ```bash
   cp kanbanpy.desktop ~/.local/share/applications/
   ```
2. Dale permisos de ejecución (si es necesario):
   ```bash
   chmod +x ~/.local/share/applications/kanbanpy.desktop
   ```

---
*Kanbanpy Pro v2.0 - hnavarro*
