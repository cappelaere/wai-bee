"""Summary Agent for aggregating all agent outputs.

This module provides the SummaryAgent class that collects results from all
agents, calculates final scores, and generates CSV reports with statistics.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional
from collections import Counter

from utils.score_calculator import load_agent_scores, calculate_final_score, load_weights


class SummaryAgent:
    """Agent for summarizing and aggregating all agent outputs.
    
    This agent collects results from all analysis agents, calculates final
    weighted scores, and generates CSV reports with statistics.
    
    Attributes:
        outputs_dir: Base outputs directory.
        scholarship_folder: Path to scholarship configuration folder.
    """
    
    def __init__(self, outputs_dir: Path, scholarship_folder: Path):
        """Initialize Summary Agent.
        
        Args:
            outputs_dir: Base outputs directory (e.g., Path("outputs")).
            scholarship_folder: Path to scholarship folder (e.g., Path("data/Delaney_Wings")).
        """
        self.logger = logging.getLogger(__name__)
        self.outputs_dir = outputs_dir
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        
        # Load weights configuration
        self.weights_config = load_weights(scholarship_folder)
        
        self.logger.info(f"Initialized SummaryAgent for {self.scholarship_name}")
    
    def collect_applicant_data(self, wai_number: str) -> Optional[dict]:
        """Collect all data for a single applicant.
        
        Args:
            wai_number: WAI application number.
            
        Returns:
            Dictionary with applicant data, or None if application data not found.
        """
        # Load application data for name and location
        # File is now: outputs/{scholarship}/{WAI}/application_data.json
        wai_dir = self.outputs_dir / self.scholarship_name / wai_number
        if not wai_dir.exists():
            self.logger.warning(f"WAI directory not found for WAI {wai_number}")
            return None
        
        app_file = wai_dir / "application_data.json"
        if not app_file.exists():
            self.logger.warning(f"Application data not found for WAI {wai_number}")
            return None
        
        try:
            with open(app_file, 'r') as f:
                app_data = json.load(f)
            
            # Extract applicant info (fields are at top level in ApplicationData model)
            name = app_data.get('name', 'Unknown')
            city = app_data.get('city', 'Unknown')
            state = app_data.get('state')  # Optional field for US applicants
            country = app_data.get('country', 'Unknown')
            
            # Load all agent scores
            scores = load_agent_scores(self.outputs_dir, self.scholarship_name, wai_number)
            
            # Calculate final weighted score
            final_result = calculate_final_score(
                application_score=scores['application'],
                recommendation_score=scores['recommendation'],
                resume_score=scores.get('resume'),
                essay_score=scores['essay'],
                weights_config=self.weights_config
            )
            
            return {
                'wai_number': wai_number,
                'name': name,
                'city': city,
                'state': state,  # Include state in returned data
                'country': country,
                'application_score': scores['application'] or 0,
                'recommendation_score': scores['recommendation'] or 0,
                'resume_score': scores.get('resume') or 0,
                'essay_score': scores['essay'] or 0,
                'final_score': final_result['final_score'],
                'complete': final_result['complete']
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting data for WAI {wai_number}: {e}")
            return None
    
    def generate_summary_csv(
        self,
        output_file: Path,
        wai_numbers: Optional[list[str]] = None
    ) -> dict:
        """Generate CSV summary of all applicants.
        
        Args:
            output_file: Path to output CSV file.
            wai_numbers: Optional list of WAI numbers to process.
                        If None, processes all found applications.
            
        Returns:
            Dictionary with statistics.
        """
        self.logger.info("="*60)
        self.logger.info("Generating Summary CSV")
        self.logger.info("="*60)
        
        # Get list of WAI numbers if not provided
        if wai_numbers is None:
            # Use unified output structure: outputs/{scholarship}/{WAI}/
            scholarship_dir = self.outputs_dir / self.scholarship_name
            if scholarship_dir.exists():
                wai_dirs = [d for d in scholarship_dir.iterdir() if d.is_dir()]
                wai_numbers = [d.name for d in wai_dirs]
            else:
                self.logger.error(f"Scholarship directory not found: {scholarship_dir}")
                return {}
        
        self.logger.info(f"Processing {len(wai_numbers)} applications")
        
        # Collect data for all applicants
        applicants = []
        for wai_number in wai_numbers:
            data = self.collect_applicant_data(wai_number)
            if data:
                applicants.append(data)
        
        self.logger.info(f"Collected data for {len(applicants)} applicants")
        
        # Sort by final score (descending)
        applicants.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Write CSV
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'rank',
                'wai_number',
                'name',
                'city',
                'state',
                'country',
                'application_score',
                'recommendation_score',
                'resume_score',
                'essay_score',
                'final_score',
                'complete'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for rank, applicant in enumerate(applicants, 1):
                row = {
                    'rank': rank,
                    **applicant
                }
                writer.writerow(row)
        
        self.logger.info(f"Saved CSV to: {output_file}")
        
        # Calculate statistics
        stats = self._calculate_statistics(applicants)
        
        return stats
    
    def _calculate_statistics(self, applicants: list[dict]) -> dict:
        """Calculate statistics from applicant data.
        
        Args:
            applicants: List of applicant dictionaries.
            
        Returns:
            Dictionary with statistics.
        """
        if not applicants:
            return {}
        
        # Extract scores
        final_scores = [a['final_score'] for a in applicants]
        app_scores = [a['application_score'] for a in applicants if a['application_score'] > 0]
        rec_scores = [a['recommendation_score'] for a in applicants if a['recommendation_score'] > 0]
        resume_scores = [a.get('resume_score', 0) for a in applicants if a.get('resume_score', 0) > 0]
        essay_scores = [a['essay_score'] for a in applicants if a['essay_score'] > 0]
        
        # Calculate percentiles
        final_scores_sorted = sorted(final_scores)
        n = len(final_scores_sorted)
        
        def percentile(scores, p):
            if not scores:
                return 0
            k = (len(scores) - 1) * p / 100
            f = int(k)
            c = f + 1 if f < len(scores) - 1 else f
            return scores[f] + (k - f) * (scores[c] - scores[f])
        
        # Count locations
        cities = Counter(a['city'] for a in applicants)
        countries = Counter(a['country'] for a in applicants)
        
        # Count complete vs incomplete
        complete_count = sum(1 for a in applicants if a['complete'])
        incomplete_count = len(applicants) - complete_count
        
        stats = {
            'total_applicants': len(applicants),
            'complete_applications': complete_count,
            'incomplete_applications': incomplete_count,
            'final_score_stats': {
                'min': min(final_scores) if final_scores else 0,
                'max': max(final_scores) if final_scores else 0,
                'mean': sum(final_scores) / len(final_scores) if final_scores else 0,
                'p25': percentile(final_scores_sorted, 25),
                'p50': percentile(final_scores_sorted, 50),
                'p75': percentile(final_scores_sorted, 75),
                'p90': percentile(final_scores_sorted, 90)
            },
            'agent_score_stats': {
                'application': {
                    'count': len(app_scores),
                    'mean': sum(app_scores) / len(app_scores) if app_scores else 0
                },
                'recommendation': {
                    'count': len(rec_scores),
                    'mean': sum(rec_scores) / len(rec_scores) if rec_scores else 0
                },
                'resume': {
                    'count': len(resume_scores),
                    'mean': sum(resume_scores) / len(resume_scores) if resume_scores else 0
                },
                'essay': {
                    'count': len(essay_scores),
                    'mean': sum(essay_scores) / len(essay_scores) if essay_scores else 0
                }
            },
            'top_cities': dict(cities.most_common(10)),
            'top_countries': dict(countries.most_common(10))
        }
        
        return stats
    
    def generate_statistics_report(
        self,
        stats: dict,
        output_file: Path,
        template_file: Optional[Path] = None
    ) -> None:
        """Generate statistics report file using template.
        
        Args:
            stats: Statistics dictionary from _calculate_statistics.
            output_file: Path to output report file.
            template_file: Optional path to template file. If None, uses default.
        """
        from datetime import datetime
        
        if template_file is None:
            template_file = Path("templates/statistics_report_template.md")
        
        # Load template
        if not template_file.exists():
            self.logger.warning(f"Template not found: {template_file}, using simple format")
            self._generate_simple_report(stats, output_file)
            return
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Prepare template variables
        fs = stats['final_score_stats']
        total = stats['total_applicants']
        complete = stats['complete_applications']
        incomplete = stats['incomplete_applications']
        
        # Calculate score ranges
        final_scores = [a['final_score'] for a in stats.get('applicants', [])]
        count_excellent = sum(1 for s in final_scores if s >= 90)
        count_very_good = sum(1 for s in final_scores if 80 <= s < 90)
        count_good = sum(1 for s in final_scores if 70 <= s < 80)
        count_fair = sum(1 for s in final_scores if 60 <= s < 70)
        count_below_average = sum(1 for s in final_scores if s < 60)
        
        # Get weights
        weights = self.weights_config['weights']
        resume_weight = weights.get('resume')
        
        # Replace template variables
        replacements = {
            '{{scholarship_name}}': self.scholarship_name,
            '{{generated_date}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '{{total_applicants}}': str(total),
            '{{complete_applications}}': str(complete),
            '{{complete_percentage}}': f"{complete/total*100:.1f}" if total > 0 else "0",
            '{{incomplete_applications}}': str(incomplete),
            '{{incomplete_percentage}}': f"{incomplete/total*100:.1f}" if total > 0 else "0",
            '{{final_score_min}}': f"{fs['min']:.2f}",
            '{{final_score_max}}': f"{fs['max']:.2f}",
            '{{final_score_mean}}': f"{fs['mean']:.2f}",
            '{{final_score_p25}}': f"{fs['p25']:.2f}",
            '{{final_score_p50}}': f"{fs['p50']:.2f}",
            '{{final_score_p75}}': f"{fs['p75']:.2f}",
            '{{final_score_p90}}': f"{fs['p90']:.2f}",
            '{{count_excellent}}': str(count_excellent),
            '{{count_very_good}}': str(count_very_good),
            '{{count_good}}': str(count_good),
            '{{count_fair}}': str(count_fair),
            '{{count_below_average}}': str(count_below_average),
            '{{weight_application}}': f"{weights['application']['weight']*100:.0f}",
            '{{weight_recommendation}}': f"{weights['recommendation']['weight']*100:.0f}",
            '{{weight_resume}}': f"{(resume_weight['weight'] if resume_weight else 0.0)*100:.0f}",
            '{{weight_essay}}': f"{weights['essay']['weight']*100:.0f}",
            '{{application_count}}': str(stats['agent_score_stats']['application']['count']),
            '{{application_mean}}': f"{stats['agent_score_stats']['application']['mean']:.2f}",
            '{{recommendation_count}}': str(stats['agent_score_stats']['recommendation']['count']),
            '{{recommendation_mean}}': f"{stats['agent_score_stats']['recommendation']['mean']:.2f}",
            '{{resume_count}}': str(stats['agent_score_stats']['resume']['count']),
            '{{resume_mean}}': f"{stats['agent_score_stats']['resume']['mean']:.2f}",
            '{{essay_count}}': str(stats['agent_score_stats']['essay']['count']),
            '{{essay_mean}}': f"{stats['agent_score_stats']['essay']['mean']:.2f}",
        }
        
        # Apply replacements
        for key, value in replacements.items():
            template = template.replace(key, value)
        
        # Handle lists (cities and countries)
        # Replace {{#top_cities}}...{{/top_cities}} section
        cities_section = ""
        for i, (city, count) in enumerate(list(stats['top_cities'].items())[:10], 1):
            cities_section += f"{i}. **{city}** - {count} applicants\n"
        template = self._replace_section(template, 'top_cities', cities_section)
        
        countries_section = ""
        for i, (country, count) in enumerate(list(stats['top_countries'].items())[:10], 1):
            countries_section += f"{i}. **{country}** - {count} applicants\n"
        template = self._replace_section(template, 'top_countries', countries_section)
        
        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(template)
        
        self.logger.info(f"Saved statistics report to: {output_file}")
    
    def _replace_section(self, template: str, section_name: str, content: str) -> str:
        """Replace a template section with content.
        
        Args:
            template: Template string.
            section_name: Name of section to replace.
            content: Content to insert.
            
        Returns:
            Updated template string.
        """
        start_tag = f"{{{{#{section_name}}}}}"
        end_tag = f"{{{{/{section_name}}}}}"
        
        start_idx = template.find(start_tag)
        end_idx = template.find(end_tag)
        
        if start_idx == -1 or end_idx == -1:
            return template
        
        # Find the content between tags (to get the template line)
        section_start = start_idx + len(start_tag)
        section_template = template[section_start:end_idx].strip()
        
        # Replace the entire section
        return template[:start_idx] + content + template[end_idx + len(end_tag):]
    
    def _generate_simple_report(self, stats: dict, output_file: Path) -> None:
        """Generate simple statistics report without template.
        
        Args:
            stats: Statistics dictionary.
            output_file: Path to output file.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write(f"SCHOLARSHIP APPLICATION STATISTICS REPORT\n")
            f.write(f"Scholarship: {self.scholarship_name}\n")
            f.write("="*60 + "\n\n")
            
            # Overview
            f.write("OVERVIEW\n")
            f.write("-"*60 + "\n")
            f.write(f"Total Applicants: {stats['total_applicants']}\n")
            f.write(f"Complete Applications: {stats['complete_applications']}\n")
            f.write(f"Incomplete Applications: {stats['incomplete_applications']}\n\n")
            
            # Final Score Statistics
            f.write("FINAL SCORE STATISTICS\n")
            f.write("-"*60 + "\n")
            fs = stats['final_score_stats']
            f.write(f"Minimum: {fs['min']:.2f}\n")
            f.write(f"Maximum: {fs['max']:.2f}\n")
            f.write(f"Mean: {fs['mean']:.2f}\n")
            f.write(f"25th Percentile: {fs['p25']:.2f}\n")
            f.write(f"50th Percentile (Median): {fs['p50']:.2f}\n")
            f.write(f"75th Percentile: {fs['p75']:.2f}\n")
            f.write(f"90th Percentile: {fs['p90']:.2f}\n\n")
            
            # Agent Score Statistics
            f.write("AGENT SCORE STATISTICS\n")
            f.write("-"*60 + "\n")
            for agent, agent_stats in stats['agent_score_stats'].items():
                f.write(f"{agent.capitalize()}:\n")
                f.write(f"  Count: {agent_stats['count']}\n")
                f.write(f"  Mean: {agent_stats['mean']:.2f}\n")
            f.write("\n")
            
            # Geographic Distribution
            f.write("TOP 10 CITIES\n")
            f.write("-"*60 + "\n")
            for city, count in stats['top_cities'].items():
                f.write(f"{city}: {count}\n")
            f.write("\n")
            
            f.write("TOP 10 COUNTRIES\n")
            f.write("-"*60 + "\n")
            for country, count in stats['top_countries'].items():
                f.write(f"{country}: {count}\n")
            f.write("\n")
        
        self.logger.info(f"Saved statistics report to: {output_file}")

# Made with Bob
