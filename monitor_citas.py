"""
Monitor de citas - Ayuntamiento Las Palmas de Gran Canaria
Trámite: Informe de vulnerabilidad para regularización de extranjeros
Oficina: METROPOL - León y Castillo 270

Basado en bot del Consulado de España en La Habana.
Versión GitHub Actions con Playwright + notificación Telegram con captura.
"""
import asyncio
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

# ── Config ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_LPGC", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_LPGC", "")

URL_CITA_PREVIA = "https://www.laspalmasgc.es/es/otras-secciones/cita-previa/"

# Textos exactos de los botones (según capturas del usuario)
TRAMITE = "Informe de vulnerabilidad para regularización de extranjeros"
DISTRITO = "METROPOL - OFICINAS EN LEÓN y CASTILLO 270"

# Texto que aparece cuando NO hay citas
TEXTO_SIN_CITA = "No existen citas disponibles"

# Zona horaria Canarias (UTC+0 invierno / UTC+1 verano WEST)
TZ_CANARIAS = timezone(timedelta(hours=1))  # Abril = horario verano


def log(msg):
    ahora = datetime.now(TZ_CANARIAS).strftime("%d/%m/%Y %H:%M:%S")
    print(f"[{ahora}] {msg}")


def debe_ejecutarse():
    """
    Control de frecuencia:
    - Martes y jueves de 7:00 a 15:00 Canarias → cada 5 min (siempre)
    - Resto → cada 10 min (solo si el minuto es divisible por 10)
    """
    ahora = datetime.now(TZ_CANARIAS)
    dia = ahora.weekday()  # 0=lun, 1=mar, 2=mié, 3=jue ...
    hora = ahora.hour
    minuto = ahora.minute

    # Martes (1) y Jueves (3), entre 7:00 y 14:59 → cada 5 min
    if dia in (1, 3) and 7 <= hora < 15:
        log(f"📅 Martes/Jueves horario intenso ({hora}:{minuto:02d}) → ejecutar")
        return True

    # Resto de momentos → cada 10 min
    if minuto % 10 == 0:
        log(f"📅 Modo normal ({hora}:{minuto:02d}) → ejecutar (cada 10 min)")
        return True

    log(f"⏭️  Saltando ({hora}:{minuto:02d}) → no toca en modo 10 min")
    return False


def enviar_telegram(mensaje):
    """Envía mensaje de texto por Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        log("⚠ Token Telegram no configurado en secrets")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            log("✅ Telegram texto enviado")
        else:
            log(f"⚠ Error Telegram: {r.text}")
    except Exception as e:
        log(f"⚠ Error Telegram: {e}")


def enviar_telegram_foto(ruta_foto, caption=""):
    """Envía captura de pantalla por Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        log("⚠ Token Telegram no configurado en secrets")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(ruta_foto, "rb") as foto:
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
            files = {"photo": foto}
            r = requests.post(url, data=data, files=files, timeout=15)
        if r.status_code == 200:
            log("✅ Telegram foto enviada")
        else:
            log(f"⚠ Error Telegram foto: {r.text}")
    except Exception as e:
        log(f"⚠ Error Telegram foto: {e}")


