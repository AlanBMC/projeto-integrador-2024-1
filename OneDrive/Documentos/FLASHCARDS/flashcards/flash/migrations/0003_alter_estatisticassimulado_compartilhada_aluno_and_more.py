# Generated by Django 5.0.1 on 2024-03-17 23:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flash', '0002_alter_simulados_alternativa_a_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estatisticassimulado_compartilhada',
            name='aluno',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estatisticas_aluno', to='flash.usuario'),
        ),
        migrations.AlterField(
            model_name='estatisticassimulado_compartilhada',
            name='prof',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estatisticas_prof', to='flash.usuario'),
        ),
    ]
