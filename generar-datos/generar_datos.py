# -*- coding: utf-8 -*-
"""
Generador simulado de datos para tablero educativo de Call Center Ecommerce.
Produce dos archivos CSV totalmente compatibles con app-av.py:
  1) llamadas_cdr.csv   -> incluye 'atendida' (bool) y 'aht_seg' (num)
  2) casos_tickets.csv -> incluye 'categoria_etiqueta' y 'comentario_caso' variados

Uso:  python generar_datos_callcenter.py
Requisitos: solo librería estándar (csv, random, datetime).
"""

import csv
import random
from datetime import datetime, timedelta

# ----------------------------- CONFIG -----------------------------
FECHA_INICIO = datetime(2026, 8, 1)   # 60 días de historia
DIAS = 92  # variable de días de historia
LLAMADAS_POR_DIA_BASE = 250           # día típico
ARCHIVO_CDR = "llamadas_cdr.csv"
ARCHIVO_CASOS = "casos_tickets.csv"
random.seed(42)                       # reproducible

# Perfil horario de un ecommerce (suma ajustada a 1.0)
PERFIL_HORARIO = {
    0: 0.005, 1: 0.002, 2: 0.001, 3: 0.001, 4: 0.001, 5: 0.005, 6: 0.01,
    7: 0.02, 8: 0.04, 9: 0.06, 10: 0.08, 11: 0.10, 12: 0.09,
    13: 0.07, 14: 0.06, 15: 0.06, 16: 0.06, 17: 0.05, 18: 0.05,
    19: 0.07, 20: 0.08, 21: 0.06, 22: 0.03, 23: 0.015,
}

# Motivos de contacto: (peso, AHT promedio seg, %FCR)
MOTIVOS = {
    "estado_envio":    (0.28, 240, 0.85),
    "devolucion":      (0.20, 420, 0.62),
    "problema_pago":   (0.15, 360, 0.70),
    "cambio_producto": (0.12, 450, 0.58),
    "facturacion":     (0.08, 300, 0.75),
    "cuenta_claves":   (0.07, 210, 0.80),
    "reclamo_calidad": (0.06, 540, 0.45),
    "informacion_preventa": (0.04, 260, 0.88),
}

# Banco de comentarios variados y contextuales por motivo
COMENTARIOS_MOTIVO = {
    "estado_envio": [
        "El paquete aparece en transito desde hace 5 dias sin actualizaciones en la plataforma.",
        "El cliente consulta si despacharan su pedido hoy mismo porque viaja la semana entrante.",
        "Duda sobre el punto de retiro elegido para buscar su compra online.",
        "El servicio postal indico direccion incorrecta y el cliente aclara las referencias.",
        "Consulta demoras en la entrega debido al temporal en su zona."
    ],
    "devolucion": [
        "Solicita etiqueta de retorno para cambiar un articulo por talle incorrecto.",
        "El producto llego con un pequeno defecto de fabrica y pide reembolso total.",
        "Quiere saber los plazos vigentes para devolver una compra internacional.",
        "Indica que el articulo recibido no coincide con la descripcion de la web.",
        "Consulta el estado de acreditacion del dinero tras despachar la devolucion."
    ],
    "problema_pago": [
        "La pasarela de pagos rechazo la tarjeta de credito pero el banco debito el saldo.",
        "Consulta por que se duplico el cobro de la cuota en su resumen.",
        "Dificultades para aplicar un cupon de descuento promocional en el checkout.",
        "Requiere factura A de su ultima transaccion corporativa.",
        "Error al intentar abonar mediante transferencia bancaria inmediata."
    ],
    "cambio_producto": [
        "Desea cambiar el color del articulo adquirido manteniendo el mismo modelo.",
        "Consulta si puede abonar la diferencia por un producto superior en sucursal.",
        "El talle le quedo chico y quiere gestionar el cambio express.",
        "Pregunta si hay stock disponible del articulo antes de enviar el cambio.",
        "Consulta costos de envio asociados al reenvio por cambio de mercaderia."
    ],
    "facturacion": [
        "Error en los datos fiscales cargados en el comprobante electronico.",
        "Solicita reenvio de la factura de compra que no llego a su casilla.",
        "Consulta sobre percepciones impositivas aplicadas en su ticket.",
        "Requiere nota de credito por una promocion no aplicada correctamente.",
        "Actualizacion de razon social en el padron de facturacion."
    ],
    "cuenta_claves": [
        "No recibe el correo electronico para blanquear y restablecer su password.",
        "Su cuenta aparece bloqueada temporalmente tras multiples intentos fallidos.",
        "Desea actualizar su numero de telefono celular asociado al perfil.",
        "Problemas para fusionar dos cuentas creadas con distintos e-mails.",
        "Consulta de seguridad sobre inicio de sesion detectado en otro dispositivo."
    ],
    "reclamo_calidad": [
        "El producto perecedero llego con cadena de frio interrumpida.",
        "Empaque roto y faltantes de accesorios dentro de la caja sellada.",
        "El articulo dejo de funcionar a las 48 horas de haberlo recibido.",
        "Falla generalizada en el lote del producto adquirido.",
        "Disconformidad con la atencion previa recibida en el chat de soporte."
    ],
    "informacion_preventa": [
        "Consulta caracteristicas tecnicas detalladas de un lanzamiento proximo.",
        "Pregunta por disponibilidad de stock mayorista para compras corporativas.",
        "Verifica medios de financiacion y cuotas sin interes vigentes con bancos.",
        "Consulta plazos estimados de entrega para envios al interior del pais.",
        "Dudas sobre las dimensiones fisicas de un mueble publicado."
    ]
}

