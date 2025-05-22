import os
import shutil
from typing import Optional

from config import settings # Importar settings para acceder al placeholder
from utils.logger import get_app_logger

app_logger = get_app_logger()

class FileManager:
    def __init__(self):
        # Usar getattr para obtener valores de settings con un default por si acaso
        self.output_base = getattr(settings, 'OUTPUT_BASE_DIR', "OCRename_Resultados")
        renamed_subdir_name = getattr(settings, 'RENAMED_SUBDIR', "Archivos_Renombrados")
        failed_subdir_name = getattr(settings, 'FAILED_SUBDIR', "Archivos_Fallidos")
        
        self.renamed_dir = os.path.join(self.output_base, renamed_subdir_name)
        self.failed_dir = os.path.join(self.output_base, failed_subdir_name)
        self._create_output_dirs()

    def _create_output_dirs(self):
        try:
            os.makedirs(self.renamed_dir, exist_ok=True)
            os.makedirs(self.failed_dir, exist_ok=True)
            app_logger.info(f"Directorios de salida asegurados/creados: '{self.renamed_dir}', '{self.failed_dir}'")
        except OSError as e:
            app_logger.error(f"No se pudieron crear los directorios de salida: {e}")
            # Considerar lanzar una excepción si esto es crítico para la GUI o manejarlo de otra forma

    def generate_new_filename(self, id_type: Optional[str], id_number: Optional[str], acta_no: Optional[str], original_ext: str) -> Optional[str]:
        """
        Genera un nuevo nombre de archivo.
        Usa un placeholder para los campos que son None.
        Devuelve None si faltan datos cruciales (ej. id_number).
        """
        # Obtener el placeholder desde settings, con un valor por defecto si no está definido
        placeholder = getattr(settings, 'FILENAME_PLACEHOLDER', "DESCONOCIDO")

        # Función helper para limpiar y reemplazar None con placeholder
        def sanitize_value(value, default_placeholder):
            if value is None:
                return default_placeholder
            # Eliminar caracteres no seguros para nombres de archivo, excepto guiones bajos
            return "".join(c if c.isalnum() or c == '-' else "_" for c in str(value)).strip('_')

        s_id_type = sanitize_value(id_type, placeholder)
        s_id_number = sanitize_value(id_number, placeholder)
        s_acta_no = sanitize_value(acta_no, placeholder)
        
        # Decisión de diseño: ¿Qué campos son MÍNIMOS para renombrar?
        # Por ejemplo, si el id_number (ya sanitizado) es igual al placeholder,
        # consideramos que falta un dato crucial.
        if id_number is None or s_id_number == placeholder: # Chequeo más robusto
            app_logger.warning(
                f"No se generará nombre de archivo porque 'id_number' es crucial y falta o es el placeholder. "
                f"Datos originales: T:'{id_type}', N:'{id_number}', A:'{acta_no}'"
            )
            return None 
        
        new_name = f"{s_id_type}_{s_id_number}_{s_acta_no}{original_ext}"
        app_logger.debug(f"Nombre de archivo generado (antes de chequeo de colisión): {new_name}")
        return new_name

    def _handle_collision(self, destination_path: str) -> str:
        """Si el archivo ya existe, añade un contador al nombre (ej. archivo_1.pdf, archivo_2.pdf)."""
        if not os.path.exists(destination_path):
            return destination_path # No hay colisión

        base, ext = os.path.splitext(destination_path)
        counter = 1
        new_path = f"{base}_{counter}{ext}"
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base}_{counter}{ext}"
        
        app_logger.info(f"Conflicto de nombre detectado para '{os.path.basename(destination_path)}'. Se usará: '{os.path.basename(new_path)}'")
        return new_path

    def copy_and_rename(self, original_filepath: str, new_filename_base: str) -> bool:
        """Copia el archivo original a la carpeta de renombrados con el nuevo nombre base."""
        if not os.path.exists(original_filepath):
            app_logger.error(f"Archivo original no encontrado para copiar: {original_filepath}")
            return False

        destination_path = os.path.join(self.renamed_dir, new_filename_base)
        final_destination_path = self._handle_collision(destination_path) # Manejar colisiones
        
        try:
            shutil.copy2(original_filepath, final_destination_path) # copy2 preserva metadatos
            app_logger.info(f"Archivo '{os.path.basename(original_filepath)}' copiado y renombrado a '{os.path.basename(final_destination_path)}' en '{self.renamed_dir}'")
            return True
        except Exception as e:
            app_logger.error(f"Error al copiar/renombrar '{os.path.basename(original_filepath)}' a '{final_destination_path}': {e}", exc_info=True)
            return False

    def move_to_failed(self, original_filepath: str) -> bool:
        """Mueve el archivo original a la carpeta de fallidos."""
        if not os.path.exists(original_filepath):
            app_logger.warning(f"Se intentó mover a fallidos, pero el archivo original no existe: {original_filepath}")
            return False
            
        destination_path = os.path.join(self.failed_dir, os.path.basename(original_filepath))
        final_destination_path = self._handle_collision(destination_path) # Manejar colisiones también en fallidos
        
        try:
            shutil.move(original_filepath, final_destination_path)
            app_logger.info(f"Archivo '{os.path.basename(original_filepath)}' movido a '{final_destination_path}' en la carpeta de fallidos.")
            return True
        except Exception as e:
            app_logger.error(f"Error al mover '{os.path.basename(original_filepath)}' a fallidos ('{final_destination_path}'): {e}", exc_info=True)
            return False