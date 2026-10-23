class AppError(Exception):
    status_code = 400
    default_detail = "Application error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    default_detail = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    default_detail = "Resource already exists"


class ValidationAppError(AppError):
    status_code = 400
    default_detail = "Invalid request"


class AuthenticationError(AppError):
    status_code = 401
    default_detail = "Could not validate credentials"


class PermissionDeniedError(AppError):
    status_code = 403
    default_detail = "You do not have permission to perform this action"


class EmailDeliveryError(Exception):
    pass
