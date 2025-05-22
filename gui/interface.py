import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import logging
from typing import List, Dict, Optional

from PIL import Image, ImageTk # Para la vista previa de imagen
from pdf2image import convert_from_path # Para obtener la imagen para vista previa y HTR/Visión

from utils.logger import get_app_logger
from core.pdf_processor import PDFProcessor
from core.ai_integration import AIIntegrator
from core.file_manager import FileManager
from config import settings

app_logger = get_app_logger()

class AppGUI:
    def __init__(self, root_tk: tk.Tk):
        self.root = root_tk
        self.root.title("OCRename v0.3 - Vista Previa y Selector")
        self.root.geometry("1100x750") # Más ancho para la vista previa

        self.pdf_processor: Optional[PDFProcessor] = None
        self.ai_integrator = AIIntegrator()
        self.file_manager = FileManager()

        self.selected_files: List[str] = []
        self.is_processing = False

        # Para la vista previa de imagen
        self.current_preview_pil_image: Optional[Image.Image] = None
        self.current_preview_tk_image: Optional[ImageTk.PhotoImage] = None

        self._setup_ui()
        self._initialize_ocr_engine_async()

    def _initialize_ocr_engine_async(self):
        # ... (sin cambios desde la última versión) ...
        self.status_var.set("Inicializando motor OCR (EasyOCR)... Esto puede tardar unos segundos.")
        self.root.update_idletasks()
        
        def init_task():
            try:
                self.pdf_processor = PDFProcessor()
                if self.pdf_processor and self.pdf_processor.reader:
                    self.status_var.set("Motor OCR listo. Seleccione archivos y tipo de documento.")
                    app_logger.info("Motor OCR (EasyOCR) inicializado desde la GUI.")
                    if self.process_button.winfo_exists(): self.process_button.config(state=tk.NORMAL)
                else:
                    self.status_var.set("ERROR: Motor OCR no pudo inicializar. Revise logs.")
                    messagebox.showerror("Error OCR", "No se pudo inicializar EasyOCR. La funcionalidad OCR no estará disponible. Revise 'ocrename_activity.log'.")
            except Exception as e:
                self.status_var.set("ERROR CRÍTICO: Inicialización de OCR falló.")
                app_logger.critical(f"Error crítico inicializando PDFProcessor: {e}", exc_info=True)
                messagebox.showerror("Error Crítico OCR", f"Error al inicializar el motor OCR: {e}\nLa aplicación podría no funcionar correctamente.")
        
        threading.Thread(target=init_task, daemon=True).start()


    def _update_api_status_label(self):
        # ... (sin cambios) ...
        if self.ai_integrator.is_api_configured_and_client_valid():
            self.api_status_var.set("DeepSeek/Llama (OpenRouter): API Key Configurada")
            self.api_status_label.config(foreground="green")
        else:
            self.api_status_var.set("DeepSeek/Llama (OpenRouter): API Key NO Configurada (ver .env)")
            self.api_status_label.config(foreground="red")


    def _setup_ui(self):
        # Frame principal que contendrá el panel izquierdo (controles) y el panel derecho (vista previa)
        top_level_frame = ttk.Frame(self.root, padding="5")
        top_level_frame.pack(fill=tk.BOTH, expand=True)

        # Panel Izquierdo para Controles
        left_panel = ttk.Frame(top_level_frame, padding="5")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # Panel Derecho para Vista Previa de Imagen
        right_panel = ttk.LabelFrame(top_level_frame, text="Vista Previa (1ra Página)", padding="10")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.preview_image_label = ttk.Label(right_panel)
        self.preview_image_label.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.preview_image_label.bind('<Configure>', self._on_preview_resize) # Para re-escalar si el label cambia


        # --- Contenido del Panel Izquierdo ---
        # 1. Selección de Archivos
        files_frame = ttk.LabelFrame(left_panel, text="1. Selección de Archivos PDF", padding="10")
        files_frame.pack(fill=tk.X, pady=5, anchor="n") # anchor="n" para que se quede arriba
        
        self.select_button = ttk.Button(files_frame, text="Seleccionar Archivos", command=self._select_files)
        self.select_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.clear_button = ttk.Button(files_frame, text="Limpiar Lista", command=self._clear_files)
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.files_listbox = tk.Listbox(files_frame, selectmode=tk.SINGLE, height=8, width=55) # Cambiado a SINGLE y un poco más alto
        self.files_listbox.pack(pady=5, fill=tk.X, expand=True)
        self.files_listbox.bind('<<ListboxSelect>>', self._on_file_select_in_listbox) # Para actualizar vista previa

        # 2. Selección de Tipo de Documento
        doc_type_frame = ttk.LabelFrame(left_panel, text="2. Tipo de Documento", padding="10")
        doc_type_frame.pack(fill=tk.X, pady=5, anchor="n")
        self.doc_type_var = tk.StringVar(value="pendiente_impreso")
        rb_pendiente = ttk.Radiobutton(doc_type_frame, text="Formato A: Acta Impresa (ej. SUPLY)", 
                                   variable=self.doc_type_var, value="pendiente_impreso")
        rb_pendiente.pack(anchor=tk.W, padx=5, pady=2)
        rb_entregado = ttk.Radiobutton(doc_type_frame, text="Formato B: Acta Manuscrita (ej. E.S.E.)", 
                                  variable=self.doc_type_var, value="entregado_manuscrito")
        rb_entregado.pack(anchor=tk.W, padx=5, pady=2)

        # 3. Procesamiento
        process_controls_frame = ttk.LabelFrame(left_panel, text="3. Procesamiento", padding="10")
        process_controls_frame.pack(fill=tk.X, pady=5, anchor="n")
        self.process_button = ttk.Button(process_controls_frame, text="Iniciar Procesamiento", command=self._start_processing_thread, state=tk.DISABLED)
        self.process_button.pack(pady=5)
        
        # 4. Progreso Detallado
        progress_frame = ttk.LabelFrame(left_panel, text="4. Progreso Detallado", padding="10")
        progress_frame.pack(fill=tk.X, pady=5, anchor="n")
        # ... (widgets de progreso como antes, pero dentro de left_panel) ...
        ttk.Label(progress_frame, text="Archivo Actual:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_file_var = tk.StringVar(value="N/A")
        ttk.Label(progress_frame, textvariable=self.current_file_var, width=40).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5)

        ttk.Label(progress_frame, text="Progreso OCR:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.ocr_progressbar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=250, mode='determinate')
        self.ocr_progressbar.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.ocr_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.ocr_progress_var).grid(row=1, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(progress_frame, text="Progreso General:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.overall_progressbar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=250, mode='determinate')
        self.overall_progressbar.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.overall_progress_var = tk.StringVar(value="0/0 (0%)")
        ttk.Label(progress_frame, textvariable=self.overall_progress_var).grid(row=2, column=2, sticky=tk.W, padx=5)
        progress_frame.columnconfigure(1, weight=1)


        # 5. Estado y Logs (en la parte inferior del panel izquierdo)
        status_log_frame = ttk.LabelFrame(left_panel, text="5. Estado y Mensajes", padding="10")
        status_log_frame.pack(fill=tk.BOTH, expand=True, pady=5, anchor="s") # anchor="s" para que se expanda hacia abajo
        
        self.log_text = tk.Text(status_log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.log_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0,5))
        # No se necesita scrollbar si el tamaño es fijo y el texto no es muy largo, o añadirlo como antes
        
        self.api_status_var = tk.StringVar()
        self.api_status_label = ttk.Label(status_log_frame, textvariable=self.api_status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        self.api_status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self._update_api_status_label()
        
        self.status_var = tk.StringVar(value="Esperando inicialización del motor OCR...")
        status_bar = ttk.Label(status_log_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self._add_gui_log_handler()


    def _add_gui_log_handler(self):
        # ... (sin cambios) ...
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                self.formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

            def emit(self, record):
                msg = self.format(record)
                if self.text_widget.winfo_exists():
                    self.text_widget.config(state=tk.NORMAL)
                    self.text_widget.insert(tk.END, msg + "\n")
                    self.text_widget.see(tk.END)
                    self.text_widget.config(state=tk.DISABLED)
        
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setLevel(logging.INFO) 
        app_logger.addHandler(gui_handler)


    def _resize_pil_image(self, pil_image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Redimensiona una imagen PIL manteniendo la proporción para que quepa en max_width/max_height."""
        img_width, img_height = pil_image.size
        if img_width == 0 or img_height == 0: return pil_image # Evitar división por cero

        # Calcular ratio para ancho y alto
        ratio_w = max_width / img_width
        ratio_h = max_height / img_height
        # Usar el ratio más pequeño para asegurar que la imagen quepa completamente
        ratio = min(ratio_w, ratio_h)

        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        return pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _display_preview_image(self, pil_image: Optional[Image.Image]):
        """Muestra la imagen PIL en el label de vista previa."""
        if pil_image:
            # Esperar a que el widget de la label tenga dimensiones
            self.preview_image_label.update_idletasks() 
            preview_width = self.preview_image_label.winfo_width() - 10 # -10 para pequeño padding
            preview_height = self.preview_image_label.winfo_height() - 10
            
            if preview_width <= 1 or preview_height <=1: # Si el widget aún no tiene tamaño
                app_logger.debug("Widget de vista previa aún no tiene tamaño, usando dimensiones por defecto para escalar.")
                preview_width = 300 # Un valor por defecto razonable
                preview_height = 400

            resized_pil_image = self._resize_pil_image(pil_image, preview_width, preview_height)
            self.current_preview_tk_image = ImageTk.PhotoImage(resized_pil_image)
            self.preview_image_label.config(image=self.current_preview_tk_image)
        else:
            self.preview_image_label.config(image='') # Limpiar vista previa
            self.current_preview_tk_image = None
        self.root.update_idletasks()

    def _on_preview_resize(self, event):
        """Llamado cuando el label de vista previa cambia de tamaño."""
        if self.current_preview_pil_image:
            self._display_preview_image(self.current_preview_pil_image)


    def _load_and_display_first_pdf_page(self, filepath: str):
        """Carga la primera página de un PDF y la muestra."""
        try:
            poppler_path_setting = settings.POPPLER_PATH if hasattr(settings, 'POPPLER_PATH') else None
            images = convert_from_path(filepath, first_page=1, last_page=1, poppler_path=poppler_path_setting, dpi=150) # DPI más bajo para vista previa rápida
            if images:
                self.current_preview_pil_image = images[0]
                self._display_preview_image(self.current_preview_pil_image)
            else:
                app_logger.warning(f"No se pudo convertir PDF para vista previa: {filepath}")
                self._display_preview_image(None)
        except Exception as e:
            app_logger.error(f"Error al cargar PDF para vista previa '{filepath}': {e}", exc_info=True)
            self._display_preview_image(None)
            messagebox.showerror("Error Vista Previa", f"No se pudo cargar la vista previa del PDF:\n{os.path.basename(filepath)}\n\nError: {e}")


    def _on_file_select_in_listbox(self, event):
        """Cuando un archivo es seleccionado en la Listbox, intenta mostrar su vista previa."""
        widget = event.widget
        selected_indices = widget.curselection()
        if selected_indices:
            selected_index = selected_indices[0]
            # La listbox almacena nombres de archivo, necesitamos la ruta completa de self.selected_files
            # Esto asume que el orden en self.selected_files es el mismo que en la listbox.
            # Sería más robusto si la listbox almacenara las rutas completas o tuviéramos un mapeo.
            # Por ahora, una simplificación:
            if selected_index < len(self.selected_files):
                filepath_to_preview = self.selected_files[selected_index]
                self._load_and_display_first_pdf_page(filepath_to_preview)
            else:
                self._display_preview_image(None)
        else:
            self._display_preview_image(None)


    def _select_files(self):
        if self.is_processing: return
        filepaths = filedialog.askopenfilenames(
            title="Seleccionar Archivos PDF",
            filetypes=(("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*"))
        )
        if filepaths:
            self.selected_files.extend(list(filepaths))
            self.selected_files = sorted(list(set(self.selected_files)))
            self._update_files_listbox()
            self.status_var.set(f"{len(self.selected_files)} archivos en lista.")
            if len(self.selected_files) == 1: # Si solo hay un archivo, mostrarlo
                self._load_and_display_first_pdf_page(self.selected_files[0])
            elif len(self.selected_files) > 1:
                 self._display_preview_image(None) # Limpiar si hay muchos
                 self.current_preview_pil_image = None


    def _clear_files(self):
        if self.is_processing: return
        self.selected_files.clear()
        self._update_files_listbox()
        self.status_var.set("Lista de archivos limpiada.")
        self._display_preview_image(None) # Limpiar vista previa
        self.current_preview_pil_image = None


    def _update_files_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for fp_idx, fp in enumerate(self.selected_files):
            self.files_listbox.insert(tk.END, f"{fp_idx+1}. {os.path.basename(fp)}")
        self.overall_progressbar['value'] = 0
        self.ocr_progressbar['value'] = 0
        self.current_file_var.set("N/A")
        self._update_overall_progress_label(0, len(self.selected_files))
        if not self.selected_files:
            self._display_preview_image(None)
            self.current_preview_pil_image = None


    def _update_ocr_progress_callback(self, value: int):
        # ... (sin cambios) ...
        if self.root.winfo_exists():
            self.ocr_progressbar['value'] = value
            self.ocr_progress_var.set(f"{value}%")
            self.root.update_idletasks()

    def _update_overall_progress_label(self, current, total):
        # ... (sin cambios) ...
        percentage = (current / total * 100) if total > 0 else 0
        self.overall_progress_var.set(f"{current}/{total} ({percentage:.0f}%)")

    def _toggle_controls(self, processing_state: bool):
        # ... (ligeramente modificado para incluir radiobuttons) ...
        self.is_processing = processing_state
        state = tk.DISABLED if processing_state else tk.NORMAL
        
        if self.select_button.winfo_exists(): self.select_button.config(state=state)
        if self.clear_button.winfo_exists(): self.clear_button.config(state=state)
        
        # Deshabilitar también los radiobuttons durante el procesamiento
        # Asumiendo que doc_type_frame se guarda como self.doc_type_frame o se accede de otra forma
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame): # Contenedor principal
                for sub_child in child.winfo_children(): # Paneles izquierdo/derecho
                    if isinstance(sub_child, ttk.Frame):
                        for frame_child in sub_child.winfo_children(): # LabelFrames
                            if isinstance(frame_child, ttk.LabelFrame) and "Tipo de Documento" in frame_child.cget("text"):
                                for rb_child in frame_child.winfo_children():
                                    if isinstance(rb_child, ttk.Radiobutton) and rb_child.winfo_exists():
                                        rb_child.config(state=state)
                                break 

        if self.process_button.winfo_exists():
            if self.pdf_processor and self.pdf_processor.reader and not processing_state:
                 self.process_button.config(state=tk.NORMAL)
            else:
                self.process_button.config(state=tk.DISABLED)


    def _start_processing_thread(self):
        # ... (sin cambios) ...
        if not self.selected_files:
            messagebox.showinfo("Sin Archivos", "Por favor, seleccione archivos PDF primero.")
            return
        if self.is_processing:
            messagebox.showwarning("En Progreso", "El procesamiento ya está en curso.")
            return
        if not self.pdf_processor or not self.pdf_processor.reader:
            messagebox.showerror("Error OCR", "El motor OCR no está listo. Espere o reinicie la aplicación.")
            return

        self._toggle_controls(True)
        self.status_var.set("Iniciando procesamiento...")
        
        processing_thread = threading.Thread(target=self._process_files_logic, daemon=True)
        processing_thread.start()


    def _process_files_logic(self):
        selected_doc_type = self.doc_type_var.get()
        app_logger.info(f"Tipo de documento seleccionado para procesar: {selected_doc_type}")

        total_files = len(self.selected_files)
        if total_files == 0:
            if self.root.winfo_exists(): self._toggle_controls(False)
            self.status_var.set("No hay archivos seleccionados para procesar.")
            return

        self.overall_progressbar['maximum'] = total_files
        files_to_process = list(self.selected_files)

        for i, filepath in enumerate(files_to_process):
            if not self.root.winfo_exists():
                app_logger.info("Ventana de GUI cerrada, deteniendo procesamiento.")
                break
            
            filename = os.path.basename(filepath)
            # Actualizar vista previa al archivo actual si la GUI aún existe
            if self.root.winfo_exists():
                 self.root.after(0, self._load_and_display_first_pdf_page, filepath) # Usar after para actualizar desde hilo

            self.current_file_var.set(f"{filename} ({i+1}/{total_files})")
            self.ocr_progressbar['value'] = 0
            # ... (resto de la lógica de _process_files_logic como en la respuesta anterior,
            #      incluyendo la llamada a get_data_with_text_ai y get_data_with_vision_ai
            #      basándose en selected_doc_type y si los datos están completos) ...
            # Asegúrate de que la lógica de qué IA llamar y cuándo esté bien definida.

            # --- COMIENZO DE LA LÓGICA DE PROCESAMIENTO DETALLADA (como antes) ---
            app_logger.info(f"--- Procesando archivo: {filename} ---")
            self.status_var.set(f"Extrayendo texto de {filename}...")

            extracted_text, text_extraction_method = self.pdf_processor.extract_text_from_pdf(filepath, self._update_ocr_progress_callback)
            if not extracted_text and selected_doc_type == "pendiente_impreso": # Si es impreso y no hay texto, es un problema mayor
                app_logger.error(f"No se pudo extraer texto de {filename} (tipo impreso, método: {text_extraction_method}). Se moverá a fallidos.")
                self.file_manager.move_to_failed(filepath)
                self.overall_progressbar['value'] = i + 1
                continue
            elif not extracted_text and selected_doc_type == "entregado_manuscrito":
                app_logger.warning(f"No se pudo extraer texto OCR de página completa de {filename} (tipo manuscrito). Se intentará con IA de Visión si es posible.")
                # No continuamos, dejaremos que la IA de Visión lo intente con la imagen.

            # Actualizar status_var solo si la GUI existe
            if self.root.winfo_exists(): self.status_var.set(f"Analizando datos de {filename}...")

            # PASO 2: Extracción de datos impresos (ID, Nombre)
            extracted_data = {}
            if extracted_text: # Solo intentar regex si hay texto
                extracted_data = self.pdf_processor.extract_printed_data_from_text(extracted_text)
            else: # Inicializar con Nones si no hubo texto para regex
                extracted_data = {"id_type": None, "id_number": None, "acta_no": None}

            final_data_source = "PrintedRegex" if extracted_text else "NoTextForRegex"


            # PASO 3: Lógica específica para el número de acta y/o IA de Visión
            first_page_pil_image = None # Para IA de visión o HTR de ROI

            if selected_doc_type == "entregado_manuscrito":
                app_logger.info(f"Documento tipo 'Entregado con Manuscrito' para {filename}.")
                try:
                    poppler_path_setting = settings.POPPLER_PATH if hasattr(settings, 'POPPLER_PATH') else None
                    temp_images = convert_from_path(filepath, first_page=1, last_page=1, poppler_path=poppler_path_setting, dpi=200) # Mejor DPI para HTR/Visión
                    if temp_images:
                        first_page_pil_image = temp_images[0]
                except Exception as e_img_load:
                    app_logger.error(f"No se pudo cargar imagen para acta manuscrita/visión de {filename}: {e_img_load}", exc_info=True)

                if first_page_pil_image:
                    # Intento 1 para "entregado_manuscrito": HTR de ROI
                    handwritten_acta_roi = self.pdf_processor.extract_handwritten_acta_number(first_page_pil_image)
                    if handwritten_acta_roi:
                        extracted_data["acta_no"] = handwritten_acta_roi
                        final_data_source += "/HandwrittenROI"
                        app_logger.info(f"Número de acta de ROI manuscrita '{handwritten_acta_roi}' usado para {filename}.")
                    
                    # Intento 2 para "entregado_manuscrito": IA de Visión (si ROI HTR falló o para todos los campos)
                    # Decidimos si usar Vision AI siempre o como fallback. Aquí como fallback si datos incompletos.
                    data_complete_after_roi = all(extracted_data.get(key) for key in ["id_type", "id_number", "acta_no"])
                    if (not data_complete_after_roi or extracted_data.get("acta_no") is None) and \
                       self.ai_integrator.is_api_configured_and_client_valid() and self.ai_integrator.vision_model_name:
                        
                        if self.root.winfo_exists(): self.status_var.set(f"Consultando IA de Visión para {filename}...")
                        vision_ai_data = self.ai_integrator.get_data_with_vision_ai(first_page_pil_image, filename)
                        if vision_ai_data:
                            app_logger.info(f"IA de Visión devolvió: {vision_ai_data}")
                            # La IA de visión podría rellenar todos los campos.
                            # Darle prioridad si devuelve algo.
                            for key_v in ["id_type", "id_number", "acta_no"]:
                                if vision_ai_data.get(key_v) is not None:
                                    extracted_data[key_v] = vision_ai_data.get(key_v)
                            final_data_source = "VisionAI" # Asumir que si se usa, es la fuente principal
                            app_logger.info(f"Datos para '{filename}' actualizados por IA de Visión: {extracted_data}")
                        else:
                            app_logger.warning(f"IA de Visión no pudo extraer datos para {filename}.")
                else:
                    app_logger.warning(f"No se pudo obtener imagen para HTR/Visión en {filename} (tipo manuscrito).")

            # PASO 4: Fallback a IA de Texto si los datos siguen incompletos (para ambos tipos de doc)
            data_complete_before_text_ai = all(extracted_data.get(key) for key in ["id_type", "id_number", "acta_no"])

            if not data_complete_before_text_ai and self.ai_integrator.is_api_configured_and_client_valid() and self.ai_integrator.text_model_name:
                if not extracted_text:
                    app_logger.warning(f"No hay texto OCR de página completa para enviar a IA de texto para {filename}. Omitiendo IA de texto.")
                else:
                    if self.root.winfo_exists(): self.status_var.set(f"Consultando IA de texto para {filename}...")
                    ai_text_data = self.ai_integrator.get_data_with_text_ai(extracted_text, filename)
                    if ai_text_data:
                        app_logger.info(f"IA de Texto devolvió: {ai_text_data}")
                        for key_t in ["id_type", "id_number", "acta_no"]:
                            if ai_text_data.get(key_t) is not None and extracted_data.get(key_t) is None: # Solo rellenar si estaba vacío
                                extracted_data[key_t] = ai_text_data.get(key_t)
                                final_data_source += "+TextAIComplement"
                        app_logger.info(f"Datos para '{filename}' complementados por IA de texto: {extracted_data}")
                    else:
                        app_logger.warning(f"IA de texto no pudo extraer/mejorar datos para {filename}.")
            
            # PASO 5: Verificación final y renombrado
            new_filename_base = self.file_manager.generate_new_filename(
                extracted_data.get("id_type"),
                extracted_data.get("id_number"),
                extracted_data.get("acta_no"),
                original_ext=os.path.splitext(filename)[1]
            )

            if new_filename_base:
                app_logger.info(f"Datos finales para '{filename}' (fuente: {final_data_source}): {extracted_data}. Nuevo nombre: {new_filename_base}")
                if self.root.winfo_exists(): self.status_var.set(f"Renombrando {filename}...")
                self.file_manager.copy_and_rename(filepath, new_filename_base)
            else:
                app_logger.error(f"No se pudo generar un nombre de archivo válido para '{filename}' (datos cruciales faltantes). Moviendo a fallidos. Datos: {extracted_data}")
                self.file_manager.move_to_failed(filepath)
            
            if self.root.winfo_exists(): self.overall_progressbar['value'] = i + 1
            self._update_overall_progress_label(i + 1, total_files)
            # --- FIN DE LA LÓGICA DE PROCESAMIENTO DETALLADA ---


        # Fin del bucle de procesamiento
        if self.root.winfo_exists():
            self._toggle_controls(False)
            self.status_var.set(f"Procesamiento completado. {total_files} archivos procesados.")
            self.current_file_var.set("N/A")
            self._update_overall_progress_label(total_files, total_files)
            messagebox.showinfo("Completado", f"Procesamiento finalizado.\nArchivos renombrados en: {self.file_manager.renamed_dir}\nArchivos fallidos en: {self.file_manager.failed_dir}")
            self.selected_files.clear()
            self._update_files_listbox() # Esto limpiará la vista previa también
        else:
            app_logger.info("Procesamiento completado pero la ventana de GUI ya no existe.")