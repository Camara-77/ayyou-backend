import json
from django.core.management.base import BaseCommand
from apps.telemetry.ml.simulate_feed import run_feed_simulation_for_profile, run_all_phase_6_scenarios


class Command(BaseCommand):
    help = "Exécute la simulation d'ordonnancement du Feed par LightGBM V2 sans modifier le Feed de production."

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='ID d\'un utilisateur spécifique pour la simulation'
        )
        parser.add_argument(
            '--session-id',
            type=str,
            default=None,
            help='Session ID d\'un visiteur anonyme pour la simulation'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Exporter le résultat sous forme JSON structuré'
        )

    def handle(self, *args, **options):
        if options['user_id'] or options['session_id']:
            scenario_name = f"Simulation Manuelle (User #{options['user_id'] or 'Anon'}, Session {options['session_id'] or 'N/A'})"
            results = {
                scenario_name: run_feed_simulation_for_profile(
                    user_id=options['user_id'],
                    session_id=options['session_id'],
                    scenario_name=scenario_name
                )
            }
        else:
            results = run_all_phase_6_scenarios()

        if options['json']:
            self.stdout.write(json.dumps(results, indent=2, ensure_ascii=False))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("========================================"))
        self.stdout.write(self.style.MIGRATE_HEADING("AYYOU — FEED IA SIMULATION (PHASE 6)"))
        self.stdout.write(self.style.MIGRATE_HEADING("Model: recommender_lgbm_v2"))
        self.stdout.write(self.style.MIGRATE_HEADING("Candidates: 8 vidéos du Feed actuel"))
        self.stdout.write(self.style.MIGRATE_HEADING("========================================\n"))

        for scenario_name, data in results.items():
            self.stdout.write(self.style.SUCCESS(f"--- {scenario_name} ---"))
            self.stdout.write(f"Nombre de candidats : {data['candidates_count']}")
            
            metrics = data['metrics']
            self.stdout.write(f"Overlap Top 3 : {metrics['overlap_top_3']}/3 | Overlap Top 5 : {metrics['overlap_top_5']}/5")
            self.stdout.write(f"Vidéos déplacées : {metrics['moved_videos_count']} | Vidéos inchangées : {metrics['unchanged_videos_count']}")
            self.stdout.write(f"Déplacement moyen : {metrics['avg_position_shift']} positions")
            self.stdout.write(f"Corrélation Spearman : {metrics['spearman_rank_correlation']} | Kendall Tau : {metrics['kendall_tau_correlation']}")
            self.stdout.write("")

            # Tableau de comparaison
            self.stdout.write(f"{'Vidéo':<8} | {'Pos Actuelle':<12} | {'Pos IA':<8} | {'Variation':<10} | {'Score IA':<8} | {'Plat':<20} | {'Prix (€)':<8}")
            self.stdout.write("-" * 85)
            for item in data['comparison_table']:
                var_str = f"+{item['variation']}" if item['variation'] > 0 else str(item['variation'])
                self.stdout.write(
                    f"{item['publication_id']:<8} | {item['current_position']:<12} | {item['ai_position']:<8} | {var_str:<10} | {item['predicted_score']:<8.4f} | {item['dish_name'][:20]:<20} | {item['dish_price']:<8.2f}"
                )
            self.stdout.write("\n" + "=" * 80 + "\n")