async def comprobar_citas():
    """
    Flujo completo:
    1. Abrir página de cita previa
    2. Clic en "Solicitar una nueva cita"
    3. Clic en "Solicitar Cita Previa" (botón azul abajo)
    4. Clic en trámite: "Informe de vulnerabilidad..."
    5. Clic en distrito: "METROPOL - OFICINAS EN LEÓN y CASTILLO 270"
    6. Leer sección "3. Cuándo" → buscar si hay citas o no
    """
    from playwright.async_api import async_playwright

    log("🔍 Iniciando comprobación...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900},
        )
        page = await context.new_page()

        try:
            # ── Paso 1: Abrir página de cita previa ──
            log("  → Paso 1: Abriendo página de cita previa...")
            await page.goto(URL_CITA_PREVIA, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            log(f"  ✓ Página cargada: {page.url}")

            # ── Paso 2: Clic en "Solicitar una nueva cita" ──
            # Los botones son imágenes clicables, no enlaces de texto
            log("  → Paso 2: Buscando botón 'Solicitar una nueva cita'...")
            clicado = False
            # Intento 1: buscar por alt o title de imagen
            for selector in [
                "img[alt*='nueva cita' i]",
                "img[alt*='solicitar' i]",
                "img[title*='nueva cita' i]",
                "a img[src*='solicitar']",
                "a:first-of-type img",   # primer enlace con imagen en la sección de botones
            ]:
                try:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        await el.click(timeout=8000)
                        clicado = True
                        log(f"  ✓ Clic con selector: {selector}")
                        break
                except Exception:
                    continue

            # Intento 2: clicar el primer enlace grande de la sección central
            if not clicado:
                try:
                    # Los dos botones azules son los primeros <a> con imagen en el contenido
                    enlaces = page.locator(".contenido a, main a, #content a, article a")
                    count = await enlaces.count()
                    log(f"  → Encontrados {count} enlaces en el contenido, clicando el primero...")
                    if count > 0:
                        await enlaces.first.click(timeout=8000)
                        clicado = True
                        log("  ✓ Clic en primer enlace del contenido")
                except Exception as e:
                    log(f"  ⚠ Falló: {e}")

            # Intento 3: buscar cualquier enlace que lleve a la solicitud
            if not clicado:
                try:
                    await page.click("a[href*='solicitar'], a[href*='nueva'], a[href*='cita']", timeout=8000)
                    clicado = True
                    log("  ✓ Clic por href")
                except Exception:
                    pass

            if not clicado:
                raise Exception("No se encontró el botón 'Solicitar una nueva cita'")

            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path="paso2.png")
            log(f"  URL tras paso 2: {page.url}")

            # ── Paso 3: Clic en "Solicitar Cita Previa" (botón azul abajo de la página) ──
            log("  → Paso 3: Buscando botón 'Solicitar Cita Previa'...")
            clicado3 = False
            for selector in [
                "a.btn:has-text('Solicitar')",
                "a:has-text('Solicitar Cita Previa')",
                "a:has-text('Cita Previa en este enlace')",
                "input[value*='Solicitar' i]",
                "button:has-text('Solicitar')",
                ".btn-primary",
                "a[href*='cs.html']",
                "a[href*='cita']",
            ]:
                try:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        await el.click(timeout=8000)
                        clicado3 = True
                        log(f"  ✓ Paso 3 con selector: {selector}")
                        break
                except Exception:
                    continue

            if not clicado3:
                raise Exception("No se encontró el botón 'Solicitar Cita Previa'")

            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="paso3.png")
            log(f"  URL tras paso 3: {page.url}")

            # ── Paso 4: Seleccionar trámite ──
            log(f"  → Paso 4: Seleccionando trámite: '{TRAMITE}'...")
            try:
                btn_tramite = page.get_by_text(TRAMITE, exact=False).first
                await btn_tramite.wait_for(state="visible", timeout=15000)
                await btn_tramite.click()
                await page.wait_for_timeout(3000)
                log("  ✓ Trámite seleccionado")
            except Exception:
                # Buscar por botón con texto parcial
                log("  → Buscando por selector alternativo...")
                await page.click(f"button:has-text('vulnerabilidad'), a:has-text('vulnerabilidad')", timeout=15000)
                await page.wait_for_timeout(3000)
                log("  ✓ Trámite seleccionado (alternativo)")

            # ── Paso 5: Seleccionar distrito ──
            log(f"  → Paso 5: Seleccionando distrito: '{DISTRITO}'...")
            try:
                btn_distrito = page.get_by_text("METROPOL", exact=False).first
                await btn_distrito.wait_for(state="visible", timeout=15000)
                await btn_distrito.click()
                await page.wait_for_timeout(5000)
                log("  ✓ Distrito seleccionado")
            except Exception:
                log("  → Buscando METROPOL por selector...")
                await page.click("button:has-text('METROPOL'), a:has-text('METROPOL')", timeout=15000)
                await page.wait_for_timeout(5000)
                log("  ✓ Distrito seleccionado (alternativo)")

            # ── Paso 6: Tomar captura y leer resultado ──
            log("  → Paso 6: Leyendo resultado de disponibilidad...")
            await page.screenshot(path="resultado.png", full_page=False)

            contenido = await page.inner_text("body")

            if TEXTO_SIN_CITA.lower() in contenido.lower():
                log("  ❌ No existen citas disponibles")
                await browser.close()
                return False
            else:
                # Buscar indicios de citas disponibles
                indicios = [
                    "elija fecha", "elija hora", "seleccione",
                    "disponible", "mostrarán los tres días",
                    "reservar", "confirmar"
                ]
                hay_cita = any(i in contenido.lower() for i in indicios)

                if hay_cita:
                    log("  🎉 ¡¡CITAS DETECTADAS!!")
                    await page.screenshot(path="cita_encontrada.png", full_page=False)
                    await browser.close()
                    return True
                else:
                    # Contenido desconocido → avisar por si acaso
                    log(f"  ⚠ Contenido no reconocido: {contenido[:300]}")
                    await page.screenshot(path="contenido_desconocido.png", full_page=False)
                    await browser.close()
                    return "unknown"

        except Exception as e:
            log(f"  ⚠ Error en el flujo: {e}")
            try:
                await page.screenshot(path="error.png", full_page=False)
            except Exception:
                pass
            await browser.close()
            return None


