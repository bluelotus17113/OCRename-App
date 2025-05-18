import os
import shutil
from typing import Optional

from config import settings
from utils.logger import get_app_logger # Cambiado

app_logger = get_app_logger() # Obtener logger

class FileManager:
    def __init__(self):
        self.output_base = settings.OUTPUT_BASE_DIR
        self.renamed_dir = os.path.join(self.output_base, settings.RENAMED_SUBDIR)
        self.failed_dir = os.path.join(self.output_base, settings.FAILED_SUBDIR)
        self._create_output_dirs()

    def _create_output_dirs(self):
        try:
            os.makedirs(self.renamed_dir, exist_ok=True)
            os.makedirs(self.failed_dir, exist_ok=True)
            app_logger.info(f"Directorios de salida asegurados/creados: '{self.renamed_dir}', '{self.failed_dir}'")
        except OSError as e:
            app_logger.error(f"No se pudieron crear los directorios de salida: {e}")

    def generate_new_filename(self, id_type: Optional[str], id_number: Optional[str], acta_no: Optional[str], original_ext: str) -> Optional[str]:
        if id_type and id_number and acta_no:
            safe_id_type = "".join(c if c.isalnum() else "_" for c in str(id_type))
            safe_id_number = "".join(c if c.isalnum() else "_" for c in str(id_number))
            safe_acta_no = "".join(c if c.isalnum() else "_" for c in str(acta_no))
            return f"{safe_id_type}_{safe_id_number}_{safe_acta_no}{original_ext}"
        app_logger.warning(f"Datos incompletos para generar nombre: T:{id_type}, N:{id_number}, A:{acta_no}")
        return None

    def _handle_collision(self, destination_path: str) -> str:
        base, ext = os.path.splitext(destination_path)
        counter = 1
        new_path = destination_path
        while os.path.exists(new_path):
            new_path = f"{base}_{counter}{ext}"
            counter += 1
        if new_path != destination_path:
            app_logger.info(f"Conflicto de nombre. Se usará: '{os.path.basename(new_path)}'")
        return new_path

    def copy_and_rename(self, original_filepath: str, new_filename: str) -> bool:
        destination_path = os.path.join(self.renamed_dir, new_filename)
        destination_path = self._handle_collision(destination_path)
        try:
            shutil.copy2(original_filepath, destination_path)
            app_logger.info(f"Archivo '{os.path.basename(original_filepath)}' copiado y renombrado a '{os.path.basename(destination_path)}'")
            return True
        except Exception as e:
            app_logger.error(f"Error al copiar/renombrar '{os.path.basename(original_filepath)}' a '{destination_path}': {e}")
            return False

    def move_to_failed(self, original_filepath: str) -> bool:
        if not os.path.exists(original_filepath):
            app_logger.warning(f"Se intentó mover a fallidos, pero el archivo no existe: {original_filepath}")
            return False
            
        destination_path = os.path.join(self.failed_dir, os.path.basename(original_filepath))
        destination_path = self._handle_collision(destination_path)
        try:
            shutil.move(original_filepath, destination_path)
            app_logger.info(f"Archivo '{os.path.basename(original_filepath)}' movido a la carpeta de fallidos.")
            return True
        except Exception as e:
            app_logger.error(f"Error al mover '{os.path.basename(original_filepath)}' a fallidos: {e}")
            return False