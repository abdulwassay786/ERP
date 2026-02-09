from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class CompanyScopedMixin(LoginRequiredMixin):
    """Mixin to ensure views are scoped to user's company"""
    
    def get_queryset(self):
        """Filter queryset by user's company"""
        queryset = super().get_queryset()
        if self.request.company:
            return queryset.filter(company=self.request.company)
        return queryset.none()

    def form_valid(self, form):
        """Automatically set company on form save"""
        if hasattr(form.instance, 'company'):
            form.instance.company = self.request.company
        return super().form_valid(form)


class CompanyAccessMixin(LoginRequiredMixin):
    """Mixin to verify object belongs to user's company"""
    
    def get_object(self, queryset=None):
        """Ensure object belongs to user's company"""
        obj = super().get_object(queryset)
        if hasattr(obj, 'company') and obj.company != self.request.company:
            raise PermissionDenied("You don't have permission to access this object.")
        return obj


class CompanyRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user belongs to a company"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.company:
             raise PermissionDenied("You must belong to a company to access this page.")
        return super().dispatch(request, *args, **kwargs)