AGENTES = [f"AG-{i:03d}" for i in range(1, 26)]
TURNOS = {
    "matutino": list(range(7, 15)),
    "vespertino": list(range(15, 23)),
    "nocturno": [23, 0, 1, 2, 3, 4, 5, 6]
}
COLAS = ["Soporte_Pedidos", "Soporte_Envios", "Retenciones", "Ventas"]
ESCALAMIENTOS = ["", "", "", "", "", "Supervisor", "Area_Logistica", "Area_Billing"]

# --------------------------- UTILIDADES ---------------------------
def elegir_ponderado(dic):
    r = random.random()
    acum = 0.0
    for k, (peso, *_rest) in dic.items():
        acum += peso
        if r <= acum:
            return k
    return list(dic.keys())[-1]

def agentes_disponibles(hora):
    if hora in TURNOS["matutino"]:
        n = 12
    elif hora in TURNOS["vespertino"]:
        n = 10
    else:
        n = 5
    return random.sample(AGENTES, min(n, len(AGENTES)))

# --------------------------- GENERACIÓN ---------------------------
llamadas = []
casos = []
id_llamada = 100000
id_caso = 50000
id_cliente_pool = [f"CLI-{i:05d}" for i in range(1, 4001)]

for d in range(DIAS):
    dia = FECHA_INICIO + timedelta(days=d)
    factor = 1.15 if dia.weekday() >= 5 else 1.0
    total_hoy = int(LLAMADAS_POR_DIA_BASE * factor * random.uniform(0.9, 1.1))

    for _ in range(total_hoy):
        id_llamada += 1
        r, acum, hora = random.random(), 0.0, 11
        for h, p in PERFIL_HORARIO.items():
            acum += p
            if r <= acum:
                hora = h
                break
        minuto = random.randint(0, 59)
        ts_entrada = dia.replace(hour=hora, minute=minuto, second=random.randint(0, 59))

        motivo = elegir_ponderado(MOTIVOS)
        _, aht_prom, fcr_motivo = MOTIVOS[motivo]
        cola = random.choices(COLAS, weights=[35, 35, 15, 15])[0]

        factor_pico = 2.2 if hora in (11, 12, 20) else (1.5 if hora in (10, 13, 19, 21) else 1.0)
        espera = max(3, int(random.expovariate(1 / (18 * factor_pico))))

        p_abandono = min(0.55, espera / 180)
        if random.random() < p_abandono:
            resultado, duracion, acw = "abandonada", 0, 0
            agente, escalo = "", ""
            fcr_flag, csat = None, None
            atendida_bool = False
            aht_seg = 0
        else:
            resultado = "atendida"
            agente = random.choice(agentes_disponibles(hora))
            duracion = max(30, int(random.gauss(aht_prom - 45, aht_prom * 0.25)))
            acw = random.randint(15, 60)
            escalo = random.choice(ESCALAMIENTOS)
            fcr_flag = random.random() < fcr_motivo
            base = 4.0 if (fcr_flag and not escalo) else 3.2
            csat = max(1, min(5, round(random.gauss(base - (0.8 if escalo else 0), 0.7))))
            atendida_bool = True
            aht_seg = duracion + acw

        # CAMPOS EXIGIDOS POR app-av.py INCLUIDOS:
        llamadas.append({
            "id_llamada": f"L{id_llamada}",
            "fecha": ts_entrada.strftime("%Y-%m-%d"),
            "hora": hora,
            "fecha_hora_entrada": ts_entrada.strftime("%Y-%m-%d %H:%M:%S"),
            "id_cliente": random.choice(id_cliente_pool),
            "id_agente": agente,
            "cola": cola,
            "tipo_llamada": random.choices(["entrante", "saliente"], weights=[90, 10])[0],
            "motivo": motivo,
            "resultado_llamada": resultado,
            "atendida": atendida_bool,           # <-- Requerido en tab_agentes de app-av.py
            "aht_seg": aht_seg,                 # <-- Requerido en tab_agentes de app-av.py
            "espera_seg": espera,
            "duracion_seg": duracion,
            "acw_seg": acw,
            "escalado_a": escalo,
            "dia_semana": dia.strftime("%A"),
        })

        if resultado == "atendida" and random.random() < 0.85:
            id_caso += 1
            reincidencia = (not fcr_flag) if random.random() < 0.7 else (random.random() > 0.8)
            comentario_generado = random.choice(COMENTARIOS_MOTIVO[motivo])
            
            # CAMPOS EXIGIDOS POR app-av.py INCLUIDOS:
            casos.append({
                "id_caso": f"C{id_caso}",
                "id_llamada": f"L{id_llamada}",
                "fecha_apertura": ts_entrada.strftime("%Y-%m-%d"),
                "id_cliente": llamadas[-1]["id_cliente"],
                "id_agente": agente,
                "categoria": motivo,
                "categoria_etiqueta": motivo.replace("_", " ").title(), # <-- Requerido en tab_calidad y tab_estadistica
                "comentario_caso": comentario_generado,                  # <-- Variantes de reclamo enriquecidas
                "estado_caso": "reabierto" if reincidencia else random.choices(
                    ["resuelto", "pendiente"], weights=[85, 15])[0],
                "fcr": int(bool(fcr_flag and not reincidencia)),
                "reincidencia": int(reincidencia),
                "horas_resolucion": round(abs(random.gauss(18, 10)), 1),
                "csat": csat if csat is not None else random.randint(1, 5),
                "valor_orden": round(random.uniform(15, 450), 2),
            })

