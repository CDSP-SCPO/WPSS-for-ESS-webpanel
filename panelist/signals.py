
def post_delete_profile(sender, instance, *args, **kwargs):

    if instance.user:
        instance.user.delete()
