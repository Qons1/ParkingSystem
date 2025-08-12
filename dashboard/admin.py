from django.contrib import admin
from .models import ParkingSlot, ParkingLog, PWDRequest, FeeConfig, Payment, Violation

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ('slot_id', 'slot_type', 'is_occupied', 'assigned_user')
    list_filter = ('slot_type', 'is_occupied')
    search_fields = ('slot_id',)

@admin.register(ParkingLog)
class ParkingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'entry_time', 'exit_time', 'payment_status')
    list_filter = ('payment_status',)
    search_fields = ('user__username', 'slot__slot_id')

@admin.register(PWDRequest)
class PWDRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status')
    list_filter = ('status',)
    search_fields = ('user__username',)

@admin.register(FeeConfig)
class FeeConfigAdmin(admin.ModelAdmin):
    list_display = ('base_fee', 'base_hours', 'succeeding_fee')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'log', 'amount', 'method', 'status', 'timestamp')
    list_filter = ('method', 'status')
    search_fields = ('user__username',)

@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ('user', 'slot', 'timestamp')
    search_fields = ('user__username', 'slot__slot_id')