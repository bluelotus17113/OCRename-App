import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Modelos de IA (DeepSeek vía OpenRouter)
# Puedes encontrar los identificadores exactos en la documentación de OpenRouter
# Ejemplo: "deepseek/deepseek-chat" o "deepseek/deepseek-coder"
DEEPSEEK_CHAT_MODEL = "deepseek/deepseek-chat" # Modelo general bueno para extracción
AI_MODEL_TO_USE = DEEPSEEK_CHAT_MODEL

# Configuraciones de OCR (EasyOCR)
OCR_LANGUAGES = ['es']  # Lista de idiomas para EasyOCR (español)
OCR_GPU = False         # Usar GPU para EasyOCR (True/False). Requiere configuración de CUDA.

# Configuraciones de FileManager
OUTPUT_BASE_DIR = "OCRename_Resultados" # <--- VARIABLE NECESARIA
RENAMED_SUBDIR = "Archivos_Renombrados"
FAILED_SUBDIR = "Archivos_Fallidos"

# Configuraciones de Logging
LOG_FILE_NAME = "ocrename_activity.log"
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Configuraciones de API
API_MAX_RETRIES = 2
API_TIMEOUT_SECONDS = 30 # <--- VARIABLE NECESARIA

# ... (otras configuraciones) ...

# Configuraciones de OCR (EasyOCR)
OCR_LANGUAGES = ['es']
OCR_GPU = True
ENABLE_IMAGE_PREPROCESSING = True # O False para desactivar el preprocesamiento

# ... (resto de las configuraciones) ...