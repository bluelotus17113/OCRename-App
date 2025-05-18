# test_connection.py
from core.ai_integration import AIIntegrator

ai = AIIntegrator()
print("Conexión exitosa:", ai.is_connected())