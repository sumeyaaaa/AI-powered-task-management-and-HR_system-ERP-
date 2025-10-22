import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
    SUPERADMIN_EMAIL = os.getenv('SUPERADMIN_EMAIL')
    SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD')
    
    def __init__(self):
        print("🔧 Frontend Configuration:")
        print(f"   BACKEND_URL: {self.BACKEND_URL}")
        print(f"   SUPERADMIN_EMAIL: {self.SUPERADMIN_EMAIL}")
        print(f"   SUPERADMIN_PASSWORD: {'*' * len(self.SUPERADMIN_PASSWORD) if self.SUPERADMIN_PASSWORD else 'Not set'}")

config = Config()