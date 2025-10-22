from datetime import datetime
from typing import Optional, List, Dict, Any

class Employee:
    def __init__(self, 
                 name: str,
                 email: str,
                 role: str,
                 skills: List[str] = None,
                 is_active: bool = True,
                 created_at: Optional[str] = None,
                 id: Optional[int] = None):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.skills = skills or []
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'skills': self.skills,
            'is_active': self.is_active,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Employee':
        return cls(
            id=data.get('id'),
            name=data['name'],
            email=data['email'],
            role=data['role'],
            skills=data.get('skills', []),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at')
        )