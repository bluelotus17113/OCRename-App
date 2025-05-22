import easyocr
import re
import os 
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from typing import Optional, Tuple, Dict, Callable
import numpy as np
from PIL import Image

# Importar OpenCV si está disponible y habilitado para preprocesamiento
opencv_available = False
cv2 = None 
try:
    from config import settings
    enable_preprocessing_flag = False
    if hasattr(settings, 'ENABLE_IMAGE_PREPROCESSING'):
        enable_preprocessing_flag = settings.ENABLE_IMAGE_PREPROCESSING

    if enable_preprocessing_flag:
        import cv2
        opencv_available = True
except ImportError: 
    print("ADVERTENCIA (pdf_processor import): No se pudo importar 'config.settings' al verificar OpenCV.")
    settings = None 
except AttributeError: 
    print("ADVERTENCIA (pdf_processor import): 'ENABLE_IMAGE_PREPROCESSING' no encontrado en settings al verificar OpenCV.")


from utils.logger import get_app_logger
app_logger = get_app_logger()

class PDFProcessor:
    def __init__(self):
        self.reader = None
        try:
            ocr_langs = ['es'] 
            use_gpu = False
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
        # ... (sin cambios respecto a la versión anterior) ...
        app_logger.debug(f"Verificando si '{pdf_path}' es solo imagen.")
        try:
            reader = PdfReader(pdf_path)
            if reader.is_encrypted:
                try: reader.decrypt('')
                except:
                    app_logger.warning(f"PDF '{pdf_path}' encriptado. Asumiendo OCR.")
                    return True
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    app_logger.info(f"'{pdf_path}' (pág {page_idx+1}) tiene texto extraíble.")
                    return False
            app_logger.info(f"'{pdf_path}' es PDF de imagen o con poco texto.")
            return True
        except Exception as e:
            app_logger.warning(f"Error verificando PDF '{pdf_path}': {e}. Asumiendo OCR.")
            return True


    def _preprocess_full_page_image_for_ocr(self, image_np_rgb: np.ndarray) -> np.ndarray:
        # ... (sin cambios respecto a la versión anterior) ...
        global opencv_available, cv2
        enable_preprocessing = False
        if settings and hasattr(settings, 'ENABLE_IMAGE_PREPROCESSING'):
            enable_preprocessing = settings.ENABLE_IMAGE_PREPROCESSING
        if not (enable_preprocessing and opencv_available):
            return image_np_rgb 
        try:
            gray = cv2.cvtColor(image_np_rgb, cv2.COLOR_RGB2GRAY)
            return gray 
        except Exception as e_cv2:
            app_logger.error(f"Error preprocesando pág completa: {e_cv2}")
            return image_np_rgb

    def extract_text_from_pdf(self, pdf_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> Tuple[Optional[str], str]:
        # ... (sin cambios respecto a la versión anterior, incluyendo la lógica de guardado de debug logs) ...
        # --- ESTA FUNCIÓN ES LARGA, USA LA VERSIÓN COMPLETA DE LA RESPUESTA ANTERIOR ---
        app_logger.debug(f"ENTRANDO a extract_text_from_pdf para: {pdf_path}")
        debug_dir = ""
        try:
            project_root = os.getcwd(); debug_dir = os.path.join(project_root, "OCRename_Logs_Debug"); os.makedirs(debug_dir, exist_ok=True)
        except Exception as e_mkdir: app_logger.error(f"No se pudo crear dir de debug '{debug_dir}': {e_mkdir}"); debug_dir = ""
        if not self._is_pdf_image_only(pdf_path):
            try:
                app_logger.info(f"Intentando extracción directa para '{pdf_path}'")
                reader = PdfReader(pdf_path); direct_text_parts = []; num_pages = len(reader.pages)
                for i, page_obj in enumerate(reader.pages):
                    direct_text_parts.append(page_obj.extract_text())
                    if progress_callback: progress_callback(int(((i + 1) / num_pages) * 50))
                direct_text = "\n".join(filter(None, direct_text_parts)).strip()
                if direct_text:
                    app_logger.info(f"Texto extraído directamente de '{pdf_path}'.")
                    if progress_callback: progress_callback(100)
                    if debug_dir:
                        try:
                            base_name = os.path.basename(pdf_path).replace('.', '_'); fname = os.path.join(debug_dir, f"debug_direct_text_output_{base_name}.txt")
                            with open(fname, "w", encoding="utf-8") as f: f.write(f"--- TEXTO DIRECTO {pdf_path} ---\n{direct_text if direct_text else '(Vacio)'}")
                            app_logger.info(f"Texto directo guardado en: {fname}")
                        except Exception as e: app_logger.error(f"Error guardando debug directo: {e}")
                    return direct_text, "directo"
            except Exception as e: app_logger.warning(f"Extracción directa falló para '{pdf_path}': {e}. Intentando OCR.")
        if not self.reader: app_logger.error("EasyOCR no inicializado."); return None, "fallido_ocr_no_init"
        full_ocr_text = []; app_logger.debug(f"Iniciando OCR para {pdf_path}")
        try:
            pop_path = settings.POPPLER_PATH if settings and hasattr(settings, 'POPPLER_PATH') else None
            images = convert_from_path(pdf_path, poppler_path=pop_path); app_logger.debug(f"PDF '{pdf_path}' -> {len(images)} imágenes.")
            num_images = len(images)
            for i, pil_img in enumerate(images):
                p_num = i + 1; app_logger.debug(f"OCR pág {p_num}/{num_images} de '{pdf_path}'")
                img_np = np.array(pil_img.convert('RGB')); img_ocr = self._preprocess_full_page_image_for_ocr(img_np)
                app_logger.debug(f"Img OCR pág {p_num}: tipo={type(img_ocr)}, shape={img_ocr.shape if isinstance(img_ocr, np.ndarray) else 'N/A'}")
                res_page = self.reader.readtext(img_ocr, detail=0, paragraph=True); app_logger.debug(f"Res OCR pág {p_num}: {res_page}")
                if res_page: full_ocr_text.extend(res_page)
                prog_ocr = 50 + int(((i + 1) / num_images) * 50);
                if progress_callback: progress_callback(prog_ocr)
            final_text = "\n".join(full_ocr_text).strip(); app_logger.debug(f"full_ocr_text ANTES join para '{pdf_path}': {full_ocr_text}")
            gpu_stat = str(settings.OCR_GPU) if settings and hasattr(settings, 'OCR_GPU') else "N/A"
            app_logger.info(f"--- INICIO TEXTO OCR (GPU:{gpu_stat}) PARA {os.path.basename(pdf_path)} ---")
            # (Lógica de logging de final_text omitida por brevedad pero debe estar)
            app_logger.info(f"--- FIN TEXTO OCR (GPU:{gpu_stat}) PARA {os.path.basename(pdf_path)} ---")
            if debug_dir:
                try:
                    base_name = os.path.basename(pdf_path).replace('.', '_'); fname = os.path.join(debug_dir, f"debug_ocr_output_{base_name}.txt")
                    with open(fname, "w", encoding="utf-8") as f: f.write(f"--- TEXTO OCR (GPU:{gpu_stat}) {pdf_path} ---\n{final_text if final_text else '(Vacio)'}")
                    app_logger.info(f"OCR guardado en: {fname}")
                except Exception as e: app_logger.error(f"Error guardando debug OCR: {e}")
            if final_text: return final_text, "ocr_pagina_completa"
            else: app_logger.warning(f"OCR pág completa no produjo texto para '{pdf_path}'."); return None, "ocr_pagina_vacia"
        except Exception as e:
            app_logger.error(f"EXCEPCIÓN en OCR pág completa de '{pdf_path}': {e}", exc_info=True)
            if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower(): app_logger.error("Error Poppler...")
            return None, "fallido_ocr_excepcion"


    def _extract_age_from_text(self, text_content: str) -> Optional[int]:
        # ... (sin cambios respecto a la versión anterior) ...
        if not text_content: return None
        age_pattern = re.compile(r"\b(?:Edad\s*[:\-]?\s*)?(\d{1,3})\s*A[ÑN]OS\b", re.IGNORECASE)
        match = age_pattern.search(text_content)
        if match:
            try:
                age = int(match.group(1)); app_logger.debug(f"Edad extraída: {age} años."); return age
            except ValueError: app_logger.warning(f"Patrón edad, pero '{match.group(1)}' no es número.")
        else:
            age_simple_match = re.search(r"\b(\d{1,3})\b\s*A[ÑN]OS", text_content, re.IGNORECASE)
            if age_simple_match:
                context_start = max(0, age_simple_match.start() - 30); context_window = text_content[context_start : age_simple_match.start()]
                if "EDAD" in context_window.upper():
                    try:
                        age = int(age_simple_match.group(1)); app_logger.debug(f"Edad (simple c/contexto) extraída: {age} años."); return age
                    except ValueError: pass
            app_logger.debug("No se pudo extraer la edad.")
        return None

    def extract_printed_data_from_text(self, text_content: str) -> Dict[str, Optional[str]]:
        data = {"id_type": None, "id_number": None, "acta_no": None}
        if not text_content:
            app_logger.debug("extract_printed_data_from_text: text_content vacío.")
            return data

        app_logger.debug(f"extract_printed_data_from_text: Iniciando Regex.")

        # Tipos de ID permitidos para renombrar (EXCLUYE NIT explícitamente de la captura de tipo)
        allowed_id_types_regex_capture = r"(CC|TI|CE|PA|RC)" # Cédula Ciudadanía, Tarjeta Identidad, Cédula Extranjería, Pasaporte, Registro Civil

        # --- Extracción de id_number e id_type ---
        # Prioridad: Buscar el número y luego asociar un tipo permitido, o inferir.

        # Patrón 1: "Identificación: [TIPO_PERMITIDO (opcional)] NUMERO"
        # El grupo del tipo es opcional. El número es el grupo principal.
        id_explicit_match = re.search(rf"(?i)Identificaci[oó]n\s*[:\-]?\s*(?:({allowed_id_types_regex_capture})\s*[:\-]?\s*)?(\d{{6,12}})\b", text_content)
        if id_explicit_match:
            id_num_candidate = id_explicit_match.group(2) # Grupo del número
            type_candidate = id_explicit_match.group(1)   # Grupo del tipo (puede ser None)
            
            if id_num_candidate and id_num_candidate.isdigit(): # Asegurarse de que el número sea solo dígitos
                data["id_number"] = id_num_candidate
                if type_candidate:
                    data["id_type"] = type_candidate.upper()
                app_logger.debug(f"Regex ID Matched (P1: 'Identificacion'): TIPO={data['id_type']}, NUM={data['id_number']}")

        # Patrón 2: "[TIPO_PERMITIDO] NUMERO" (sin "Identificación" necesariamente)
        # Solo si no se encontró id_number aún.
        if not data["id_number"]:
            id_type_and_num_match = re.search(rf"(?i)\b({allowed_id_types_regex_capture})\s*[:\-]?\s*(\d{{6,12}})\b", text_content)
            if id_type_and_num_match:
                id_num_candidate = id_type_and_num_match.group(2)
                if id_num_candidate.isdigit():
                    data["id_type"] = id_type_and_num_match.group(1).upper()
                    data["id_number"] = id_num_candidate
                    app_logger.debug(f"Regex ID Matched (P2: tipo + número): TIPO={data['id_type']}, NUM={data['id_number']}")
        
        # Patrón 3: Número solitario (solo dígitos) con contexto de "Identificación" o similar.
        # Solo si no se encontró id_number aún.
        if not data["id_number"]:
            for m in re.finditer(r"\b(\d{6,10})\b", text_content): # Busca números puros
                num_candidate = m.group(1)
                context_start = max(0, m.start() - 70)
                context_end = min(len(text_content), m.end() + 70)
                context_window = text_content[context_start:context_end]
                
                # Contexto para confirmar que es un id_number
                if re.search(r"Identificaci[oó]n|DOCUMENTO|No\.\s*Doc|C[.\s]*C\b|IDENTIFICACION\s*No", context_window, re.IGNORECASE):
                    if num_candidate.isdigit(): # Doble chequeo
                        data["id_number"] = num_candidate
                        app_logger.debug(f"Regex ID Number Matched (P3: número solitario con contexto): NUM={data['id_number']}")
                        # Intentar encontrar tipo permitido en el mismo contexto si no se encontró antes
                        if not data["id_type"]: 
                            type_match_context_solo = re.search(rf"\b({allowed_id_types_regex_capture})\b", context_window, re.IGNORECASE)
                            if type_match_context_solo:
                                data["id_type"] = type_match_context_solo.group(1).upper()
                                app_logger.debug(f"Regex ID Type Matched (contexto de P3): TIPO={data['id_type']}")
                        break # Tomar la primera coincidencia válida

        # --- Lógica de Inferencia y Default para id_type (SOLO SI HAY id_number) ---
        if data["id_number"]: 
            if not data["id_type"]: # Si id_number existe, pero id_type (permitido) no fue capturado
                age = self._extract_age_from_text(text_content)
                if age is not None:
                    if age >= 18: data["id_type"] = "CC"
                    elif age < 5: data["id_type"] = "RC"
                    else: data["id_type"] = "TI" 
                    app_logger.info(f"Se infirió id_type='{data['id_type']}' basado en la edad: {age} años.")
                else:
                    # Si no hay edad para inferir Y no se encontró un tipo permitido, default a "CC"
                    app_logger.warning("id_type no encontrado por Regex y no se pudo inferir por edad. Asignando 'CC' por defecto ya que id_number existe.")
                    data["id_type"] = "CC"
        else: 
            app_logger.warning("No se encontró id_number. No se puede inferir id_type ni renombrar efectivamente.")
            data["id_type"] = None # Asegurar que id_type sea None si no hay id_number para que falle el renombrado

        # --- Extracción de acta_no ---
        acta_patterns = [
            re.compile(r"(?i)Acta\s*de\s*Entrega\s*No\.?\s*(\d+)"),
            re.compile(r"(?i)F[oó]rmula\s*M[eé]dica\s*Nro\.?\s*(\d+)"),
            re.compile(r"(?i)(?:ORDEN|AUTORIZACION)\s*N[°oº\.]*[:\s]*(\d+)"),
            re.compile(r"(?i)(?:Entrega\s*No|Nro|RECIBO)\.?\s*(\d+)")
        ]
        for i, pattern in enumerate(acta_patterns):
            match = pattern.search(text_content)
            if match:
                data["acta_no"] = match.group(1)
                app_logger.debug(f"Regex Acta Matched (patrón {i+1}): ACTA={data['acta_no']}")
                break 
        if not data["acta_no"]: app_logger.debug("Regex Acta: Ningún patrón de acta coincidió.")

        # Logging final
        if not data.get("id_number"): app_logger.warning(f"Extracción Regex final: FALTA ID_NUMBER. Datos: {data}")
        elif not data.get("id_type"): app_logger.warning(f"Extracción Regex final: FALTA ID_TYPE (id_number existe). Datos: {data}") # Debería ser CC si id_number existe
        elif not data.get("acta_no"): app_logger.warning(f"Extracción Regex final: FALTA ACTA_NO. Datos: {data}")
        else: app_logger.info(f"Extracción Regex de datos impresos considerada completa para renombrar: {data}")
        return data

    def _preprocess_roi_for_handwritten_acta(self, roi_image_np: np.ndarray) -> np.ndarray:
        # ... (sin cambios) ...
        global opencv_available, cv2
        if not opencv_available: app_logger.warning("OpenCV no disponible, no se puede preprocesar ROI HTR."); return roi_image_np
        app_logger.debug("Preprocesando ROI para número manuscrito...")
        try:
            if len(roi_image_np.shape) == 3: gray_roi = cv2.cvtColor(roi_image_np, cv2.COLOR_RGB2GRAY)
            else: gray_roi = roi_image_np.copy()
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)); contrast_roi = clahe.apply(gray_roi)
            _, binary_roi = cv2.threshold(contrast_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU) 
            app_logger.debug("Preprocesamiento ROI HTR completado."); return binary_roi
        except Exception as e: app_logger.error(f"Error preprocesando ROI HTR: {e}", exc_info=True); return roi_image_np

    def extract_handwritten_acta_number(self, first_page_pil_image: Image.Image) -> Optional[str]:
        # ... (sin cambios) ...
        if not self.reader: app_logger.error("EasyOCR no inicializado para HTR."); return None
        app_logger.info("Intentando extraer acta manuscrita...")
        try:
            img_np_rgb = np.array(first_page_pil_image.convert('RGB')); alto, ancho, _ = img_np_rgb.shape
            roi_y_s, roi_y_e = 0, int(alto * 0.18); roi_x_s, roi_x_e = int(ancho * 0.70), ancho
            roi_np = img_np_rgb[roi_y_s:roi_y_e, roi_x_s:roi_x_e]
            if roi_np.size == 0: app_logger.warning("ROI acta manuscrita vacía."); return None
            proc_roi = self._preprocess_roi_for_handwritten_acta(roi_np)
            ocr_res = self.reader.readtext(proc_roi, detail=0, paragraph=False, allowlist='0123456789')
            if ocr_res:
                num_digits = "".join(filter(str.isdigit, "".join(ocr_res).replace(" ", "").strip()))
                app_logger.info(f"ROI HTR: '{num_digits}'")
                if num_digits and 4 <= len(num_digits) <= 6: return num_digits
                else: app_logger.warning(f"ROI HTR '{num_digits}' longitud inválida.")
            else: app_logger.warning("EasyOCR no encontró números en ROI HTR.")
        except Exception as e: app_logger.error(f"Error extrayendo acta manuscrita: {e}", exc_info=True)
        return None