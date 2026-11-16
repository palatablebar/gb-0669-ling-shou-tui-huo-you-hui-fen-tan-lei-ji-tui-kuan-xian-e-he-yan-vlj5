class DomainError(ValueError):
    def __init__(self, code, detail, status=422):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(detail)
