# OCRename

# Short Description
OCRename is a Python application designed to process PDF documents, primarily focused on medical prescriptions or delivery acts. It automates the extraction of key information (such as patient ID, document/acta number) using Optical Character Recognition (OCR), regular expressions, and Artificial Intelligence (AI) model integration. The application then renames the files based on the extracted data for better organization. It features a graphical user interface (GUI) for ease of use.

# Features
- **PDF Processing:** Handles both text-based and image-based PDF files.
- **Optical Character Recognition (OCR):** Utilizes EasyOCR to extract text from image-based PDFs or when direct extraction fails. Includes support for multiple languages (configurable).
- **Image Preprocessing:** Optional image preprocessing capabilities (e.g., grayscale conversion) using OpenCV to potentially improve OCR accuracy.
- **Rule-Based Data Extraction:** Employs regular expressions to identify and extract specific data fields (ID type, ID number, acta number) from the extracted text.
- **Handwritten Text Recognition (HTR):** Specialized OCR for extracting handwritten acta numbers from a defined Region of Interest (ROI) in certain document types.
- **AI-Powered Data Extraction:** Integrates with external AI models (via OpenRouter) for:
    - Text-based analysis to extract data from OCRed text.
    - Vision-based analysis to extract data directly from PDF page images, useful for complex layouts or handwritten information.
- **Configurable AI Models:** Allows specification of different text and vision AI models through settings.
- **File Renaming & Organization:** Automatically renames processed files based on extracted data. Organizes files into "renamed" and "failed" directories.
- **Collision Handling:** Prevents overwriting files by appending a counter to filenames if a file with the same name already exists.
- **Graphical User Interface (GUI):** Provides a user-friendly interface built with Tkinter for:
    - Selecting multiple PDF files.
    - Choosing document processing types.
    - Monitoring processing progress (overall and per-file OCR).
    - Viewing status messages and logs.
    - Previewing the first page of selected PDFs.
- **Configuration:** Flexible configuration options through `config/settings.py` (or an environment file for sensitive data like API keys).
- **Logging:** Comprehensive logging of application activities and errors for monitoring and debugging.

# Requirements
- Python 3.7+
- Pip (Python package installer)
- Poppler: Required by the `pdf2image` library to convert PDF pages to images. The project includes a Windows version in the `poppler-24.08.0` directory. For other operating systems, Poppler needs to be installed and available in the system's PATH.
- Python packages:
    - `python-dotenv`
    - `easyocr`
    - `requests`
    - `PyPDF2`
    - `pdf2image`
    - `Pillow`
    - `openai`
    - (OpenCV is optional, for image preprocessing, and can be installed separately if needed: `opencv-python`)

# Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd ocrename 
    ```
    (Replace `<repository_url>` with the actual URL of the repository)

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Poppler:**
    *   **Windows:** The project includes a Poppler distribution in the `poppler-24.08.0` directory. The application attempts to use this. Ensure the path in `config/settings.py` ( `POPPLER_PATH`) points to your `poppler-24.08.0/Library/bin` if you move it or if it's not found automatically.
    *   **macOS/Linux:** Install Poppler using your system's package manager (e.g., `brew install poppler` on macOS, `sudo apt-get install poppler-utils` on Debian/Ubuntu). Ensure `pdftoppm` (part of Poppler) is accessible via the system PATH.

5.  **(Optional) Install OpenCV for image preprocessing:**
    If you want to enable image preprocessing features for potentially improved OCR, install OpenCV:
    ```bash
    pip install opencv-python
    ```
    Then, ensure `ENABLE_IMAGE_PREPROCESSING` is set to `True` in `config/settings.py`.

# Configuration

The application's behavior can be customized through settings primarily found in `config/settings.py`. For sensitive information like API keys, it's highly recommended to use a `.env` file in the project root.

1.  **API Key for AI Integration:**
    *   Create a `.env` file in the root directory of the project.
    *   Add your OpenRouter API key to this file:
        ```env
        OPENROUTER_API_KEY="your_openrouter_api_key_here"
        ```
    *   The application (`main.py`) loads this key at startup. If not found, AI-dependent features will be disabled.

2.  **Core Settings (`config/settings.py`):**
    *   `OPENROUTER_API_KEY`: While it can be set directly here, using a `.env` file is preferred for security.
    *   `DEEPSEEK_TEXT_MODEL`: Specifies the text-based AI model to be used via OpenRouter (default: `"deepseek/deepseek-r1:free"`).
    *   `LLAMA32_VISION_MODEL`: Specifies the vision-based AI model to be used via OpenRouter (default: `"meta-llama/llama-3.2-11b-vision-instruct:free"`).
    *   `API_TIMEOUT_SECONDS`: Timeout for API calls to OpenRouter (default: `60`).
    *   `API_MAX_RETRIES`: Number of retries for failed API calls (default: `3`).
    *   `OPENROUTER_SITE_URL`, `OPENROUTER_SITE_TITLE`: Optional headers for OpenRouter API calls.
    *   `POPPLER_PATH`: Path to the Poppler `bin` directory. For the bundled Windows version, this might be `os.path.join(BASE_DIR, 'poppler-24.08.0', 'Library', 'bin')`. It's often detected automatically if Poppler is in PATH or the bundled version is in the default location.
    *   `OCR_LANGUAGES`: List of languages for EasyOCR (default: `['es']`).
    *   `OCR_GPU`: Boolean to enable/disable GPU for EasyOCR (default: `False`).
    *   `ENABLE_IMAGE_PREPROCESSING`: Boolean to enable/disable OpenCV-based image preprocessing for OCR and HTR (default: `False`).
    *   `OUTPUT_BASE_DIR`: The main directory where processed files will be stored (default: `"OCRename_Resultados"`).
    *   `RENAMED_SUBDIR`: Subdirectory for successfully renamed files (default: `"Archivos_Renombrados"`).
    *   `FAILED_SUBDIR`: Subdirectory for files that failed processing (default: `"Archivos_Fallidos"`).
    *   `FILENAME_PLACEHOLDER`: Placeholder string used in filenames when a piece of data (ID type, ID number, Acta no.) is missing (default: `"DESCONOCIDO"`).
    *   `LOG_LEVEL`: Logging level for the application (e.g., `logging.INFO`, `logging.DEBUG`).
    *   `LOG_FILE`: Name of the activity log file (default: `"ocrename_activity.log"`).
    *   `DEBUG_LOG_DIR`: Directory for more detailed debug logs, especially for OCR outputs (default: `"OCRename_Logs_Debug"`).

**Note:** After changing any settings in `config/settings.py` or `.env`, restart the application for the changes to take effect.

# Usage

1.  **Ensure all setup and configuration steps are completed.** (Refer to "Setup and Installation" and "Configuration" sections).
2.  **Run the application:**
    Open your terminal or command prompt, navigate to the project's root directory (where `main.py` is located), and ensure your virtual environment is activated. Then execute:
    ```bash
    python main.py
    ```
3.  **Using the OCRename GUI:**
    *   **Window Layout:**
        *   The main window is divided into a left panel for controls and a right panel for PDF preview.
        *   **Left Panel:** Contains sections for file selection, document type, processing controls, progress display, and status messages/logs.
        *   **Right Panel:** Shows a preview of the first page of the currently selected PDF file from the list.
    *   **Step 1: Select PDF Files:**
        *   Click the "Seleccionar Archivos" button to open a file dialog.
        *   Choose one or more PDF files you want to process.
        *   The selected files will appear in the listbox below the buttons.
        *   To select a single file in the list to preview it, simply click on its name.
        *   Click "Limpiar Lista" to remove all files from the current selection.
    *   **Step 2: Choose Document Type:**
        *   Select the appropriate document type from the radio buttons:
            *   `Formato A: Acta Impresa (ej. SUPLY)`: For documents that are primarily printed and data extraction relies more on direct text or standard OCR.
            *   `Formato B: Acta Manuscrita (ej. E.S.E.)`: For documents that may contain significant handwritten parts, especially for the "acta number". This option enables HTR on a specific ROI and may also be a cue for the Vision AI.
    *   **Step 3: Start Processing:**
        *   Click the "Iniciar Procesamiento" button. This button is enabled only after the OCR engine initializes successfully.
        *   The application will begin processing the files one by one.
    *   **Step 4: Monitor Progress:**
        *   **Archivo Actual:** Shows the name of the file currently being processed and its sequence number (e.g., "document.pdf (1/5)").
        *   **Progreso OCR:** A progress bar indicating the OCR stage for the current file (if OCR is used).
        *   **Progreso General:** A progress bar showing the overall progress of the batch (e.g., "3/5 (60%)").
    *   **Step 5: Review Status and Logs:**
        *   **Log Text Area:** Displays real-time log messages (INFO level and above) about the application's operations. More detailed logs are saved to files (see "Logging" section).
        *   **API Status:** Indicates whether the OpenRouter API key is configured and if AI functionality is enabled.
        *   **Status Bar:** Shows general status messages, like "Motor OCR listo" or "Procesamiento completado."
    *   **After Processing:**
        *   A message box will appear summarizing the outcome.
        *   Successfully processed and renamed files will be copied to the `OCRename_Resultados/Archivos_Renombrados` directory (or as configured).
        *   Files that could not be processed successfully (e.g., due to missing critical data for renaming or repeated errors) will be moved to the `OCRename_Resultados/Archivos_Fallidos` directory.
        *   The file list in the GUI will be cleared.

**Important Notes:**
*   The OCR engine (EasyOCR) initialization might take a few seconds when the application starts. The "Iniciar Procesamiento" button will be disabled until it's ready.
*   If the `OPENROUTER_API_KEY` is not configured, AI-dependent extraction steps will be skipped, potentially affecting the accuracy for complex documents.
*   The quality of OCR and AI extraction can vary depending on the document's scan quality, layout, and handwriting.

# Directory Structure

```
OCRename/
├── .gitignore
├── config/                 # Configuration files
│   ├── __init__.py
│   └── settings.py         # Main application settings
├── core/                   # Core application logic
│   ├── __init__.py
│   ├── ai_integration.py   # AI model interaction
│   ├── file_manager.py     # File operations (renaming, moving)
│   └── pdf_processor.py    # PDF parsing, OCR, data extraction
├── Documentos admitidos/   # Example/supported PDF documents (if any)
├── gui/                    # Graphical User Interface
│   ├── __init__.py
│   └── interface.py        # Main GUI class and logic
├── main.py                 # Main application entry point
├── models/                 # EasyOCR models
│   ├── craft_mlt_25k.pth
│   └── latin_g2.pth
├── poppler-24.08.0/        # Bundled Poppler PDF rendering library (Windows)
├── OCRename_Resultados/    # Default output directory (created automatically)
│   ├── Archivos_Renombrados/ # Successfully processed and renamed files
│   └── Archivos_Fallidos/   # Files that failed processing
├── ocrename_activity.log   # Main activity log file (created automatically)
├── OCRename_Logs_Debug/    # Debug log files, especially OCR outputs (created automatically)
├── README.md               # This file
├── requirements.txt        # Python package dependencies
└── utils/                  # Utility modules
    ├── __init__.py
    └── logger.py           # Logging setup
