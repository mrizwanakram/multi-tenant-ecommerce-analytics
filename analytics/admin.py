from django.contrib import admin
from .models import Tenant, Product, Customer, Order, OrderItem, PriceHistory, StockEvent, PriceEvent, IngestionJob, MaterializedView, ExportJob

# Register models for admin interface
admin.site.register(Tenant)
admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PriceHistory)
admin.site.register(StockEvent)
admin.site.register(PriceEvent)
admin.site.register(IngestionJob)
admin.site.register(MaterializedView)
admin.site.register(ExportJob)