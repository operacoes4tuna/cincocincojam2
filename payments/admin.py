from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'enrollment_info', 'amount', 'status', 'payment_date', 'created_at']
    list_filter = ['status', 'payment_date', 'created_at']
    search_fields = ['enrollment__student__email', 'enrollment__course__title', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def enrollment_info(self, obj):
        return f"{obj.enrollment.student.email} - {obj.enrollment.course.title}"
    
    enrollment_info.short_description = _('Matrícula')