```

**Key Directories:**
*   `config/`: Contains application settings.
*   `core/`: Houses the main processing logic (PDF handling, OCR, AI, file management).
*   `gui/`: Contains the Tkinter-based graphical user interface code.
*   `main.py`: The script to run the application.
*   `OCRename_Resultados/`: Default output directory where processed files are saved.
*   `poppler-24.08.0/`: Bundled Poppler version for Windows.
*   `models/`: Stores downloaded EasyOCR models.
*   `utils/`: Utility scripts, like logger configuration.

# Logging

The application generates logs to help monitor its activity and diagnose issues:

*   **Activity Log (`ocrename_activity.log`):**
    *   Located in the project's root directory.
    *   Records main events, processing status for each file, errors, and warnings at the INFO level by default (configurable in `config/settings.py` via `LOG_LEVEL`).
    *   This is the first place to check if you encounter issues or want to see a summary of operations.

*   **GUI Log Display:**
    *   The application's GUI has a dedicated text area that displays INFO-level log messages in real-time as they occur.

*   **Debug Logs (`OCRename_Logs_Debug/`):**
    *   Located in the `OCRename_Logs_Debug` directory within the project root.
    *   Contains more detailed information, especially:
        *   The full text extracted by direct PDF text extraction (if applicable) for each processed file, saved as `debug_direct_text_output_<original_filename>.txt`.
        *   The full text extracted by OCR (if applicable) for each processed file, saved as `debug_ocr_output_<original_filename>.txt`.
    *   This directory is created automatically.
    *   These logs are useful for debugging OCR accuracy issues or understanding exactly what text the application is working with.

The log level and log file names can be configured in `config/settings.py`.

# Contributing

Contributions are welcome! If you'd like to contribute to OCRename, please follow these general steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix (`git checkout -b feature/your-feature-name` or `bugfix/your-bug-fix`).
3.  Make your changes and commit them with clear, descriptive messages.
4.  Ensure your code adheres to any existing coding style and includes relevant tests if applicable.
5.  Push your changes to your forked repository.
6.  Open a pull request to the main OCRename repository, detailing the changes you've made.

# License

This project is licensed under the MIT License. See the `LICENSE` file for more details (if a `LICENSE` file is present in the repository).

If a `LICENSE` file is not present, you may consider adding one. For now, this statement indicates the intended licensing.
