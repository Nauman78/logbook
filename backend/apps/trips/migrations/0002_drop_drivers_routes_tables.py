# Drop orphaned drivers and routes tables after removing those apps

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0001_add_trip_log"),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS routes_route; DROP TABLE IF EXISTS drivers_driver;",
            migrations.RunSQL.noop,
        ),
    ]
