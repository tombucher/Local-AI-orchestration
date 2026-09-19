"""
Exceptions personnalisées pour l'application Orchestrateur IA

Ce module définit les exceptions spécifiques à l'application pour une gestion
d'erreurs centralisée et cohérente.
"""
from fastapi import HTTPException, status

class AppException(Exception):
    """
    Classe de base pour toutes les exceptions personnalisées de l'application

    Args:
        message (str): Message d'erreur détaillé
        error_code (str): Code d'erreur unique pour l'identification
        status_code (int): Code HTTP associé
        details (dict): Détails supplémentaires sur l'erreur
    """
    def __init__(self, message: str, error_code: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convertit l'exception en dictionnaire pour la réponse API"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }

class EntityNotFoundError(AppException):
    """
    Exception pour les entités non trouvées (404)

    Args:
        entity_type (str): Type d'entité (ex: "Project", "Task")
        entity_id (str): Identifiant de l'entité
    """
    def __init__(self, entity_type: str, entity_id: str):
        message = f"{entity_type} with ID {entity_id} not found"
        super().__init__(
            message=message,
            error_code="entity_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": entity_id}
        )

class AgentProcessingError(AppException):
    """
    Exception pour les erreurs de traitement des agents IA

    Args:
        task_id (str): Identifiant de la tâche concernée
        agent_type (str): Type d'agent (ex: "code_generator", "web_research")
        original_error (str): Erreur originale
    """
    def __init__(self, task_id: str, agent_type: str, original_error: str):
        message = f"Agent {agent_type} failed to process task {task_id}"
        super().__init__(
            message=message,
            error_code="agent_processing_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "task_id": task_id,
                "agent_type": agent_type,
                "original_error": str(original_error)
            }
        )

class DatabaseError(AppException):
    """
    Exception pour les erreurs de base de données

    Args:
        operation (str): Opération en cours (ex: "create", "update")
        entity_type (str): Type d'entité concernée
        original_error (str): Erreur originale
    """
    def __init__(self, operation: str, entity_type: str, original_error: str):
        message = f"Database error during {operation} of {entity_type}"
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "operation": operation,
                "entity_type": entity_type,
                "original_error": str(original_error)
            }
        )

class ValidationError(AppException):
    """
    Exception pour les erreurs de validation

    Args:
        field (str): Champ concerné par l'erreur
        error_details (str): Détails de l'erreur de validation
    """
    def __init__(self, field: str, error_details: str):
        message = f"Validation error for field {field}"
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={
                "field": field,
                "error_details": error_details
            }
        )

class AuthenticationError(AppException):
    """
    Exception pour les erreurs d'authentification

    Args:
        error_type (str): Type d'erreur (ex: "invalid_credentials", "expired_token")
    """
    def __init__(self, error_type: str):
        message = "Authentication failed"
        error_codes = {
            "invalid_credentials": "invalid_credentials",
            "expired_token": "expired_token",
            "invalid_token": "invalid_token",
            "permission_denied": "permission_denied"
        }
        super().__init__(
            message=message,
            error_code=error_codes.get(error_type, "authentication_error"),
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"error_type": error_type}
        )

class AuthorizationError(AppException):
    """
    Exception pour les erreurs d'autorisation

    Args:
        resource_type (str): Type de ressource concernée
        action (str): Action tentée
    """
    def __init__(self, resource_type: str, action: str):
        message = f"Permission denied to {action} on {resource_type}"
        super().__init__(
            message=message,
            error_code="authorization_error",
            status_code=status.HTTP_403_FORBIDDEN,
            details={
                "resource_type": resource_type,
                "action": action
            }
        )

class ConflictError(AppException):
    """
    Exception pour les conflits de ressources

    Args:
        resource_type (str): Type de ressource
        conflict_details (str): Détails du conflit
    """
    def __init__(self, resource_type: str, conflict_details: str):
        message = f"Conflict with existing {resource_type}"
        super().__init__(
            message=message,
            error_code="conflict_error",
            status_code=status.HTTP_409_CONFLICT,
            details={
                "resource_type": resource_type,
                "conflict_details": conflict_details
            }
        )

class RateLimitError(AppException):
    """
    Exception pour les erreurs de rate limiting

    Args:
        limit (int): Limite autorisée
        retry_after (int): Temps avant réessai (secondes)
    """
    def __init__(self, limit: int, retry_after: int):
        message = f"Rate limit exceeded. Try again in {retry_after} seconds"
        super().__init__(
            message=message,
            error_code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "limit": limit,
                "retry_after": retry_after
            }
        )