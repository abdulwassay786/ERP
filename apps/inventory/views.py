from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Product, ItemGroup
from .forms import ProductForm, ItemGroupForm


class ProductListView(LoginRequiredMixin, ListView):
    """List all products for the user's company"""
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        """Filter products by user's company and optional filters"""
        if not self.request.user.company:
            return Product.objects.none()
            
        queryset = Product.objects.filter(company=self.request.user.company, is_deleted=False).select_related('group')
        
        # Filter by group
        group_id = self.request.GET.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
            
        # Search by name or SKU
        query = self.request.GET.get('q')
        if query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=query) | 
                Q(sku__icontains=query)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.company:
            context['groups'] = ItemGroup.objects.filter(company=self.request.user.company, is_deleted=False)
        
        # Pass current filters to context for preserving state
        context['selected_group_id'] = self.request.GET.get('group')
        if context['selected_group_id']:
            try:
                context['selected_group_id'] = int(context['selected_group_id'])
            except ValueError:
                context['selected_group_id'] = None
                
        context['search_query'] = self.request.GET.get('q', '')
        return context



class ProductDetailView(LoginRequiredMixin, DetailView):
    """View product details"""
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        """Only allow viewing products from user's company"""
        if self.request.user.company:
            return Product.objects.filter(company=self.request.user.company, is_deleted=False).select_related('group')
        return Product.objects.none()


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Create a new product"""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:list')

    def get_form(self, form_class=None):
        """Filter item groups by company"""
        form = super().get_form(form_class)
        if self.request.user.company:
            form.fields['group'].queryset = ItemGroup.objects.filter(
                company=self.request.user.company, 
                is_deleted=False
            )
        return form

    def form_valid(self, form):
        """Set the company before saving"""
        form.instance.company = self.request.user.company
        messages.success(self.request, 'Product created successfully.')
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing product"""
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:list')

    def get_queryset(self):
        """Only allow editing products from user's company"""
        if self.request.user.company:
            return Product.objects.filter(company=self.request.user.company, is_deleted=False)
        return Product.objects.none()

    def get_form(self, form_class=None):
        """Filter item groups by company"""
        form = super().get_form(form_class)
        if self.request.user.company:
            form.fields['group'].queryset = ItemGroup.objects.filter(
                company=self.request.user.company, 
                is_deleted=False
            )
        return form

    def form_valid(self, form):
        messages.success(self.request, 'Product updated successfully.')
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a product"""
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:list')

    def get_queryset(self):
        """Only allow deleting products from user's company"""
        if self.request.user.company:
            return Product.objects.filter(company=self.request.user.company, is_deleted=False)
        return Product.objects.none()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.soft_delete()

        if request.headers.get("HX-Request"):
            from django.http import HttpResponse
            return HttpResponse("")

        messages.success(request, "Product deleted successfully.")
        return redirect(self.success_url)

# Item Group Views

class ItemGroupListView(LoginRequiredMixin, ListView):
    """List all item groups"""
    model = ItemGroup
    template_name = 'inventory/itemgroup_list.html'
    context_object_name = 'groups'
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.company:
            return ItemGroup.objects.filter(company=self.request.user.company, is_deleted=False)
        return ItemGroup.objects.none()


class ItemGroupCreateView(LoginRequiredMixin, CreateView):
    """Create a new item group"""
    model = ItemGroup
    form_class = ItemGroupForm
    template_name = 'inventory/itemgroup_form.html'
    success_url = reverse_lazy('inventory:group_list')

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        messages.success(self.request, 'Item Group created successfully.')
        return super().form_valid(form)


class ItemGroupUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing item group"""
    model = ItemGroup
    form_class = ItemGroupForm
    template_name = 'inventory/itemgroup_form.html'
    success_url = reverse_lazy('inventory:group_list')

    def get_queryset(self):
        if self.request.user.company:
            return ItemGroup.objects.filter(company=self.request.user.company, is_deleted=False)
        return ItemGroup.objects.none()

    def form_valid(self, form):
        messages.success(self.request, 'Item Group updated successfully.')
        return super().form_valid(form)


class ItemGroupDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete an item group"""
    model = ItemGroup
    success_url = reverse_lazy('inventory:group_list')

    def get_queryset(self):
        if self.request.user.company:
            return ItemGroup.objects.filter(company=self.request.user.company, is_deleted=False)
        return ItemGroup.objects.none()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.soft_delete()
        
        if request.headers.get("HX-Request"):
            from django.http import HttpResponse
            return HttpResponse(status=204)
            
        messages.success(request, 'Item Group deleted successfully.')
        return redirect(self.success_url)


@login_required
def get_product_price(request, product_id):
    """API endpoint to get product price"""
    from django.http import JsonResponse
    
    try:
        product = Product.objects.get(
            id=product_id,
            company=request.user.company,
            is_deleted=False
        )
        return JsonResponse({
            'success': True,
            'unit_price': str(product.unit_price),
            'name': product.name,
            'sku': product.sku
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
