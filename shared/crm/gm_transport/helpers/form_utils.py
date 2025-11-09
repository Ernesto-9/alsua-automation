"""
Utilidades de formularios para GM Transport
Llenado de campos, selección de elementos, etc.
"""
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .ui_utils import cerrar_todos_los_alerts, cerrar_calendarios_abiertos

logger = logging.getLogger(__name__)


def llenar_fecha(driver, debug_logger, id_input, fecha_valor, incluir_hora=True):
    """
    Llena un campo de fecha de forma robusta

    Args:
        driver: WebDriver de Selenium
        debug_logger: Logger de debug
        id_input: ID del campo de fecha
        fecha_valor: Valor de la fecha en formato dd/mm/YYYY
        incluir_hora: Si incluir hora en el valor

    Returns:
        bool: True si se llenó exitosamente
    """
    try:
        debug_logger.info(
            f"Llenando fecha {id_input} con valor {fecha_valor}, incluir_hora={incluir_hora}"
        )

        # Preparación especial para EDT_DESDE
        if id_input == "EDT_DESDE":
            cerrar_todos_los_alerts(driver)
            cerrar_calendarios_abiertos(driver)
            time.sleep(1.5)

        cerrar_todos_los_alerts(driver)
        cerrar_calendarios_abiertos(driver)
        time.sleep(0.5)

        # Verificar estado de la página
        try:
            estado_pagina = driver.execute_script("return document.readyState")
            if estado_pagina != "complete":
                time.sleep(1)
        except:
            pass

        # Verificar que el elemento exista
        try:
            elemento_existe = driver.find_element(By.ID, id_input)
        except Exception as e:
            logger.error(f"Elemento {id_input} NO ENCONTRADO: {e}")
            debug_logger.error(f"Campo {id_input} no encontrado: {e}")
            return False

        # Construir valor con hora si es necesario
        if incluir_hora:
            try:
                valor_actual = driver.execute_script(
                    f"return document.getElementById('{id_input}').value;"
                )
                if valor_actual and " " in valor_actual:
                    hora = valor_actual.split(" ")[1]
                else:
                    hora = "14:00"
            except:
                hora = "14:00"
            nuevo_valor = f"{fecha_valor} {hora}"
        else:
            nuevo_valor = fecha_valor

        # Intentar llenar el campo (3 intentos)
        for intento in range(3):
            try:
                cerrar_todos_los_alerts(driver)

                script = f"""
                var campo = document.getElementById('{id_input}');
                if (campo) {{
                    campo.value = '{nuevo_valor}';
                    campo.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    campo.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    campo.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    return true;
                }}
                return false;
                """

                resultado = driver.execute_script(script)

                if not resultado:
                    time.sleep(2)
                    continue

                time.sleep(0.5)

                # Verificar que el valor se haya insertado
                valor_final = driver.execute_script(
                    f"return document.getElementById('{id_input}').value;"
                )

                if valor_final and fecha_valor in valor_final:
                    debug_logger.info(f"Fecha {id_input} = {valor_final}")
                    return True
                else:
                    time.sleep(2)
                    continue

            except Exception as e:
                cerrar_todos_los_alerts(driver)
                debug_logger.error(f"Error llenando fecha {id_input} intento {intento + 1}: {e}")
                time.sleep(2)
                continue

        logger.error(f"ERROR CRÍTICO: No se pudo insertar fecha después de 3 intentos")
        debug_logger.error(f"FALLO CRÍTICO llenando fecha {id_input} con valor {fecha_valor}")
        return False

    except Exception as e:
        logger.error(f"Error en llenar_fecha: {e}")
        debug_logger.error(f"Excepción en llenar_fecha para {id_input}: {e}")
        return False


def llenar_campo_texto(wait, id_input, valor, descripcion=""):
    """
    Llena un campo de texto de forma robusta

    Args:
        wait: WebDriverWait instance
        id_input: ID del campo
        valor: Valor a insertar
        descripcion: Descripción del campo para logs

    Returns:
        bool: True si se llenó exitosamente
    """
    try:
        campo = wait.until(EC.element_to_be_clickable((By.ID, id_input)))
        campo.click()
        campo.clear()
        campo.send_keys(str(valor))
        logger.info(f"{descripcion} '{valor}' insertado en {id_input}")
        return True

    except Exception as e:
        logger.error(f"Error al llenar {descripcion} en {id_input}: {e}")
        return False


