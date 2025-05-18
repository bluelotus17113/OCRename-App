import tkinter as tk
from gui.interface import AppGUI
from utils.logger import get_app_logger # Cambiado
from config import settings

app_logger = get_app_logger() # Obtener logger

def main():
    app_logger.info("===============================================")
    app_logger.info("    Iniciando Aplicación OCRename        ")
    app_logger.info("===============================================")

    if not settings.OPENROUTER_API_KEY:
        app_logger.warning("ADVERTENCIA: OPENROUTER_API_KEY no está configurada en .env.")
        app_logger.warning("La funcionalidad de IA (DeepSeek) estará deshabilitada.")
    else:
        app_logger.info("OPENROUTER_API_KEY encontrada. Funcionalidad de IA habilitada.")

    try:
        root = tk.Tk()
        # from tkinterdnd2 import TkinterDnD # Descomenta si reinstalas y usas tkinterdnd2
        # root = TkinterDnD.Tk()          # Descomenta si reinstalas y usas tkinterdnd2
        app = AppGUI(root)
        root.mainloop()
    except Exception as e:
        app_logger.critical("Error fatal al iniciar o ejecutar la aplicación:", exc_info=True)
    finally:
        app_logger.info("===============================================")
        app_logger.info("    Aplicación OCRename Finalizada        ")
        app_logger.info("===============================================")

if __name__ == "__main__":
    main()