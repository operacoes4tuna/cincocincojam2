import requests
import json
from django.conf import settings
from datetime import datetime, timedelta

class OpenPixService:
    BASE_URL = "https://api.openpix.com.br/api/v1"
    
    def __init__(self):
        self.headers = {
            "Authorization": settings.OPENPIX_TOKEN,
            "Content-Type": "application/json"
        }
    
    def create_charge(self, course, user, correlation_id=None):
        """
        Cria uma cobrança Pix para um curso
        """
        expiration_date = datetime.now() + timedelta(minutes=60)
        
        payload = {
            "correlationID": correlation_id or f"course-{course.id}-{user.id}-{int(datetime.now().timestamp())}",
            "value": int(course.price * 100),  # Valor em centavos
            "comment": f"Pagamento do curso: {course.title}",
            "customer": {
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "phone": user.phone if hasattr(user, 'phone') else "",
                "taxID": user.cpf if hasattr(user, 'cpf') else ""
            },
            "expiresIn": 3600,  # 1 hora em segundos
            "additionalInfo": [
                {
                    "key": "Curso",
                    "value": course.title
                }
            ]
        }
        
        response = requests.post(
            f"{self.BASE_URL}/charge",
            headers=self.headers,
            data=json.dumps(payload)
        )
        
        return response.json()
    
    def get_charge_status(self, correlation_id):
        """
        Verifica o status de uma cobrança
        """
        response = requests.get(
            f"{self.BASE_URL}/charge/{correlation_id}",
            headers=self.headers
        )
        
        return response.json()
