from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# This is the one and only Profile model for your project.
class Profile(models.Model):
    # The OneToOneField links this profile to exactly one User.
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # These fields store the streak data.
    streak_count = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# This signal automatically creates a Profile when a new User registers.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# This signal saves the profile whenever the user object is saved.
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # This handles users that existed before this signal was created.
        Profile.objects.create(user=instance)