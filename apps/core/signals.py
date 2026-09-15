from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs):
    """إعداد SQLite لتزامن أفضل بين أجهزة العيادة مع حماية سلامة العلاقات."""
    if connection.vendor != "sqlite" or connection.settings_dict.get("NAME") == ":memory:":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=20000;")
