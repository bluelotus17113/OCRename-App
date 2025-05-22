from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError # IMPORTACIONES CORREGIDAS
import json
import time
import re
import base64
from io import BytesIO
from PIL import Image
from typing import Optional, Dict

# Importar settings y logger
try:
    from config import settings
except ImportError:
    class MockSettings:
        OPENROUTER_API_KEY = None
        DEEPSEEK_TEXT_MODEL = "deepseek/deepseek-r1:free"
        LLAMA32_VISION_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"
        API_TIMEOUT_SECONDS = 60
        API_MAX_RETRIES = 3
        OPENROUTER_SITE_URL = "YOUR_SITE_URL_HERE" # Placeholder
        OPENROUTER_SITE_TITLE = "OCRenameApp"      # Placeholder
    settings = MockSettings()
    print("ADVERTENCIA (ai_integration.py): No se pudo importar 'config.settings'. Usando configuraciones por defecto.")

from utils.logger import get_app_logger
app_logger = get_app_logger()


class AIIntegrator:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY if hasattr(settings, 'OPENROUTER_API_KEY') else None
        
        self.text_model_name = "deepseek/deepseek-r1:free"
        if hasattr(settings, 'DEEPSEEK_TEXT_MODEL') and settings.DEEPSEEK_TEXT_MODEL:
            self.text_model_name = settings.DEEPSEEK_TEXT_MODEL
        
        self.vision_model_name = "meta-llama/llama-3.2-11b-vision-instruct:free"
        if hasattr(settings, 'LLAMA32_VISION_MODEL') and settings.LLAMA32_VISION_MODEL:
            self.vision_model_name = settings.LLAMA32_VISION_MODEL
        
        self.client = None
        if not self.api_key:
            app_logger.warning("OPENROUTER_API_KEY no está configurada. La integración con IA estará deshabilitada.")
        else:
            try:
                timeout_seconds = settings.API_TIMEOUT_SECONDS if hasattr(settings, 'API_TIMEOUT_SECONDS') else 60
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                    timeout=timeout_seconds,
                    max_retries=0 
                )
                app_logger.info(f"Cliente OpenAI inicializado para OpenRouter. Modelo Texto: {self.text_model_name}, Modelo Visión: {self.vision_model_name}")
            except Exception as e:
                app_logger.error(f"Error al inicializar el cliente OpenAI para OpenRouter: {e}", exc_info=True)

    def is_api_configured_and_client_valid(self) -> bool:
        return bool(self.api_key and self.client)

    def _make_api_call(self, model_name: str, messages_payload: list, original_filename: str) -> Optional[Dict[str, str]]:
        if not self.is_api_configured_and_client_valid():
            app_logger.info("Cliente IA no configurado o inválido, omitiendo llamada a API.")
            return None

        site_url = settings.OPENROUTER_SITE_URL if hasattr(settings, 'OPENROUTER_SITE_URL') else "YOUR_SITE_URL_HERE"
        site_title = settings.OPENROUTER_SITE_TITLE if hasattr(settings, 'OPENROUTER_SITE_TITLE') else "OCRenameApp"
        
        extra_headers = {}
        if site_url != "YOUR_SITE_URL_HERE": # Solo añadir si no son placeholders
             extra_headers["HTTP-Referer"] = site_url
             extra_headers["X-Title"] = site_title
        
        app_logger.info(f"Enviando solicitud para '{original_filename}' al modelo IA: {model_name}")
        
        max_retries = settings.API_MAX_RETRIES if hasattr(settings, 'API_MAX_RETRIES') else 3
        completion = None # Inicializar completion a None

        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create( # Asignar a completion
                    model=model_name,
                    messages=messages_payload,
                    temperature=0.1,
                    max_tokens=350,
                    extra_headers=extra_headers,
                )
                
                # Verificar si completion y sus atributos necesarios existen antes de acceder
                if completion and completion.choices and len(completion.choices) > 0 and completion.choices[0].message:
                    ai_message_content = completion.choices[0].message.content
                    if ai_message_content is None: # A veces el contenido puede ser None explícitamente
                        ai_message_content = "" 
                        app_logger.warning(f"IA ({model_name}, intento {attempt+1}) devolvió contenido de mensaje None, tratando como vacío.")
                else:
                    app_logger.error(f"Respuesta inesperada de IA o estructura de 'completion' incompleta ({model_name}, intento {attempt+1}). Completion: {completion}")
                    ai_message_content = "" # Tratar como si no hubiera contenido para evitar más errores

                app_logger.debug(f"Respuesta cruda de IA ({model_name}, intento {attempt+1}): {ai_message_content}")

                json_match = re.search(r"```json\s*(\{.*?\})\s*```|(\{.*?\})", ai_message_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                    try:
                        extracted_data = json.loads(json_str)
                        final_data = {
                            "id_type": extracted_data.get("id_type"),
                            "id_number": extracted_data.get("id_number"),
                            "acta_no": extracted_data.get("acta_no")
                        }
                        app_logger.info(f"Datos extraídos por IA ({model_name}) para '{original_filename}': {final_data}")
                        return final_data # Éxito, salir del bucle y la función
                    except json.JSONDecodeError as json_err_inner:
                        app_logger.error(f"Error al decodificar JSON de la respuesta IA ({model_name}, intento {attempt + 1}): {json_err_inner}. JSON string: '{json_str}'")
                else:
                    app_logger.warning(f"No se encontró JSON en la respuesta de IA ({model_name}, intento {attempt + 1}) para '{original_filename}'. Contenido: {ai_message_content}")

            # --- BLOQUES EXCEPT CORREGIDOS ---
            except APIConnectionError as e: 
                app_logger.error(f"API Connection Error ({model_name}, intento {attempt+1}): {e}")
            except RateLimitError as e: 
                app_logger.warning(f"API Rate Limit Error ({model_name}, intento {attempt+1}): {e}. Esperando...")
                time.sleep(10 * (attempt + 1))
            except APIStatusError as e: 
                response_text = e.response.text if hasattr(e, 'response') and e.response else 'N/A'
                status_code = e.status_code if hasattr(e, 'status_code') else 'N/A'
                app_logger.error(f"API Status Error ({model_name}, intento {attempt+1}): Code={status_code}, Resp={response_text}")
                if hasattr(e, 'status_code') and e.status_code == 401:
                    app_logger.error("Error de autenticación con OpenRouter. Verifica tu API Key.")
                    return None 
            except Exception as e_gen: 
                 app_logger.error(f"API General Error ({model_name}, intento {attempt+1}): {e_gen}", exc_info=True)
            
            if attempt < max_retries - 1:
                app_logger.info(f"Reintentando llamada a API ({model_name}) en {3 * (attempt + 1)} segundos...")
                time.sleep(3 * (attempt + 1))
            else:
                app_logger.error(f"Todos los {max_retries} intentos de API ({model_name}) fallaron para '{original_filename}'.")
        return None # Retornar None si todos los reintentos fallan o si hay error no recuperable

    def get_data_with_text_ai(self, text_content: str, original_filename: str) -> Optional[Dict[str, str]]:
        # ... (código del prompt sin cambios) ...
        prompt = f"""
        Analiza el siguiente texto extraído de un documento llamado "{original_filename}". El texto puede contener errores de OCR.
        El documento es un "Acta de Entrega de Medicamentos" o una "Fórmula Médica" en español.
        Tu tarea es extraer la siguiente información:
        1. "id_type": El tipo de identificación del PACIENTE (ej. CC, TI, NIT, CE, RC, PA). Busca términos como "Identificación", "USUARIO", "Paciente", "DOCUMENTO".
        2. "id_number": El número de identificación del PACIENTE.
        3. "acta_no": El número del "Acta de Entrega" o "Fórmula Médica Nro." o "Orden". Busca términos como "Acta de Entrega No.", "Formula Médica Nro.", "Solicitud De Medicamentos N°", "Orden".

        Texto a analizar:
        ---
        {text_content}
        ---

        Por favor, devuelve la información ÚNICAMENTE en formato JSON con las claves "id_type", "id_number", y "acta_no".
        Si alguna pieza de información no se puede encontrar de forma confiable, establece su valor como null en el JSON.
        Asegúrate de que la respuesta sea solo el objeto JSON, sin texto adicional antes o después.
        Ejemplo: {{"id_type": "CC", "id_number": "12345678", "acta_no": "98765"}}
        """
        messages_payload = [{"role": "user", "content": prompt}]
        return self._make_api_call(self.text_model_name, messages_payload, original_filename)

    def get_data_with_vision_ai(self, pil_image_obj: Image.Image, original_filename: str) -> Optional[Dict[str, str]]:
        # ... (código del prompt sin cambios) ...
        if not self.vision_model_name:
            app_logger.warning("Nombre del modelo de visión no configurado. Omitiendo IA de visión.")
            return None
        if not pil_image_obj:
            app_logger.warning("Objeto de imagen PIL vacío proporcionado a la IA de visión.")
            return None

        try:
            buffered = BytesIO()
            pil_image_obj.save(buffered, format="PNG") 
            img_str_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            image_data_url = f"data:image/png;base64,{img_str_base64}"

            prompt_text = f"""
            Analiza la siguiente imagen de un documento llamado "{original_filename}".
            El documento es un "Acta de Entrega de Medicamentos" o una "Fórmula Médica" en español.
            Puede contener tanto texto impreso como texto manuscrito.
            Tu tarea es extraer la siguiente información directamente de la imagen:
            1. "id_type": El tipo de identificación del PACIENTE (ej. CC, TI, NIT, CE, RC, PA). Busca la identificación asociada al paciente o usuario.
            2. "id_number": El número de identificación del PACIENTE.
            3. "acta_no": El número del "Acta de Entrega" o "Fórmula Médica Nro." o "Orden". Busca también un número manuscrito prominente, a menudo en una esquina (especialmente superior derecha), que podría ser un número de orden o acta, usualmente de 4 a 6 dígitos. Si encuentras tanto un número de fórmula impreso como un número manuscrito que calce con esta descripción, prioriza el manuscrito si parece ser un número de control de entrega.

            Por favor, devuelve la información ÚNICAMENTE en formato JSON con las claves "id_type", "id_number", y "acta_no".
            Si alguna información no se puede encontrar de forma confiable, usa null para su valor.
            Asegúrate de que la respuesta sea solo el objeto JSON, sin texto adicional antes o después.
            Ejemplo de JSON si se encuentra todo: {{"id_type": "CC", "id_number": "12345678", "acta_no": "46150"}}
            Ejemplo si falta el acta: {{"id_type": "CC", "id_number": "12345678", "acta_no": null}}
            """

            messages_payload = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", 
                     "image_url": {
                         "url": image_data_url,
                         }
                    }
                ]
            }]
            return self._make_api_call(self.vision_model_name, messages_payload, original_filename)

        except Exception as e_vision_prep:
            app_logger.error(f"Error preparando datos o llamando a IA de visión: {e_vision_prep}", exc_info=True)
            return None