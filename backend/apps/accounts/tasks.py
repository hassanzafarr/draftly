from celery import shared_task


@shared_task
def reset_demo_data_task():
    """Wipe + reseed the public demo org's data. Dispatched async so demo login never blocks on it."""
    from .demo import get_or_create_demo, reset_demo_data

    org, user = get_or_create_demo()
    reset_demo_data(org, user)
