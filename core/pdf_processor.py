import easyocr
import re
import os # Para os.path.basename en el nombre del archivo de depuración
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from typing import Optional, Tuple, Dict, Callable
import numpy as np
from PIL import Image
# import time # Descomenta si usas time.time() en nombres de archivo de depuración que no sean los de os.urandom

# Importar OpenCV si está disponible y habilitado para preprocesamiento
opencv_available = False # Inicializar
cv2 = None # Inicializar para evitar NameError si no se importa
try:
    from config import settings
    # Verificar si el atributo existe antes de intentar acceder a él
    enable_preprocessing_flag = False
    if hasattr(settings, 'ENABLE_IMAGE_PREPROCESSING'):
        enable_preprocessing_flag = settings.ENABLE_IMAGE_PREPROCESSING

    if enable_preprocessing_flag:
        import cv2 # Importar cv2 aquí si está habilitado
        opencv_available = True
except ImportError: 
    # Esto podría pasar si config o settings no se pueden importar, aunque es menos probable aquí
    app_logger_temp = get_app_logger() # Obtener logger para este mensaje
    app_logger_temp.warning("No se pudo importar 'config.settings' en pdf_processor.py al verificar OpenCV.")
    settings = None # Para que el resto del código no falle si settings es None
except AttributeError: 
    # Esto podría pasar si settings se importó pero no tiene ENABLE_IMAGE_PREPROCESSING
    app_logger_temp = get_app_logger()
    app_logger_temp.warning("'ENABLE_IMAGE_PREPROCESSING' no encontrado en settings al verificar OpenCV.")


from utils.logger import get_app_logger
app_logger = get_app_logger()

