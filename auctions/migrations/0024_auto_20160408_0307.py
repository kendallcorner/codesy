# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-08 03:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0023_auto_20160408_0114'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='confirmation',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='payout',
            name='confirmation',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]