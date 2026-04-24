# 🤖 Monitor Citas Vulnerabilidad — Ayto. Las Palmas GC

Vigila automáticamente la disponibilidad de citas para el trámite **"Informe de vulnerabilidad para regularización de extranjeros"** en la oficina **METROPOL (León y Castillo 270)**.

Cuando detecta citas, te avisa por **Telegram con captura de pantalla**.

---

## ⚡ Frecuencia de chequeo

| Cuándo | Frecuencia |
|---|---|
| **Martes y jueves** de 7:00 a 15:00 (hora Canarias) | Cada **5 minutos** |
| Resto de momentos | Cada **10 minutos** |

> Las citas de este trámite se ofertan los martes y jueves según el Ayuntamiento.

---

## 🚀 Instalación paso a paso

### 1️⃣ Crear un bot de Telegram NUEVO (chat exclusivo)

> ⚠️ Crea un bot **distinto** al del consulado para tener las notificaciones separadas.

1. Abre Telegram → busca **@BotFather**
2. Escríbele `/newbot`
3. Nombre: `Citas LPGC` (o lo que quieras)
4. Username: `@citas_lpgc_tuuser_bot` (debe ser único)
5. Guarda el **token** que te da (ej: `7123456789:AAFxxxxxxxxxxxxx`)
6. **Abre el bot nuevo** en Telegram y escríbele `/start` para activarlo

### 2️⃣ Obtener tu Chat ID

Si ya lo tienes del otro bot, es el mismo número. Si no:
1. Busca **@userinfobot** en Telegram
2. Escríbele `/start`
3. Guarda tu **ID numérico** (ej: `123456789`)

### 3️⃣ Crear repositorio en GitHub

```bash
cd citas-bot
git init
git add .
git commit -m "bot citas vulnerabilidad LPGC"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/citas-vulnerabilidad-lpgc.git
git push -u origin main
```

### 4️⃣ Configurar Secrets en GitHub

Ve a tu repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Nombre | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN_LPGC` | El token del bot **nuevo** (de @BotFather) |
| `TELEGRAM_CHAT_ID_LPGC` | Tu ID numérico (de @userinfobot) |

> 📌 Los nombres son distintos a los del bot del consulado (`_LPGC`) para que no interfieran.

### 5️⃣ Activar GitHub Actions

1. Ve a la pestaña **Actions** de tu repo
2. Si pide confirmar → "I understand my workflows, go ahead and enable them"
3. Haz clic en **"Run workflow"** para probarlo manualmente la primera vez

### 6️⃣ Dar permisos de escritura (si da error)

Si ves "Resource not accessible by integration":
1. **Settings** → **Actions** → **General**
2. Sección "Workflow permissions" → marca **"Read and write permissions"**
3. Guardar

---

## 📊 Cómo funciona

```
GitHub Actions (cada 5 min)
        │
        ▼
  ¿Toca ejecutar? (martes/jueves=5min, resto=10min)
        │
    No ──┤── Sí
    │         │
  Sale        ▼
           Abre navegador headless (Playwright)
                │
                ▼
           1. Entra en cita previa LPGC
           2. Clic "Solicitar una nueva cita"
           3. Clic "Solicitar Cita Previa"
           4. Clic "Informe de vulnerabilidad..."
           5. Clic "METROPOL - León y Castillo 270"
                │
                ▼
           Lee sección "3. Cuándo"
                │
         ┌──────┴──────┐
         │             │
  "No existen     ¡HAY CITAS!
   citas"              │
         │             ▼
       Nada      📱 Telegram:
                  - Mensaje de alerta
                  - Captura de pantalla
                  - Recordatorio
```

---

## 🔧 Personalización

### Cambiar frecuencia
Edita la función `debe_ejecutarse()` en `monitor_citas.py`:
```python
# Ejemplo: cada 5 min TODOS los días
def debe_ejecutarse():
    return True
```

### Vigilar otro trámite u oficina
Cambia estas líneas en `monitor_citas.py`:
```python
TRAMITE = "Registro - Empadronamiento - Certificados"  # otro trámite
DISTRITO = "DISTRITO ISLETA-PUERTO-GUANARTEME"          # otra oficina
```

---

## 🆘 Problemas comunes

**El bot no envía mensajes**
→ ¿Le escribiste `/start` al bot nuevo? Es obligatorio para activarlo.

**Timeout en los clics**
→ La web puede estar lenta o haber cambiado su estructura. Mira la captura en Actions → Artifacts.

**"No existen citas" siempre**
→ Es normal fuera de martes y jueves. El bot sigue vigilando por si abren slots extra.

**Minutos de GitHub Actions**
→ Repo **público** = minutos ilimitados gratis. Repo **privado** = 2.000 min/mes gratis.
