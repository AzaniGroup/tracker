from django.db import migrations
from decimal import Decimal

def set_logistics_percentage_only(apps, schema_editor):
    FeeType = apps.get_model('projects', 'FeeType')
    for ft in FeeType.objects.all():
        if 'logistics' in ft.name.lower():
            ft.default_percentage = Decimal('10.00')
        else:
            ft.default_percentage = Decimal('0.00')
        ft.save()

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0020_feetype_default_percentage'),
    ]

    operations = [
        migrations.RunPython(set_logistics_percentage_only),
    ]
