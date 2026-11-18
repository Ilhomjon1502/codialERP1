from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0006_inbox'),
    ]

    operations = [
        migrations.AddField(
            model_name='inboxlead',
            name='outcome',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Hisobot holati'),
        ),
    ]
