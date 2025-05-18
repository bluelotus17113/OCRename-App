import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import logging
from typing import List, Dict, Optional
import subprocess # Para abrir carpetas
import sys        # Para identificar el sistema operativo

from pdf2image import convert_from_path # Asumiendo que sigue siendo necesario aquí para el tipo manuscrito

from utils.logger import get_app_logger
from core.pdf_processor import PDFProcessor
from core.ai_integration import AIIntegrator
from core.file_manager import FileManager
from config import settings

app_logger = get_app_logger()

class AppGUI:
    def __init__(self, root_tk: tk.Tk):
        self.root = root_tk
        self.root.title("OCRename v0.3 - Abrir Resultados") # Actualizar versión/título
        self.root.geometry("800x700") 

        self.pdf_processor: Optional[PDFProcessor] = None
        self.ai_integrator = AIIntegrator()
        self.file_manager = FileManager() # FileManager crea las carpetas en su __init__

        self.selected_files: List[str] = []
        self.is_processing = False

        self._setup_ui()
        self._initialize_ocr_engine_async()

    def _initialize_ocr_engine_async(self):
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
        if self.ai_integrator.is_api_configured_and_client_valid():
            self.api_status_var.set("DeepSeek (OpenRouter): API Key Configurada")
            self.api_status_label.config(foreground="green")
        else:
            self.api_status_var.set("DeepSeek (OpenRouter): API Key NO Configurada (ver .env)")
            self.api_status_label.config(foreground="red")

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Selección de Archivos ---
        files_frame = ttk.LabelFrame(main_frame, text="1. Selección de Archivos PDF", padding="10")
        files_frame.pack(fill=tk.X, pady=5)
        self.select_button = ttk.Button(files_frame, text="Seleccionar Archivos", command=self._select_files)
        self.select_button.pack(side=tk.LEFT, padx=5)
        self.clear_button = ttk.Button(files_frame, text="Limpiar Lista", command=self._clear_files)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        self.files_listbox_frame = ttk.Frame(files_frame)
        self.files_listbox_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.files_listbox = tk.Listbox(self.files_listbox_frame, selectmode=tk.EXTENDED, height=6, width=70)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        listbox_scrollbar = ttk.Scrollbar(self.files_listbox_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=listbox_scrollbar.set)

        # --- Selección de Tipo de Documento ---
        doc_type_frame = ttk.LabelFrame(main_frame, text="2. Seleccione el Tipo de Documento a Procesar", padding="10")
        doc_type_frame.pack(fill=tk.X, pady=(10,5), padx=0)
        self.doc_type_var = tk.StringVar(value="pendiente_impreso")
        rb_pendiente = ttk.Radiobutton(doc_type_frame, text="Formato A: Acta Impresa (ej. SUPLY MEDICAL)", 
                                   variable=self.doc_type_var, value="pendiente_impreso")
        rb_pendiente.pack(anchor=tk.W, padx=10, pady=2)
        rb_entregado = ttk.Radiobutton(doc_type_frame, text="Formato B: Acta Manuscrita en Esquina (ej. E.S.E. UNIDAD)", 
                                  variable=self.doc_type_var, value="entregado_manuscrito")
        rb_entregado.pack(anchor=tk.W, padx=10, pady=2)

        # --- Controles de Procesamiento y Resultados ---
        process_controls_frame = ttk.LabelFrame(main_frame, text="3. Procesamiento y Resultados", padding="10")
        process_controls_frame.pack(fill=tk.X, pady=10)
        
        self.process_button = ttk.Button(process_controls_frame, text="Iniciar Procesamiento", command=self._start_processing_thread, state=tk.DISABLED)
        self.process_button.pack(pady=(5,2))

        self.open_results_button = ttk.Button(process_controls_frame, text="Abrir Carpeta de Resultados", command=self._open_results_folder, state=tk.DISABLED)
        # Habilitar el botón de abrir resultados si las carpetas ya existen (FileManager las crea en __init__)
        if os.path.isdir(self.file_manager.output_base):
            self.open_results_button.config(state=tk.NORMAL)
        self.open_results_button.pack(pady=(2,5))
        
        # --- Progreso ---
        progress_frame = ttk.LabelFrame(main_frame, text="4. Progreso Detallado", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        ttk.Label(progress_frame, text="Archivo Actual:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_file_var = tk.StringVar(value="N/A")
        ttk.Label(progress_frame, textvariable=self.current_file_var, width=60).grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5)
        ttk.Label(progress_frame, text="Progreso OCR (Archivo):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.ocr_progressbar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.ocr_progressbar.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.ocr_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.ocr_progress_var).grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Label(progress_frame, text="Progreso General:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.overall_progressbar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.overall_progressbar.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.overall_progress_var = tk.StringVar(value="0/0 (0%)")
        ttk.Label(progress_frame, textvariable=self.overall_progress_var).grid(row=2, column=2, sticky=tk.W, padx=5)
        progress_frame.columnconfigure(1, weight=1)

        # --- Estado y Logs ---
        status_log_frame = ttk.LabelFrame(main_frame, text="5. Estado y Mensajes", padding="10")
        status_log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.status_var = tk.StringVar(value="Esperando inicialización del motor OCR...")
        status_bar = ttk.Label(status_log_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.api_status_var = tk.StringVar()
        self.api_status_label = ttk.Label(status_log_frame, textvariable=self.api_status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        self.api_status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self._update_api_status_label()
        log_text_frame = ttk.Frame(status_log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_text_frame, height=10, state=tk.DISABLED, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self._add_gui_log_handler()

    def _add_gui_log_handler(self):
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

    def _clear_files(self):
        if self.is_processing: return
        self.selected_files.clear()
        self._update_files_listbox()
        self.status_var.set("Lista de archivos limpiada.")
        # Opcional: deshabilitar el botón de abrir resultados si se limpia la lista
        # if self.open_results_button.winfo_exists():
        #     self.open_results_button.config(state=tk.DISABLED)


    def _update_files_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for fp in self.selected_files:
            self.files_listbox.insert(tk.END, os.path.basename(fp))
        self.overall_progressbar['value'] = 0
        self.ocr_progressbar['value'] = 0
        self.current_file_var.set("N/A")
        self._update_overall_progress_label(0, len(self.selected_files))

    def _update_ocr_progress_callback(self, value: int):
        if self.root.winfo_exists():
            self.ocr_progressbar['value'] = value
            self.ocr_progress_var.set(f"{value}%")
            self.root.update_idletasks()

    def _update_overall_progress_label(self, current, total):
        percentage = (current / total * 100) if total > 0 else 0
        self.overall_progress_var.set(f"{current}/{total} ({percentage:.0f}%)")

    def _toggle_controls(self, processing_state: bool):
        self.is_processing = processing_state
        state = tk.DISABLED if processing_state else tk.NORMAL
        
        if self.select_button.winfo_exists(): self.select_button.config(state=state)
        if self.clear_button.winfo_exists(): self.clear_button.config(state=state)
        
        # Deshabilitar también los radiobuttons durante el procesamiento
        # Iterar sobre los hijos del frame de tipo de documento
        doc_type_frame_children = []
        for child_widget in self.root.winfo_children():
            if isinstance(child_widget, ttk.LabelFrame) and "Tipo de Documento" in child_widget.cget("text"):
                doc_type_frame_children = child_widget.winfo_children()
                break
        
        for rb_child in doc_type_frame_children:
            if isinstance(rb_child, ttk.Radiobutton) and rb_child.winfo_exists():
                rb_child.config(state=state)

        if self.process_button.winfo_exists():
            if self.pdf_processor and self.pdf_processor.reader and not processing_state:
                 self.process_button.config(state=tk.NORMAL)
            else:
                self.process_button.config(state=tk.DISABLED)
        
        # El botón de abrir resultados se maneja por separado (se habilita después del primer proceso)
        # pero también se deshabilita si el procesamiento está activo.
        if self.open_results_button.winfo_exists():
            if processing_state: # Si está procesando, deshabilitar
                self.open_results_button.config(state=tk.DISABLED)
            elif os.path.isdir(self.file_manager.output_base): # Si no está procesando y la carpeta existe, habilitar
                 self.open_results_button.config(state=tk.NORMAL)


    def _open_results_folder(self):
        results_path = self.file_manager.output_base
        
        if not os.path.isdir(results_path):
            app_logger.warning(f"La carpeta de resultados '{results_path}' no existe aún.")
            messagebox.showwarning("Carpeta no encontrada", f"La carpeta de resultados '{results_path}' aún no ha sido creada. Por favor, procese algunos archivos primero.")
            return

        app_logger.info(f"Abriendo carpeta de resultados: {results_path}")
        try:
            if sys.platform == "win32":
                os.startfile(os.path.realpath(results_path)) # os.path.realpath para manejar rutas relativas/simbólicas
            elif sys.platform == "darwin":
                subprocess.Popen(["open", os.path.realpath(results_path)])
            else: 
                subprocess.Popen(["xdg-open", os.path.realpath(results_path)])
        except Exception as e:
            app_logger.error(f"No se pudo abrir la carpeta de resultados '{results_path}': {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir la carpeta de resultados: {e}")

    def _start_processing_thread(self):
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
            self.current_file_var.set(f"{filename} ({i+1}/{total_files})")
            self.ocr_progressbar['value'] = 0
            self.ocr_progress_var.set("0%")
            self._update_overall_progress_label(i, total_files)
            self.root.update_idletasks()

            app_logger.info(f"--- Procesando archivo: {filename} ---")
            self.status_var.set(f"Extrayendo texto de {filename}...")

            extracted_text, text_extraction_method = self.pdf_processor.extract_text_from_pdf(filepath, self._update_ocr_progress_callback)
            if not extracted_text:
                app_logger.error(f"No se pudo extraer texto de {filename} (método: {text_extraction_method}). Se moverá a fallidos.")
                self.file_manager.move_to_failed(filepath)
                self.overall_progressbar['value'] = i + 1
                continue

            app_logger.info(f"Texto extraído de '{filename}' (método: {text_extraction_method}). Analizando...")
            self.status_var.set(f"Analizando texto de {filename}...")

            extracted_data = self.pdf_processor.extract_printed_data_from_text(extracted_text)
            final_data_source = "PrintedRegex"

            if selected_doc_type == "entregado_manuscrito":
                app_logger.info(f"Documento tipo 'Entregado con Manuscrito'. Buscando acta manuscrita para {filename}...")
                first_page_pil_image = None
                try:
                    poppler_path_setting = settings.POPPLER_PATH if hasattr(settings, 'POPPLER_PATH') else None
                    temp_images = convert_from_path(filepath, first_page=1, last_page=1, poppler_path=poppler_path_setting)
                    if temp_images:
                        first_page_pil_image = temp_images[0]
                except Exception as e_img_load:
                    app_logger.error(f"No se pudo cargar imagen para acta manuscrita de {filename}: {e_img_load}", exc_info=True)

                if first_page_pil_image:
                    handwritten_acta = self.pdf_processor.extract_handwritten_acta_number(first_page_pil_image)
                    if handwritten_acta:
                        extracted_data["acta_no"] = handwritten_acta 
                        final_data_source += "/HandwrittenActa"
                        app_logger.info(f"Número de acta manuscrito '{handwritten_acta}' encontrado y usado para {filename}.")
                    else:
                        app_logger.warning(f"No se encontró número de acta manuscrito para {filename}. Se usará el de datos impresos si existe: '{extracted_data.get('acta_no')}'.")
                else:
                    app_logger.warning(f"No se pudo obtener imagen para buscar acta manuscrita en {filename}.")
            
            elif selected_doc_type == "pendiente_impreso":
                app_logger.info(f"Documento tipo 'Pendiente Entregado'. Usando acta_no de datos impresos: '{extracted_data.get('acta_no')}'.")

            data_complete_before_ai = all(extracted_data.get(key) for key in ["id_type", "id_number", "acta_no"])

            if not data_complete_before_ai and self.ai_integrator.is_api_configured_and_client_valid():
                app_logger.info(f"Datos incompletos para '{filename}' ({extracted_data}). Intentando con IA de texto...")
                self.status_var.set(f"Consultando IA de texto para {filename}...")
                ai_text_data = self.ai_integrator.get_data_with_text_ai(extracted_text, filename)
                
                if ai_text_data:
                    updated_by_ai = False
                    for key in ["id_type", "id_number", "acta_no"]:
                        if ai_text_data.get(key) is not None and (extracted_data.get(key) is None or ai_text_data.get(key) != extracted_data.get(key)):
                            extracted_data[key] = ai_text_data[key]
                            updated_by_ai = True
                    if updated_by_ai:
                        final_data_source += "+TextAI"
                        app_logger.info(f"Datos para '{filename}' actualizados/complementados por IA de texto: {extracted_data}")
                else:
                    app_logger.warning(f"IA de texto no devolvió datos o falló para '{filename}'.")

            new_filename_base = self.file_manager.generate_new_filename(
                extracted_data.get("id_type"),
                extracted_data.get("id_number"),
                extracted_data.get("acta_no"),
                original_ext=os.path.splitext(filename)[1]
            )

            if new_filename_base:
                app_logger.info(f"Datos finales para '{filename}' (fuente: {final_data_source}): {extracted_data}. Nuevo nombre: {new_filename_base}")
                self.status_var.set(f"Renombrando {filename}...")
                self.file_manager.copy_and_rename(filepath, new_filename_base)
            else:
                app_logger.error(f"No se pudo generar un nombre de archivo válido para '{filename}' debido a datos cruciales faltantes. Moviendo a fallidos. Datos: {extracted_data}")
                self.file_manager.move_to_failed(filepath)
            
            self.overall_progressbar['value'] = i + 1
            self._update_overall_progress_label(i + 1, total_files)

        if self.root.winfo_exists():
            self._toggle_controls(False) # Esto ahora también considera el botón de abrir resultados
            self.status_var.set(f"Procesamiento completado. {total_files} archivos procesados.")
            self.current_file_var.set("N/A")
            self._update_overall_progress_label(total_files, total_files)
            messagebox.showinfo("Completado", 
                                f"Procesamiento finalizado.\n"
                                f"Archivos renombrados en: {self.file_manager.renamed_dir}\n"
                                f"Archivos fallidos en: {self.file_manager.failed_dir}\n\n"
                                f"Puede abrir la carpeta de resultados usando el botón.")
            self.selected_files.clear()
            self._update_files_listbox()
        else:
            app_logger.info("Procesamiento completado pero la ventana de GUI ya no existe.")