class PDFProcessor:
    def __init__(self):
        self.reader = None
        try:
            ocr_langs = ['es'] 
            use_gpu = False
            # Verificar si settings y sus atributos existen antes de usarlos
            if settings:
                if hasattr(settings, 'OCR_LANGUAGES'):
                    ocr_langs = settings.OCR_LANGUAGES
                if hasattr(settings, 'OCR_GPU'):
                    use_gpu = settings.OCR_GPU
            
            app_logger.info(f"Inicializando EasyOCR con idiomas: {ocr_langs}, GPU: {use_gpu}")
            self.reader = easyocr.Reader(ocr_langs, gpu=use_gpu)
            app_logger.info("EasyOCR inicializado correctamente.")

            enable_preprocessing_check = False
            if settings and hasattr(settings, 'ENABLE_IMAGE_PREPROCESSING'):
                enable_preprocessing_check = settings.ENABLE_IMAGE_PREPROCESSING

            if enable_preprocessing_check and not opencv_available:
                app_logger.warning("Preprocesamiento de imágenes HABILITADO en settings, pero OpenCV (cv2) no está disponible/instalado. El preprocesamiento se omitirá.")
        
        except Exception as e:
            app_logger.error(f"Error crítico al inicializar EasyOCR: {e}", exc_info=True)

    def _is_pdf_image_only(self, pdf_path: str) -> bool:
        """Intenta determinar si un PDF es principalmente de imágenes o tiene texto extraíble."""
        app_logger.debug(f"Verificando si '{pdf_path}' es solo imagen.")
        try:
            reader = PdfReader(pdf_path)
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except:
                    app_logger.warning(f"PDF '{pdf_path}' encriptado y no se pudo desencriptar. Asumiendo OCR.")
                    return True

            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 50: 
                    app_logger.info(f"'{pdf_path}' (página {page_idx+1}) parece tener texto extraíble directamente.")
                    return False
            app_logger.info(f"'{pdf_path}' parece ser PDF de solo imágenes o con poco texto extraíble tras revisar todas las páginas.")
            return True
        except Exception as e:
            app_logger.warning(f"Error al verificar tipo de PDF '{pdf_path}': {e}. Asumiendo OCR necesario.")
            return True

    def _preprocess_full_page_image_for_ocr(self, image_np_rgb: np.ndarray) -> np.ndarray:
        """Preprocesamiento opcional para OCR de página completa."""
        global opencv_available, cv2 # Para asegurar que usamos las variables correctas
        
        enable_preprocessing = False
        if settings and hasattr(settings, 'ENABLE_IMAGE_PREPROCESSING'):
            enable_preprocessing = settings.ENABLE_IMAGE_PREPROCESSING

        if not (enable_preprocessing and opencv_available):
            app_logger.debug("Preprocesamiento de página completa deshabilitado o OpenCV no disponible.")
            return image_np_rgb 

        app_logger.debug("Aplicando preprocesamiento de página completa...")
        try:
            gray = cv2.cvtColor(image_np_rgb, cv2.COLOR_RGB2GRAY)
            app_logger.debug("Preprocesamiento de página completa: Convertido a escala de grises.")
            # Aquí podrías añadir más pasos si lo deseas, ej. umbral adaptativo suave
            return gray 
        except Exception as e_cv2:
            app_logger.error(f"Error durante el preprocesamiento de página completa: {e_cv2}")
            return image_np_rgb

    def extract_text_from_pdf(self, pdf_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> Tuple[Optional[str], str]:
        app_logger.debug(f"ENTRANDO a extract_text_from_pdf para: {pdf_path}")

        if not self._is_pdf_image_only(pdf_path): # Intento de extracción directa primero
            try:
                app_logger.info(f"Intentando extracción directa de texto para '{pdf_path}'")
                reader = PdfReader(pdf_path)
                direct_text_parts = []
                num_pages = len(reader.pages)
                for i, page_obj in enumerate(reader.pages):
                    direct_text_parts.append(page_obj.extract_text())
                    if progress_callback:
                        progress_callback(int(((i + 1) / num_pages) * 50)) # 0-50% para esta fase
                
                direct_text = "\n".join(filter(None, direct_text_parts)).strip()
                if direct_text:
                    app_logger.info(f"Texto extraído directamente de '{pdf_path}'.")
                    if progress_callback: progress_callback(100) # Asegurar 100% si termina aquí
                    
                    try:
                        debug_filename_direct = f"debug_direct_text_output_{os.path.basename(pdf_path).replace('.', '_')}.txt"
                        with open(debug_filename_direct, "w", encoding="utf-8") as f_out_direct:
                            f_out_direct.write(f"--- TEXTO DIRECTO PARA {pdf_path} ---\n")
                            f_out_direct.write(direct_text)
                        app_logger.info(f"Texto directo también guardado en: {debug_filename_direct}")
                    except Exception as e_write_direct:
                        app_logger.error(f"No se pudo guardar el archivo de depuración de texto directo: {e_write_direct}")
                    return direct_text, "directo"
            except Exception as e_direct:
                app_logger.warning(f"Extracción directa falló para '{pdf_path}': {e_direct}. Intentando OCR.")
        
        if not self.reader:
            app_logger.error("Motor EasyOCR no inicializado en extract_text_from_pdf. No se puede realizar OCR.")
            return None, "fallido_ocr_no_init"
        
        full_ocr_text = []
        app_logger.debug(f"Iniciando proceso OCR para {pdf_path}")
        try:
            poppler_path_setting = None
            if settings and hasattr(settings, 'POPPLER_PATH'):
                 poppler_path_setting = settings.POPPLER_PATH

            images = convert_from_path(pdf_path, poppler_path=poppler_path_setting) 
            app_logger.debug(f"PDF '{pdf_path}' convertido a {len(images)} imágenes.")
            
            num_images = len(images)
            for i, pil_image_obj in enumerate(images):
                page_num_log = i + 1
                app_logger.debug(f"Procesando OCR para página {page_num_log}/{num_images} de '{pdf_path}'")
                image_np_rgb = np.array(pil_image_obj.convert('RGB'))
                
                image_to_ocr = self._preprocess_full_page_image_for_ocr(image_np_rgb)
                
                app_logger.debug(f"Imagen para OCR (página {page_num_log}): tipo={type(image_to_ocr)}, shape={image_to_ocr.shape if isinstance(image_to_ocr, np.ndarray) else 'N/A'}, dtype={image_to_ocr.dtype if isinstance(image_to_ocr, np.ndarray) else 'N/A'}")

                ocr_result_page = self.reader.readtext(image_to_ocr, detail=0, paragraph=True)
                
                app_logger.debug(f"Resultado OCR para página {page_num_log} (lista de strings): {ocr_result_page}")
                
                if ocr_result_page: 
                    full_ocr_text.extend(ocr_result_page)
                
                # Calcular progreso para la fase de OCR (50-100%)
                current_progress_ocr = 50 + int(((i + 1) / num_images) * 50) 
                if progress_callback:
                    progress_callback(current_progress_ocr) 
            
            app_logger.debug(f"Contenido de full_ocr_text ANTES del join para '{pdf_path}': {full_ocr_text}")
            final_text = "\n".join(full_ocr_text).strip()
            
            ocr_gpu_status = "N/A"
            if settings and hasattr(settings, 'OCR_GPU'):
                ocr_gpu_status = str(settings.OCR_GPU)

            app_logger.info(f"--- INICIO TEXTO OCR (GPU:{ocr_gpu_status}) PARA {os.path.basename(pdf_path)} ---")
            if final_text:
                lines = final_text.splitlines()
                max_lines_to_log = 10
                if len(lines) > 2 * max_lines_to_log:
                    for line_num, line in enumerate(lines[:max_lines_to_log]):
                        app_logger.info(f"[OCR Line {line_num+1}]: {line}")
                    app_logger.info(f"... (texto intermedio omitido, total {len(lines)} líneas) ...")
                    for line_num, line in enumerate(lines[-max_lines_to_log:]):
                        app_logger.info(f"[OCR Line {len(lines) - max_lines_to_log + line_num + 1}]: {line}")
                else:
                    for line_num, line in enumerate(lines):
                        app_logger.info(f"[OCR Line {line_num+1}]: {line}")
            else:
                app_logger.info("[OCR Line]: (Texto vacío de OCR)")
            app_logger.info(f"--- FIN TEXTO OCR (GPU:{ocr_gpu_status}) PARA {os.path.basename(pdf_path)} ---")
            
            try:
                base_name = os.path.basename(pdf_path).replace('.', '_')
                debug_filename_ocr = f"debug_ocr_output_{base_name}.txt" 
                with open(debug_filename_ocr, "w", encoding="utf-8") as f_out_ocr:
                    f_out_ocr.write(f"--- TEXTO OCR (GPU: {ocr_gpu_status}) PARA {pdf_path} ---\n")
                    f_out_ocr.write(final_text if final_text else "(Texto vacío de OCR)")
                app_logger.info(f"Salida de OCR también guardada en: {debug_filename_ocr}")
            except Exception as e_write_ocr:
                app_logger.error(f"No se pudo guardar el archivo de depuración de OCR: {e_write_ocr}")
            
            if final_text:
                return final_text, "ocr_pagina_completa"
            else:
                app_logger.warning(f"OCR de página completa no produjo texto (final_text vacío) para '{pdf_path}'.")
                return None, "ocr_pagina_vacia"

        except Exception as e_ocr:
            app_logger.error(f"EXCEPCIÓN durante el OCR de página completa de '{pdf_path}': {e_ocr}", exc_info=True)
            if "poppler" in str(e_ocr).lower() or "pdftoppm" in str(e_ocr).lower():
                app_logger.error(
                    "Error relacionado con Poppler (pdftoppm). "
                    "Asegúrate de que Poppler esté instalado y su carpeta 'bin' esté en tu variable de entorno PATH. "
                    "O especifica 'POPPLER_PATH' en config/settings.py."
                )
            return None, "fallido_ocr_excepcion"

    def extract_printed_data_from_text(self, text_content: str) -> Dict[str, Optional[str]]:
        """Extrae datos impresos (ID, Nombre, Acta si está impresa) usando Regex."""
        data = {"id_type": None, "id_number": None, "acta_no": None}
        if not text_content:
            app_logger.debug("extract_printed_data_from_text: text_content está vacío.")
            return data

        app_logger.debug(f"extract_printed_data_from_text: Iniciando búsqueda Regex en texto de {len(text_content)} caracteres.")

        # Regex para Identificacion CC XXXXXXX
        id_pattern = re.compile(r"(?i)Identificaci[oó]n\s*([A-Z]{2,3})\s*(\d{6,12})")
        id_match = id_pattern.search(text_content)
        if id_match:
            data["id_type"] = id_match.group(1).upper()
            data["id_number"] = id_match.group(2)
            app_logger.debug(f"Regex ID Matched (patrón 1): TIPO={data['id_type']}, NUM={data['id_number']}")
        else:
            simple_id_pattern = re.compile(r"(?i)\b(CC|TI|CE|NIT|PA)\s*(\d{6,12})\b")
            simple_id_match = simple_id_pattern.search(text_content)
            if simple_id_match:
                context_start = max(0, simple_id_match.start() - 70)
                context_end = min(len(text_content), simple_id_match.end() + 30)
                context_window = text_content[context_start:context_end]
                if re.search(r"Identificaci[oó]n|DOCUMENTO|No\.\s*Doc", context_window, re.IGNORECASE):
                    data["id_type"] = simple_id_match.group(1).upper()
                    data["id_number"] = simple_id_match.group(2)
                    app_logger.debug(f"Regex ID Matched (patrón 2 - simple con contexto): TIPO={data['id_type']}, NUM={data['id_number']}")
                else:
                    app_logger.debug(f"Regex ID (patrón 2 - simple) encontró {simple_id_match.groups()} pero faltó contexto 'Identificacion'.")
            else:
                app_logger.debug("Regex ID: Ningún patrón coincidió.")


        acta_pattern_1 = re.compile(r"(?i)Acta\s*de\s*Entrega\s*No\.?\s*(\d+)")
        acta_match_1 = acta_pattern_1.search(text_content)
        if acta_match_1:
            data["acta_no"] = acta_match_1.group(1)
            app_logger.debug(f"Regex Acta Matched (patrón 1): ACTA={data['acta_no']}")
        else:
            acta_pattern_2 = re.compile(r"(?i)F[oó]rmula\s*M[eé]dica\s*Nro\.?\s*(\d+)")
            acta_match_2 = acta_pattern_2.search(text_content)
            if acta_match_2:
                 data["acta_no"] = acta_match_2.group(1)
                 app_logger.debug(f"Regex Acta Matched (patrón 2 - formula): ACTA={data['acta_no']}")
            else:
                simple_acta_pattern = re.compile(r"(?i)(?:Entrega\s*No|Nro|Orden)\.?\s*(\d+)")
                simple_acta_match = simple_acta_pattern.search(text_content)
                if simple_acta_match:
                    data["acta_no"] = simple_acta_match.group(1)
                    app_logger.debug(f"Regex Acta Matched (patrón 3 - simple): ACTA={data['acta_no']}")
                else:
                    app_logger.debug("Regex Acta: Ningún patrón coincidió.")


        if not all(value is not None for value in data.values()):
            app_logger.warning(f"Extracción Regex de datos impresos incompleta: {data}")
        else:
            app_logger.info(f"Extracción Regex de datos impresos completa: {data}")
        return data

    def _preprocess_roi_for_handwritten_acta(self, roi_image_np: np.ndarray) -> np.ndarray:
        """Preprocesamiento específico para la ROI del número de acta manuscrito."""
        global opencv_available, cv2 # Asegurar que usamos las correctas

        if not opencv_available:
            app_logger.warning("OpenCV no disponible, no se puede preprocesar ROI para HTR.")
            return roi_image_np

        app_logger.debug("Preprocesando ROI para número manuscrito...")
        try:
            if len(roi_image_np.shape) == 3:
                gray_roi = cv2.cvtColor(roi_image_np, cv2.COLOR_RGB2GRAY)
            else:
                gray_roi = roi_image_np.copy()

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)) 
            contrast_roi = clahe.apply(gray_roi)
            
            _, binary_roi = cv2.threshold(contrast_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU) 
            
            app_logger.debug("Preprocesamiento de ROI para número manuscrito completado.")
            return binary_roi
        
        except Exception as e_cv2_roi:
            app_logger.error(f"Error durante el preprocesamiento de ROI para HTR: {e_cv2_roi}", exc_info=True)
            return roi_image_np

    def extract_handwritten_acta_number(self, first_page_pil_image: Image.Image) -> Optional[str]:
        """Extrae el número de acta manuscrito de la esquina superior de una imagen PIL."""
        if not self.reader:
            app_logger.error("EasyOCR no inicializado, no se puede extraer número manuscrito.")
            return None
        
        app_logger.info("Intentando extraer número de acta manuscrito...")
        try:
            image_np_rgb = np.array(first_page_pil_image.convert('RGB'))
            alto, ancho, _ = image_np_rgb.shape

            # --- AJUSTA ESTAS COORDENADAS ROI ---
            roi_y_start = 0
            roi_y_end = int(alto * 0.18)
            roi_x_start = int(ancho * 0.75) 
            roi_x_end = ancho
            # --------------------------------
            
            roi_np_rgb = image_np_rgb[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

            if roi_np_rgb.size == 0:
                app_logger.warning("ROI para número manuscrito está vacía o mal definida.")
                return None
            
            # if opencv_available: # Descomenta para guardar imagen de depuración
            #    unique_id = os.urandom(4).hex()
            #    cv2.imwrite(f"debug_roi_acta_original_{unique_id}.png", cv2.cvtColor(roi_np_rgb, cv2.COLOR_RGB2BGR))

            processed_roi_np = self._preprocess_roi_for_handwritten_acta(roi_np_rgb)

            # if opencv_available: # Descomenta para guardar imagen de depuración
            #    unique_id_proc = os.urandom(4).hex()
            #    cv2.imwrite(f"debug_roi_acta_procesada_{unique_id_proc}.png", processed_roi_np)

            ocr_results = self.reader.readtext(
                processed_roi_np, 
                detail=0, 
                paragraph=False, 
                allowlist='0123456789',
            )
            
            if ocr_results:
                extracted_number = "".join(ocr_results).replace(" ", "").strip()
                extracted_number_digits_only = "".join(filter(str.isdigit, extracted_number))

                app_logger.info(f"Número manuscrito potencial extraído de ROI: '{extracted_number_digits_only}' (original de OCR: '{extracted_number}')")
                
                if extracted_number_digits_only and 4 <= len(extracted_number_digits_only) <= 7:
                    return extracted_number_digits_only
                else:
                    app_logger.warning(f"Extracción de ROI '{extracted_number_digits_only}' no parece un número de acta válido.")
            else:
                app_logger.warning("EasyOCR no encontró texto numérico en la ROI del número manuscrito.")
                
        except Exception as e:
            app_logger.error(f"Error extrayendo número de acta manuscrito: {e}", exc_info=True)
        return None