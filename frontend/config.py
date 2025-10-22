import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
    SUPERADMIN_EMAIL = os.getenv('SUPERADMIN_EMAIL')
    SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD')

config = Config()