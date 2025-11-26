from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")  # força usar este ficheiro

print("GEMINI_API_KEY via get =", os.environ.get("GEMINI_API_KEY"))
print("Variáveis com 'KEY' no nome:")
for k, v in os.environ.items():
    if "KEY" in k.upper():
        print(repr(k), "=", v)