# --------------------------- EXPORT ---------------------------
columnas_cdr = list(llamadas[0].keys())
with open(ARCHIVO_CDR, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=columnas_cdr)
    w.writeheader()
    w.writerows(llamadas)

columnas_casos = list(casos[0].keys())
with open(ARCHIVO_CASOS, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=columnas_casos)
    w.writeheader()
    w.writerows(casos)

# --------------------------- RESUMEN ---------------------------
atendidas = [l for l in llamadas if l["resultado_llamada"] == "atendida"]
sl = 100 * sum(1 for l in llamadas if l["espera_seg"] <= 20) / len(llamadas)
aband = 100 * (len(llamadas) - len(atendidas)) / len(llamadas)
asa = sum(l["espera_seg"] for l in llamadas) / len(llamadas)
aht = (sum(l["aht_seg"] for l in atendidas) / len(atendidas))
fcr = 100 * sum(c["fcr"] for c in casos) / len(casos)
csat = sum(c["csat"] for c in casos) / len(casos)

print(f"Archivo {ARCHIVO_CDR}: {len(llamadas):,} llamadas")
print(f"Archivo {ARCHIVO_CASOS}: {len(casos):,} casos")
print("--- KPIs resultantes ---")
print(f"Nivel de servicio (<=20s): {sl:.1f}%")
print(f"Tasa de abandono: {aband:.1f}%")
print(f"ASA: {asa:.0f}s | AHT: {aht:.0f}s")
print(f"FCR: {fcr:.1f}% | CSAT: {csat:.2f}/5")