def seleccionar_base_origen(driver, wait, base_origen):
    """
    Selecciona la base origen del combo

    Args:
        driver: WebDriver de Selenium
        wait: WebDriverWait instance
        base_origen: Código de base origen

    Returns:
        bool: True si se seleccionó exitosamente
    """
    if not base_origen:
        logger.error("No se proporcionó base origen")
        return False

    try:
        base_origen_texto = f"BASE {base_origen.strip().upper()}"
        base_combo = wait.until(EC.element_to_be_clickable((By.ID, "COMBO_CATSUCURSALES")))
        driver.execute_script("arguments[0].click();", base_combo)
        time.sleep(0.5)

        opciones = base_combo.find_elements(By.TAG_NAME, "option")
        for option in opciones:
            if option.text.strip().upper() == base_origen_texto:
                valor_encontrado = option.get_attribute("value")
                script = f"""
                    var select = document.getElementById('COMBO_CATSUCURSALES');
                    select.value = '{valor_encontrado}';
                    var event = new Event('change', {{ bubbles: true }});
                    select.dispatchEvent(event);
                """
                driver.execute_script(script)
                logger.info(f"Base origen '{base_origen_texto}' seleccionada")
                return True

        logger.error(f"No se encontró la opción '{base_origen_texto}'")
        return False

    except Exception as e:
        logger.error(f"Error al seleccionar base origen: {e}")
        return False


def buscar_y_seleccionar_placa(driver, wait, tipo_placa, placa_valor):
    """
    Busca y selecciona una placa (remolque o tractor)

    Args:
        driver: WebDriver de Selenium
        wait: WebDriverWait instance
        tipo_placa: 'remolque' o 'tractor'
        placa_valor: Valor de la placa a buscar

    Returns:
        tuple: (exito, mensaje_error)
    """
    try:
        logger.info(f"Buscando {tipo_placa}: {placa_valor}")

        # Abrir buscador según tipo
        if tipo_placa == 'remolque':
            btn_buscar = wait.until(
                EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCARGA1"))
            )
        else:
            btn_buscar = wait.until(
                EC.element_to_be_clickable((By.ID, "BTN_BUSCARCODIGOUNIDADCAMION"))
            )

        btn_buscar.click()
        time.sleep(1.5)
        logger.info(f"Buscador de {tipo_placa} abierto")

        # Desmarcar filtro de unidades rentadas
        try:
            checkbox_filtro = wait.until(
                EC.element_to_be_clickable((By.ID, "CBOX_FILTRARRENTADAS_1"))
            )
            if checkbox_filtro.is_selected():
                checkbox_filtro.click()
                time.sleep(0.3)
                logger.info(f"Filtro de unidades rentadas deshabilitado para {tipo_placa}")
        except Exception as e:
            logger.warning(f"No se pudo desmarcar filtro para {tipo_placa}: {e}")

        # Ingresar placa en buscador
        campo_busqueda = wait.until(EC.element_to_be_clickable((By.ID, "EDT_BUSQUEDA")))
        campo_busqueda.clear()
        campo_busqueda.send_keys(placa_valor)
        logger.info(f"Placa {placa_valor} ingresada en buscador")

        # Aplicar búsqueda
        btn_aplicar = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[@class='btnvalignmiddle' and contains(text(), 'Aplicar')]/..")
            )
        )
        btn_aplicar.click()
        time.sleep(3)
        logger.info(f"Búsqueda aplicada para {tipo_placa}")

        # Verificar y seleccionar
        try:
            btn_seleccionar = driver.find_element(By.ID, "BTN_SELECCIONAR")
            if not btn_seleccionar.is_enabled():
                error_msg = f"Placa {tipo_placa} {placa_valor} no encontrada"
                logger.error(error_msg)
                try:
                    cerrar_btn = driver.find_element(
                        By.XPATH, "//span[contains(text(), 'Cerrar')]/.."
                    )
                    cerrar_btn.click()
                except:
                    pass
                return False, error_msg

            btn_seleccionar.click()
            time.sleep(1)
            logger.info(f"{tipo_placa.capitalize()} {placa_valor} seleccionado")
            return True, ""

        except Exception as e:
            error_msg = f"Placa {tipo_placa} {placa_valor} no encontrada"
            logger.error(error_msg)
            try:
                cerrar_btn = driver.find_element(By.XPATH, "//span[contains(text(), 'Cerrar')]/..")
                cerrar_btn.click()
            except:
                pass
            return False, error_msg

    except Exception as e:
        error_msg = f"Error buscando {tipo_placa} {placa_valor}"
        logger.error(error_msg)
        return False, error_msg
