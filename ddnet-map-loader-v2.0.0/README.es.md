# DDNet Map Loader v2 (Portátil)

Pequeña herramienta para abrir con doble clic cualquier archivo `.map` y recargarlo en caliente en tu servidor local de DDNet. También crea copias de seguridad y registra lo que hace.

## 📋 Requisitos
- Windows 10/11 (sin admin)
- Cliente/servidor DDNet instalados y servidor local accesible

## 🤔 Qué es y para qué sirve
- Asocia archivos `.map` con esta app.
- Al hacer doble clic en un mapa:
  - Lo valida
  - Hace copia de seguridad del mapa actual
  - Sustituye el mapa de trabajo y envía `hot_reload`
  - Escribe en `%APPDATA%\DDNet\maps\ddnet_control.log`
- Ideal para iterar rápido mientras mapeas.

## 🚀 Uso rápido
1) Revisar/mover `myServerconfig.cfg`
   - Copia `myServerconfig.cfg` a `data` (recomendado; ver detalles abajo).
2) Asociar `.map` con este EXE (método recomendado)
   - Clic derecho sobre un `.map` → Abrir con → Elegir otra aplicación → Más aplicaciones → Buscar otra aplicación en este equipo
   - Selecciona `ddnet_control.exe` en esta carpeta
   - Marca “Usar siempre esta aplicación para abrir .map” y confirma
   - Verifica que el icono de `.map` cambió; si no, mira “Solución de problemas”.
   - Avanzado (opcional): también puedes ejecutar `registry\setup_map_association_current_user.bat` y luego reiniciar el Explorador.
3) Doble clic en cualquier `.map`
   - Ejemplo: `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`
   - El icono debe ser el del cargador (puede mostrar una flecha si es acceso directo).
4) Revisar el log
   - `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 Dónde poner myServerconfig.cfg
- Forma sencilla de encontrar la carpeta `data` de DDNet:
  1) Clic derecho en el acceso directo de DDNet (barra de tareas/Inicio/Escritorio) → Abrir ubicación del archivo
  2) En la carpeta abierta, entra en `ddnet` (donde está `DDNet.exe`)
  3) Abre `data` → copia `myServerconfig.cfg` allí
- Ubicaciones comunes (ejemplos):
  - Steam por defecto: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - Otra biblioteca de Steam: `<TuBibliotecaSteam>\steamapps\common\DDraceNetwork\ddnet\data`
  - No Steam/portátil: carpeta `data` junto a `DDNet.exe`

## 🧰 Solución de problemas
- La consola se abre y se cierra al instante
  - Normalmente no se pasó la ruta del archivo. Repite la asociación (paso 2) y reinicia el Explorador.
- No aparece en “Abrir con”
  - Usa “Buscar otra aplicación en este equipo” y elige `ddnet_control.exe`; marca “Usar siempre esta aplicación…”.
- El icono no cambia
  - Reinicia el Explorador de Windows (caché de iconos).
- No hay hot‑reload
  - Asegura servidor local en `127.0.0.1:8303` y RCON correcto.
  - Mira el log para el motivo exacto.
- Deshacer asociación
  - Ejecuta: `registry\remove_map_association_current_user.bat`

## 📂 Contenido
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`