async def main():
    ahora = datetime.now(TZ_CANARIAS)
    log("=" * 55)
    log("  BOT CITAS AYTO. LAS PALMAS DE GRAN CANARIA")
    log(f"  Trámite: Informe vulnerabilidad extranjeros")
    log(f"  Oficina: METROPOL - León y Castillo 270")
    log(f"  Hora Canarias: {ahora.strftime('%A %d/%m/%Y %H:%M')}")
    log("=" * 55)

    # Control de frecuencia
    if not debe_ejecutarse():
        return

    resultado = await comprobar_citas()

    if resultado is True:
        # ¡¡HAY CITAS!!
        mensaje = (
            "🚨 <b>¡¡CITAS DISPONIBLES!!</b> 🚨\n\n"
            "📍 <b>Ayto. Las Palmas de Gran Canaria</b>\n"
            f"📋 {TRAMITE}\n"
            f"🏢 {DISTRITO}\n\n"
            f"👉 <a href='{URL_CITA_PREVIA}'>ENTRA YA A RESERVAR</a>\n\n"
            f"⏰ {ahora.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        enviar_telegram(mensaje)
        enviar_telegram_foto("cita_encontrada.png", caption="📸 Captura de la página con citas disponibles")
        enviar_telegram("🔔 <b>¡¡Corre, que vuelan!!</b> Entra ya antes de que se agoten.")

    elif resultado == "unknown":
        # Contenido ha cambiado pero no reconocemos el estado
        mensaje = (
            "🟡 <b>La página ha cambiado</b>\n\n"
            "El contenido no es el habitual. Puede que haya citas.\n"
            f"👉 <a href='{URL_CITA_PREVIA}'>Compruébalo tú mismo</a>\n\n"
            f"⏰ {ahora.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        enviar_telegram(mensaje)
        enviar_telegram_foto("contenido_desconocido.png", caption="📸 Contenido no reconocido")

    elif resultado is False:
        log("Sin citas. El workflow volverá a ejecutarse según el schedule.")

    else:
        # Error
        mensaje = (
            "⚠ <b>Error en la comprobación</b>\n\n"
            "Hubo un problema al acceder a la página.\n"
            "Revisaré de nuevo en el próximo ciclo.\n\n"
            f"⏰ {ahora.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        enviar_telegram(mensaje)
        if os.path.exists("error.png"):
            enviar_telegram_foto("error.png", caption="📸 Captura del error")


if __name__ == "__main__":
    asyncio.run(main())
