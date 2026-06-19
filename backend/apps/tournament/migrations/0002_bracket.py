"""Add tournament winner, participant elimination flag and bracket models."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tournament', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='winner',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tournaments_won',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='tournamentparticipant',
            name='is_eliminated',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='TournamentRound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rounds', to='tournament.tournament')),
            ],
            options={
                'verbose_name': 'Tournament Round',
                'verbose_name_plural': 'Tournament Rounds',
                'ordering': ['number'],
                'unique_together': {('tournament', 'number')},
            },
        ),
        migrations.CreateModel(
            name='TournamentMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveIntegerField(default=0)),
                ('player1_score', models.IntegerField(default=0)),
                ('player2_score', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('live', 'Live'), ('completed', 'Completed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('player1', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tournament_matches_as_p1', to=settings.AUTH_USER_MODEL)),
                ('player2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tournament_matches_as_p2', to=settings.AUTH_USER_MODEL)),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tournament_matches_won', to=settings.AUTH_USER_MODEL)),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='tournament.tournamentround')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='tournament.tournament')),
            ],
            options={
                'verbose_name': 'Tournament Match',
                'verbose_name_plural': 'Tournament Matches',
                'ordering': ['round__number', 'position'],
            },
        ),
    ]
