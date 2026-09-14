# Generated migration for Project model update

from django.db import migrations, models


def migrate_rolled_over_to_linked(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    for p in Project.objects.all():
        if hasattr(p, 'rolled_over_from') and p.rolled_over_from:
            p.linked_projects.add(p.rolled_over_from)


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0021_set_logistics_percentage_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='year',
            field=models.PositiveIntegerField(default=2025, verbose_name='Project Year'),
        ),
        migrations.AddField(
            model_name='project',
            name='linked_project_raw',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Linked Project (Raw Text)'),
        ),
        migrations.AddField(
            model_name='project',
            name='linked_projects',
            field=models.ManyToManyField(blank=True, related_name='linked_by_projects', to='projects.project', verbose_name='Linked Projects'),
        ),
        migrations.RunPython(migrate_rolled_over_to_linked, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='project',
            name='rolled_over_from',
        ),
    ]
