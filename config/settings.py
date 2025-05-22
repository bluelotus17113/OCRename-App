import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- API Keys ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- Modelos de IA (OpenRouter) ---

DEEPSEEK_TEXT_MODEL = "deepseek/deepseek-r1:free" # Modelo principal para extracción basada en texto
LLAMA32_VISION_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free" # 

# (Opcional) Modelo multimodal si decides implementarlo
MULTIMODAL_MODEL_NAME = "opengvlab/internvl3-14b:free" # O None si no se usa
ENABLE_MULTIMODAL_FALLBACK = False # Cambia a True si implementas y quieres usar el fallback multimodal

# --- Configuraciones de OCR (EasyOCR) ---
OCR_LANGUAGES = ['es']  # Lista de idiomas para EasyOCR
OCR_GPU = True          # True para intentar usar GPU, False para forzar CPU

# (Opcional) Habilitar preprocesamiento de imágenes con OpenCV
ENABLE_IMAGE_PREPROCESSING = True # True para habilitar, False para deshabilitar
# Parámetros de preprocesamiento (solo se usan si ENABLE_IMAGE_PREPROCESSING = True y OpenCV está instalado)
# Estos son ejemplos, ajústalos según tus necesidades de preprocesamiento
PREPROCESSING_NOISE_REDUCTION_METHOD = "none"       # "none", "gaussian", "median"
PREPROCESSING_NOISE_KERNEL_SIZE = 3                 # Tamaño del kernel para reducción de ruido (impar)
PREPROCESSING_THRESHOLD_METHOD = "adaptive_mean"    # "none", "global", "otsu", "adaptive_mean", "adaptive_gaussian"
PREPROCESSING_GLOBAL_THRESHOLD_VALUE = 127          # Para umbral global (0-255)
PREPROCESSING_ADAPTIVE_BLOCK_SIZE = 15              # Para umbral adaptativo (impar, ej. 11, 15, 21)
PREPROCESSING_ADAPTIVE_C_VALUE = 5                  # Constante C para umbral adaptativo (ej. 2, 5, 7)
PREPROCESSING_THRESHOLD_INVERT = False              # False para cv2.THRESH_BINARY, True para cv2.THRESH_BINARY_INV

# --- Configuraciones de FileManager ---
OUTPUT_BASE_DIR = "OCRename_Resultados"
RENAMED_SUBDIR = "Archivos_Renombrados"
FAILED_SUBDIR = "Archivos_Fallidos"
FILENAME_PLACEHOLDER = "DESCONOCIDO" # Placeholder para campos None en el nombre de archivo

# --- Configuraciones de Logging ---
LOG_FILE_NAME = "ocrename_activity.log"
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# --- Configuraciones de API (para OpenRouter) ---
API_MAX_RETRIES = 1       # Número de reintentos DESPUÉS del primer intento (total 1+1=2 intentos si es 1).
                          # Si es 0, solo 1 intento en total. Para tu caso de timeout rápido, 0 o 1 es adecuado.
API_TIMEOUT_SECONDS = 10  # Timeout en segundos para la respuesta de la API.

# --- (Opcional) Ruta a Poppler ---
# Si Poppler no está en el PATH del sistema, descomenta y ajusta la siguiente línea.
# Úsala con precaución, lo ideal es que Poppler esté en el PATH.
# POPPLER_PATH = r"C:\ruta\completa\a\tu\carpeta_poppler\bin" 
POPPLER_PATH = None # Déjalo como None si Poppler está en el PATH del sistema.