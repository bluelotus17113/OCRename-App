from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError # <--- IMPORTAR EXCEPCIONES
import json
import time
import re
from typing import Optional, Dict

# Para la función multimodal (aunque sea placeholder, para que Pylance no se queje)
from PIL import Image
from io import BytesIO
import base64

from config import settings
from utils.logger import get_app_logger

app_logger = get_app_logger()

class AIIntegrator:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY if hasattr(settings, 'OPENROUTER_API_KEY') else None
        self.text_model = settings.AI_MODEL_TO_USE if hasattr(settings, 'AI_MODEL_TO_USE') else "deepseek/deepseek-r1:free"
        self.multimodal_model = settings.MULTIMODAL_MODEL_NAME if hasattr(settings, 'MULTIMODAL_MODEL_NAME') else None
        
        self.client = None
        if not self.api_key:
            app_logger.warning("OPENROUTER_API_KEY no está configurada. La integración con IA estará deshabilitada.")
        else:
            try:
                api_timeout = settings.API_TIMEOUT_SECONDS if hasattr(settings, 'API_TIMEOUT_SECONDS') else 30
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                    timeout=api_timeout, 
                    max_retries=0
                )
                app_logger.info(f"Cliente OpenAI inicializado para OpenRouter. Modelo de texto: {self.text_model}, Timeout: {api_timeout}s")
            except Exception as e:
                app_logger.error(f"Error al inicializar el cliente OpenAI para OpenRouter: {e}", exc_info=True)
                self.client = None

    def is_api_configured_and_client_valid(self) -> bool:
        return bool(self.api_key and self.client)

    def get_data_with_text_ai(self, text_content: str, original_filename: str) -> Optional[Dict[str, str]]:
        if not self.is_api_configured_and_client_valid():
            app_logger.info("Cliente IA (texto) no configurado o inválido, omitiendo llamada a API.")
            return None
        if not text_content:
            app_logger.warning(f"Texto vacío proporcionado a la IA de texto para '{original_filename}', omitiendo.")
            return None

        prompt = f"""
        Analiza el siguiente texto extraído de un documento llamado "{original_filename}". El texto puede contener errores de OCR.
        El documento es un "Acta de Entrega de Medicamentos" o una "Fórmula Médica" en español.
        Tu tarea es extraer la siguiente información:
        1.  "id_type": El tipo de identificación del paciente (ej. CC, TI, NIT, CE, RC, PA). Si no se especifica pero hay un número que parece una cédula colombiana, asume "CC".
        2.  "id_number": El número de identificación del paciente.
        3.  "acta_no": El número del "Acta de Entrega" o "Fórmula Médica Nro.". Suele estar precedido por "Acta de Entrega No.", "Formula Médica Nro.", "Orden", o similar.

        Texto a analizar:
        ---
        {text_content}
        ---

        Por favor, devuelve la información ÚNICAMENTE en formato JSON con las claves "id_type", "id_number", y "acta_no".
        Si alguna pieza de información no se puede encontrar de forma confiable, establece su valor como null en el JSON.
        Asegúrate de que la respuesta sea solo el objeto JSON, sin texto adicional antes o después.
        Ejemplo de salida JSON esperada:
        {{
          "id_type": "CC",
          "id_number": "12345678",
          "acta_no": "98765"
        }}
        Otro ejemplo si falta el acta:
        {{
          "id_type": "TI",
          "id_number": "87654321",
          "acta_no": null
        }}
        """
        messages = [{"role": "user", "content": prompt}]
        
        extra_headers = {} # Configura si es necesario

        app_logger.info(f"Enviando texto de '{original_filename}' al modelo IA de texto: {self.text_model}")
        
        max_retries = settings.API_MAX_RETRIES if hasattr(settings, 'API_MAX_RETRIES') else 1
        
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.text_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=300, 
                    extra_headers=extra_headers if any(extra_headers.values()) else None,
                )
                
                ai_message_content = completion.choices[0].message.content
                app_logger.debug(f"Respuesta cruda de IA de texto (intento {attempt + 1}): {ai_message_content}")

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
                        app_logger.info(f"Datos extraídos por IA de texto para '{original_filename}': {final_data}")
                        return final_data
                    except json.JSONDecodeError as json_err_inner:
                        app_logger.error(f"Error al decodificar JSON de la respuesta IA de texto (intento {attempt + 1}): {json_err_inner}. JSON string: '{json_str}'")
                else:
                    app_logger.warning(f"No se encontró JSON en la respuesta de IA de texto para '{original_filename}' (intento {attempt + 1}): {ai_message_content}")

            except APITimeoutError as e: # <--- Usar excepción importada directamente
                api_timeout_val = settings.API_TIMEOUT_SECONDS if hasattr(settings, 'API_TIMEOUT_SECONDS') else 'N/A'
                app_logger.warning(f"Timeout de {api_timeout_val}s con API de IA de texto para '{original_filename}' (intento {attempt + 1}): {e}")
                return None 

            except APIConnectionError as e: # <--- Usar excepción importada directamente
                app_logger.error(f"Error de conexión con API de IA de texto (intento {attempt + 1}): {e}")
            except RateLimitError as e: # <--- Usar excepción importada directamente
                app_logger.warning(f"Límite de tasa alcanzado con API de IA de texto (intento {attempt + 1}): {e}. Esperando antes de reintentar...")
                time.sleep(15 * (attempt + 1)) 
                continue 
            except APIStatusError as e: # <--- Usar excepción importada directamente
                app_logger.error(f"Error de estado de API de IA de texto (intento {attempt + 1}): Código={e.status_code}, Respuesta={e.response.text if e.response else 'N/A'}")
                if e.status_code == 401:
                    app_logger.error("Error de autenticación con OpenRouter. Verifica tu API Key.")
                    return None
            except Exception as e_general:
                 app_logger.error(f"Error inesperado durante la llamada a la API de IA de texto (intento {attempt + 1}): {e_general}", exc_info=True)
            
            if attempt < max_retries - 1:
                sleep_time = 3 * (attempt + 1)
                app_logger.info(f"Reintentando llamada a API de IA de texto en {sleep_time} segundos...")
                time.sleep(sleep_time)
            else:
                app_logger.error(f"Todos los {max_retries} intentos de API de IA de texto fallaron para '{original_filename}'.")
        
        return None

    def get_data_with_multimodal_ai(self, pil_image_obj: Image.Image, original_filename: str) -> Optional[Dict[str, str]]: # Image.Image aquí
        if not self.is_api_configured_and_client_valid() or not self.multimodal_model:
            app_logger.info("IA multimodal no configurada o modelo no especificado, omitiendo.")
            return None
        
        app_logger.warning(f"Función get_data_with_multimodal_ai para '{original_filename}' aún no completamente implementada/probada con API real.")
        try:
            buffered = BytesIO()
            pil_image_obj.save(buffered, format="PNG") # pil_image_obj es Image.Image
            img_str_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            image_data_url = f"data:image/png;base64,{img_str_base64}"
            
            # ... (resto de la lógica conceptual para multimodal) ...
        except Exception as e:
            app_logger.error(f"Error en get_data_with_multimodal_ai: {e}", exc_info=True)
        return None