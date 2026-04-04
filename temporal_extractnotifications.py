from flask import Flask, jsonify
from flask_cors import CORS
import asyncio
import re
import winrt.windows.foundation
import winrt.windows.foundation.collections
from winrt.windows.ui.notifications.management import UserNotificationListener
from winrt.windows.ui.notifications import NotificationKinds

app = Flask(__name__)
CORS(app)

# Variable global para rastrear los IDs de notificaciones ya procesadas
notificaciones_vistas = set()

async def inicializar_mensajes_existentes():
    """Carga las notificaciones que ya están en pantalla al iniciar para ignorarlas."""
    global notificaciones_vistas
    listener = UserNotificationListener.current
    try:
        notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
        for notif in notifications:
            notificaciones_vistas.add(notif.id)
        print(f"✅ Sistema listo. Ignorando {len(notificaciones_vistas)} mensajes antiguos.")
    except Exception as e:
        print(f"Error al inicializar: {e}")

async def buscar_sms_nuevo():
    global notificaciones_vistas
    listener = UserNotificationListener.current
    
    # Consultamos todas las notificaciones tipo TOAST
    notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
    
    for notif in notifications:
        # SI el ID de la notificación NO está en nuestro conjunto de 'vistas'
        if notif.id not in notificaciones_vistas:
            try:
                visual = notif.notification.visual
                binding = visual.get_binding("ToastGeneric")
                if binding:
                    text_elements = binding.get_text_elements()
                    for el in text_elements:
                        mensaje = el.text
                        # Buscamos el patrón de 7 dígitos del BDV
                        match = re.search(r"es\s+(\d{7})", mensaje)
                        if match:
                            codigo = match.group(1)
                            # Marcamos esta notificación como vista para no repetirla
                            notificaciones_vistas.add(notif.id)
                            print(f"📩 ¡Nuevo código detectado!: {codigo}")
                            return codigo
            except Exception:
                continue
    return None

@app.route('/get-sms', methods=['GET'])
def get_sms():
    # Creamos el loop para manejar la consulta asíncrona a Windows
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    codigo = loop.run_until_complete(buscar_sms_nuevo())
    loop.close()

    if codigo:
        return jsonify({"status": "success", "code": codigo}), 200
    else:
        return jsonify({"status": "pending", "message": "Esperando mensaje nuevo..."}), 404

# Limpieza periódica opcional (para no llenar la RAM si dejas el script prendido días)
@app.route('/clear-cache', methods=['GET'])
def clear_cache():
    global notificaciones_vistas
    notificaciones_vistas.clear()
    return jsonify({"status": "cleared"}), 200

if __name__ == '__main__':
    # Al arrancar el script, marcamos lo que ya está en el centro de actividades como "viejo"
    loop = asyncio.new_event_loop()
    loop.run_until_complete(inicializar_mensajes_existentes())
    loop.close()
    
    print("\n" + "="*50)
    print("🚀 SMS SERVICE 9097 - MODO FILTRO NUEVO ACTIVO")
    print("Solo se entregarán códigos que lleguen a partir de este momento.")
    print("="*50 + "\n")
    
    app.run(port=9097, debug=False)