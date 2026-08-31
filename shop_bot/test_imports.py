import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

modules = [
    'config.settings',
    'core.database',
    'core.scheduler',
    'core.force_join',
    'core.webhook_server',
    'models',
    'repositories.base_repository',
    'repositories.user_repository',
    'repositories.product_repository',
    'repositories.inventory_repository',
    'repositories.order_repository',
    'repositories.ticket_repository',
    'services.order_service',
    'services.payment_service',
    'services.notification_service',
    'services.referral_service',
    'services.ticket_service',
    'utils.keyboards',
    'utils.helpers',
    'utils.decorators',
    'handlers.user.start',
    'handlers.user.shop',
    'handlers.user.profile',
    'handlers.user.phone',
    'handlers.user.tutorials',
    'handlers.admin.dashboard',
    'handlers.admin.products',
    'handlers.admin.inventory',
    'handlers.admin.discounts',
    'handlers.admin.tutorials',
    'handlers.admin.settings',
    'core.dispatcher',
    'core.bot',
]

errors = []
for mod in modules:
    try:
        __import__(mod)
        print(f"[OK] {mod}")
    except Exception as e:
        print(f"[ERROR] {mod}: {e}")
        errors.append((mod, str(e)))

print("\n" + "="*50)
if errors:
    print(f"ERRORS: {len(errors)}")
    for m, e in errors:
        print(f"  - {m}: {e}")
else:
    print(f"All {len(modules)} modules imported OK!")
