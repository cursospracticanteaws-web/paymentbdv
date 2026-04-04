import re
import random
import requests
import time
import os
from flask import Flask, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# --- CONFIGURACIÓN ---
SESSION_FILE = "sesion_bdv.json"
SMS_SERVICE_URL = "http://localhost:9097/get-sms"

def inyectar_blindaje_total(page):
    """
    Técnica de evasión definitiva. Elimina el rastro de 'webdriver'
    del prototipo del navegador antes de que la página cargue.
    """
    stealth_js = """
    (() => {
        // 1. Borrar la bandera de webdriver del prototipo
        const newProto = navigator.__proto__;
        delete newProto.webdriver;
        navigator.__proto__ = newProto;

        // 2. Mock de Chrome y Hardware
        window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {}, app: {} };
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
        Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    })();
    """
    page.add_init_script(stealth_js)
    print("🛡️  Blindaje Nivel 2: WebDriver eliminado del prototipo.")

def run_pago_movil():
    with sync_playwright() as p:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        
        # Lanzamiento con argumentos de evasión críticos
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-sandbox"
            ]
        )
        
        # Gestión de Sesión (Cookies)
        storage = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        context = browser.new_context(
            user_agent=user_agent,
            storage_state=storage,
            viewport={'width': 1366, 'height': 768}
        )
        
        page = context.new_page()
        inyectar_blindaje_total(page)
        
        def espera_humana(min_s=2, max_s=4):
            page.wait_for_timeout(random.uniform(min_s * 1000, max_s * 1000))

        try:
            print("🌐 Navegando al Banco...")
            page.goto("https://bdvenlinea.banvenez.com/", wait_until="networkidle", timeout=60000)
            
            # --- LÓGICA DE LOGIN ---
            user_field = page.get_by_role("textbox", name="usuario")
            if user_field.is_visible(timeout=8000):
                print("🔑 Sesión expirada. Iniciando sesión...")
                user_field.type("isaacli77", delay=random.uniform(100, 200))
                page.get_by_role("button", name="Entrar").click()
                
                page.wait_for_selector("input[type='password']", timeout=15000)
                page.get_by_role("textbox", name="Introduce tu contraseña").type("31Enero3031*", delay=random.uniform(100, 200))
                page.get_by_role("button", name="Continuar").click()
                
                # Esperar entrada y guardar cookies
                page.wait_for_selector("button:has-text('Pagos')", timeout=60000)
                context.storage_state(path=SESSION_FILE)
                print("💾 Sesión guardada en JSON.")
            else:
                print("🚀 Sesión activa recuperada.")

            # --- PROCESO DE PAGO MÓVIL ---
            espera_humana(2, 3)
            page.get_by_role("button", name="Pagos ▾").click()
            page.get_by_role("menuitem", name="PagomóvilBDV").click()
            page.get_by_role("menuitem", name="pago a personas").click()
            
            espera_humana(2, 4)
            page.get_by_text("Pago no registrado").click()
            
            print("📝 Rellenando formulario de pago...")
            page.get_by_role("textbox", name="Cédula").type("33612754", delay=120)
            page.locator("div").filter(has_text=re.compile(r"^Teléfono$")).nth(3).click()
            page.get_by_role("textbox", name="Teléfono").type("04242370576", delay=120)
            
            monto_input = page.get_by_role("textbox", name="Monto en (Bs.)")
            monto_input.click()
            monto_input.type("1.00", delay=150)
            
            espera_humana(1, 2)
            page.get_by_role("button", name="Pagar").click()
            page.get_by_role("button", name="Confirmar").click()

            # --- CAPTURA DE SMS ---
            input_sms = page.get_by_role("textbox", name="Introduzca código recibido")
            input_sms.wait_for(state="visible", timeout=20000)
            
            print("⏳ Consultando SMS en puerto 9097...")
            codigo = None
            for _ in range(30):
                try:
                    r = requests.get(SMS_SERVICE_URL, timeout=5)
                    if r.status_code == 200:
                        codigo = r.json().get("code")
                        if codigo:
                            print(f"✅ Código interceptado: {codigo}")
                            break
                except: pass
                time.sleep(2)

            if codigo:
                input_sms.type(codigo, delay=200)
                page.get_by_role("button", name="Continuar").click()
                print("🏁 PAGO EXITOSO.")
                context.storage_state(path=SESSION_FILE)
                resultado = {"status": "success", "monto": "1.00"}
            else:
                resultado = {"status": "error", "message": "SMS Timeout"}

            page.wait_for_timeout(5000)
            browser.close()
            return resultado

        except Exception as e:
            print(f"❌ Error en la ejecución: {e}")
            if 'browser' in locals(): browser.close()
            return {"status": "error", "message": str(e)}

# --- RUTA RESTAURADA ---
@app.route('/ejecutar-pago', methods=['GET', 'POST'])
def api_pago():
    return jsonify(run_pago_movil())

if __name__ == '__main__':
    print("🔥 Servidor Flask activo en http://localhost:9096/ejecutar-pago")
    app.run(port=9096, threaded=False)