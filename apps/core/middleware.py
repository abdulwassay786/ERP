class CompanyMiddleware:
    """Middleware to attach company to request"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'company'):
            request.company = request.user.company
        else:
            request.company = None
        
        response = self.get_response(request)
        return response
