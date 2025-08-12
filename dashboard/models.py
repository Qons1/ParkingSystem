from django.db import models
from django.conf import settings

# 1. Parking Slot
class ParkingSlot(models.Model):
    SLOT_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('pwd', 'PWD'),
        ('bike', 'Bike'),
    ]
    slot_id = models.CharField(max_length=20, unique=True)
    slot_type = models.CharField(max_length=10, choices=SLOT_TYPE_CHOICES, default='regular')
    is_occupied = models.BooleanField(default=False)
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_slots')

    def __str__(self):
        return f"{self.slot_id} ({self.get_slot_type_display()})"

# 2. Parking Log (Entry/Exit)
class ParkingLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    photo_url = models.URLField(blank=True)  # URL to Firebase Storage or similar
    payment_status = models.CharField(max_length=20, choices=[('unpaid', 'Unpaid'), ('paid', 'Paid')], default='unpaid')

    def __str__(self):
        return f"{self.user.username} - {self.slot} ({self.entry_time})"

# 3. PWD Request
class PWDRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_id_image = models.URLField()  # Or use models.ImageField if storing locally
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

# 4. Fee Configuration
class FeeConfig(models.Model):
    base_fee = models.DecimalField(max_digits=8, decimal_places=2, help_text="Base fee (e.g., ₱50)")
    base_hours = models.PositiveIntegerField(help_text="Number of hours covered by base fee")
    succeeding_fee = models.DecimalField(max_digits=8, decimal_places=2, help_text="Fee per succeeding hour")

    def __str__(self):
        return f"₱{self.base_fee} for {self.base_hours}h, ₱{self.succeeding_fee}/h after"

# 5. Payment
class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    log = models.ForeignKey(ParkingLog, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=20, choices=[('gcash', 'GCash'), ('cash', 'Cash'), ('other', 'Other')])
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"

# 6. (Optional) Violation
class Violation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.SET_NULL, null=True)
    photo_url = models.URLField(blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Violation by {self.user.username} at {self.timestamp}"