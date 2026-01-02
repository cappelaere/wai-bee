"""Data service for loading and processing scholarship analysis data.

This module provides functions to load and aggregate analysis data from
the outputs directory for a specific scholarship.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import json
import logging
import os
import csv
from pathlib import Path
from typing import List, Optional, Dict, Any
import statistics

from .logging_config import setup_logging

logger = setup_logging("data_service")

class DataService:
    """Service for loading scholarship analysis data."""
    
    def __init__(self, scholarship_name: str, base_output_dir: str = "outputs"):
        """Initialize the data service.
        
        Args:
            scholarship_name: Name of the scholarship (e.g., "Delaney_Wings")
            base_output_dir: Base directory containing output files
        """
        self.scholarship_name = scholarship_name
        self.base_output_dir = Path(base_output_dir)
        self.scholarship_dir = self.base_output_dir / scholarship_name
        
        if not self.scholarship_dir.exists():
            raise ValueError(f"Scholarship directory not found: {self.scholarship_dir}")
        
        logger.info(f"DataService initialized for scholarship: {scholarship_name}")
    
    def load_scholarship_info(self) -> Optional[Dict[str, Any]]:
        """Load scholarship information from scholarship.json.
        
        Returns:
            Dictionary containing scholarship information, or None if not found
        """
        scholarship_file = Path("data") / self.scholarship_name / "scholarship.json"
        if not scholarship_file.exists():
            logger.warning(f"Scholarship info file not found: {scholarship_file}")
            return None
        
        try:
            with open(scholarship_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scholarship info: {e}")
            return None
    
    def load_agents_config(self) -> Optional[Dict[str, Any]]:
        """Load agents configuration from agents.json.
        
        Returns:
            Dictionary containing agents configuration, or None if not found
        """
        agents_file = Path("data") / self.scholarship_name / "agents.json"
        if not agents_file.exists():
            logger.warning(f"Agents config file not found: {agents_file}")
            return None
        
        try:
            with open(agents_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading agents config: {e}")
            return None
    
    def get_all_wai_numbers(self) -> List[str]:
        """Get list of all WAI numbers with analysis data.
        
        Returns:
            List of WAI numbers as strings
        """
        logger.debug(f"Scanning directory: {self.scholarship_dir}")
        
        wai_numbers = []
        all_items = list(self.scholarship_dir.iterdir())
        logger.debug(f"Found {len(all_items)} items in directory")
        
        dirs_found = [item for item in all_items if item.is_dir()]
        logger.debug(f"Found {len(dirs_found)} directories: {[d.name for d in dirs_found[:10]]}")
        
        for wai_dir in dirs_found:
            analysis_file = wai_dir / "application_analysis.json"
            if analysis_file.exists():
                wai_numbers.append(wai_dir.name)
                logger.debug(f"Found valid WAI: {wai_dir.name}")
            else:
                logger.debug(f"Directory {wai_dir.name} missing application_analysis.json")
        
        logger.info(f"Total valid WAI numbers found: {len(wai_numbers)}")
        return sorted(wai_numbers)
    
    def load_application_analysis(self, wai_number: str) -> Optional[Dict[str, Any]]:
        """Load application analysis for a specific WAI number.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary containing analysis data, or None if not found
        """
        analysis_file = self.scholarship_dir / wai_number / "application_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Application analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading application analysis for WAI {wai_number}: {e}")
            return None
    
    def load_academic_analysis(self, wai_number: str) -> Optional[Dict[str, Any]]:
        """Load academic analysis for a specific WAI number.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary containing analysis data, or None if not found
        """
        analysis_file = self.scholarship_dir / wai_number / "academic_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Academic analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add download URL for the source transcript file
            server_url = os.environ.get("API_SERVER_URL", "http://localhost:8200")
            if "source_file" in data:
                source_filename = os.path.basename(data["source_file"])
                data["download_url"] = f"{server_url}/attachments/text/{self.scholarship_name}/{wai_number}/{source_filename}"
            
            return data
        except Exception as e:
            logger.error(f"Error loading academic analysis for WAI {wai_number}: {e}")
            return None
    
    def load_essay_analysis(self, wai_number: str, essay_number: int) -> Optional[Dict[str, Any]]:
        """Load essay analysis for a specific WAI number and essay.
        
        Args:
            wai_number: WAI application number
            essay_number: Essay number (1 or 2)
            
        Returns:
            Dictionary containing analysis data, or None if not found
        """
        analysis_file = self.scholarship_dir / wai_number / f"essay_{essay_number}_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Essay {essay_number} analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading essay {essay_number} analysis for WAI {wai_number}: {e}")
            return None
    
    def load_recommendation_analysis(self, wai_number: str, rec_number: int) -> Optional[Dict[str, Any]]:
        """Load recommendation analysis for a specific WAI number and recommendation.
        
        Args:
            wai_number: WAI application number
            rec_number: Recommendation number (1 or 2)
            
        Returns:
            Dictionary containing analysis data, or None if not found
        """
        analysis_file = self.scholarship_dir / wai_number / f"recommendation_{rec_number}_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Recommendation {rec_number} analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading recommendation {rec_number} analysis for WAI {wai_number}: {e}")
            return None
    
    def load_combined_essay_analysis(self, wai_number: str) -> Optional[Dict[str, Any]]:
        """Load essay analysis for a specific WAI number.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Essay analysis dictionary with download URLs
        """
        analysis_file = self.scholarship_dir / wai_number / "essay_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Essay analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add download URLs for essay source files
            server_url = os.environ.get("API_SERVER_URL", "http://localhost:8200")
            if "essays" in data:
                for essay in data["essays"]:
                    if "source_file" in essay:
                        source_filename = os.path.basename(essay["source_file"])
                        essay["download_url"] = f"{server_url}/attachments/text/{self.scholarship_name}/{wai_number}/{source_filename}"
            
            return data
        except Exception as e:
            logger.error(f"Error loading essay analysis for WAI {wai_number}: {e}")
            return None
    
    def load_combined_recommendation_analysis(self, wai_number: str) -> Optional[Dict[str, Any]]:
        """Load recommendation analysis for a specific WAI number.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Recommendation analysis dictionary with download URLs
        """
        analysis_file = self.scholarship_dir / wai_number / "recommendation_analysis.json"
        if not analysis_file.exists():
            logger.warning(f"Recommendation analysis not found for WAI {wai_number}")
            return None
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Add download URLs for recommendation source files
            server_url = os.environ.get("API_SERVER_URL", "http://localhost:8200")
            if "recommendations" in data:
                for rec in data["recommendations"]:
                    if "source_file" in rec:
                        source_filename = os.path.basename(rec["source_file"])
                        rec["download_url"] = f"{server_url}/attachments/text/{self.scholarship_name}/{wai_number}/{source_filename}"
            
            return data
        except Exception as e:
            logger.error(f"Error loading recommendation analysis for WAI {wai_number}: {e}")
            return None
    
    def load_application_data(self, wai_number: str) -> Optional[Dict[str, Any]]:
        """Load application data for a specific WAI number.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary containing application data, or None if not found
        """
        data_file = self.scholarship_dir / wai_number / "application_data.json"
        if not data_file.exists():
            logger.warning(f"Application data not found for WAI {wai_number}")
            return None
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading application data for WAI {wai_number}: {e}")
            return None
    
    def list_attachments(self, wai_number: str) -> Dict[str, Any]:
        """List processed attachment files for a specific WAI number.
        
        Only returns files that have been processed and are available as text files.
        Regular viewers can only download the processed text files, not the original PDFs.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary with processed attachment files and processing summary
        """
        # Load processing summary
        processing_summary = None
        summary_file = Path("outputs") / self.scholarship_name / wai_number / "attachments" / "_processing_summary.json"
        
        if not summary_file.exists():
            logger.warning(f"Processing summary not found for WAI {wai_number}")
            return {"files": [], "processing_summary": None}
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                processing_summary = json.load(f)
        except Exception as e:
            logger.error(f"Error loading processing summary for {wai_number}: {e}")
            return {"files": [], "processing_summary": None}
        
        # Get server URL from environment or use default
        server_url = os.environ.get("API_SERVER_URL", "http://localhost:8200")
        
        # Build file list from processed files only
        attachments = []
        attachments_dir = Path("outputs") / self.scholarship_name / wai_number / "attachments"
        
        if processing_summary and "processed_files" in processing_summary:
            for pf in processing_summary["processed_files"]:
                # Only include files that were successfully processed
                if not pf.get("has_errors", False):
                    text_file = pf.get("output_file")
                    text_file_path = attachments_dir / text_file
                    
                    # Verify text file exists
                    if text_file_path.exists():
                        file_info = {
                            "source_filename": pf["source_file"],
                            "text_filename": text_file,
                            "text_file_size": text_file_path.stat().st_size,
                            "original_file_size": pf.get("source_file_size", 0),
                            "download_url": f"{server_url}/attachments/text/{self.scholarship_name}/{wai_number}/{text_file}",
                            "pii_types_found": pf.get("pii_types_found", []),
                            "processed_date": pf.get("processed_date"),
                            "original_length": pf.get("original_length", 0),
                            "redacted_length": pf.get("redacted_length", 0)
                        }
                        attachments.append(file_info)
        
        # Sort by source filename
        attachments.sort(key=lambda x: x["source_filename"])
        
        return {
            "files": attachments,
            "processing_summary": processing_summary.get("summary") if processing_summary else None
        }
    
    def get_attachment_path(self, wai_number: str, filename: str) -> Optional[Path]:
        """Get the full path to an attachment file.
        
        Args:
            wai_number: WAI application number
            filename: Attachment filename
            
        Returns:
            Path to the file, or None if not found
        """
        # Look in data directory for actual PDF files
        file_path = Path("data") / self.scholarship_name / "Applications" / wai_number / filename
        if file_path.exists() and file_path.suffix.lower() == '.pdf':
            return file_path
        return None
    
    def load_summary_csv(self) -> List[Dict[str, Any]]:
        """Load data from summary.csv file.
        
        Returns:
            List of dictionaries containing application data from CSV
        """
        csv_file = self.scholarship_dir / "summary.csv"
        
        if not csv_file.exists():
            logger.warning(f"Summary CSV not found: {csv_file}")
            return []
        
        try:
            scores = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert scores to integers, handling empty values
                    try:
                        final_score = float(row.get('final_score', 0))
                        # Convert final_score (0-100 scale) to overall_score for compatibility
                        overall_score = int(final_score * 2) if final_score else 0
                        
                        # Map CSV scores to API response format
                        # The CSV has different score components, so we'll map them appropriately
                        application_score = int(row.get('application_score', 0))
                        recommendation_score = int(row.get('recommendation_score', 0))
                        academic_score = int(row.get('academic_score', 0))
                        essay_score = int(row.get('essay_score', 0))
                        
                        score_entry = {
                            'wai_number': row.get('wai_number', ''),
                            'name': row.get('name', ''),
                            'city': row.get('city', ''),
                            'state': row.get('state', ''),
                            'country': row.get('country', ''),
                            'overall_score': overall_score,
                            # Map to expected fields for ScoreResponse
                            'completeness_score': application_score,  # Use application_score as completeness
                            'validity_score': recommendation_score,   # Use recommendation_score as validity
                            'attachment_score': academic_score,       # Use academic_score as attachment
                            'final_score': final_score,
                            'application_score': application_score,
                            'recommendation_score': recommendation_score,
                            'academic_score': academic_score,
                            'essay_score': essay_score,
                            'complete': row.get('complete', 'False') == 'True',
                            'summary': f"Final Score: {final_score:.2f} (Academic: {academic_score}, Essay: {essay_score}, Application: {application_score}, Recommendation: {recommendation_score})"
                        }
                        scores.append(score_entry)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing row for WAI {row.get('wai_number')}: {e}")
                        continue
            
            logger.info(f"Loaded {len(scores)} applications from summary.csv")
            return scores
            
        except Exception as e:
            logger.error(f"Error reading summary CSV: {e}", exc_info=True)
            return []
    
    def get_all_scores(self) -> List[Dict[str, Any]]:
        """Get scores for all applications.
        
        Returns:
            List of dictionaries containing WAI number, applicant info, and scores
        """
        # Try to load from CSV first (much faster)
        scores = self.load_summary_csv()
        if scores:
            logger.info(f"Loaded {len(scores)} scores from CSV")
            return scores
        
        # Fallback to JSON files if CSV doesn't exist
        logger.info("CSV not found, falling back to JSON files")
        scores = []
        for wai_number in self.get_all_wai_numbers():
            analysis = self.load_application_analysis(wai_number)
            app_data = self.load_application_data(wai_number)
            
            if not analysis:
                continue

            # Support both legacy format (scores object) and new facet-based schema output.
            if 'scores' in analysis:
                score_entry = {
                    'wai_number': wai_number,
                    'overall_score': analysis['scores'].get('overall_score', 0),
                    'completeness_score': analysis['scores'].get('completeness_score', 0),
                    'validity_score': analysis['scores'].get('validity_score', 0),
                    'attachment_score': analysis['scores'].get('attachment_score', 0),
                    'summary': analysis.get('summary', '')
                }
            elif 'facets' in analysis:
                facets = analysis.get('facets') or []
                facet_scores = {f.get('name'): int(f.get('score', 0)) for f in facets if isinstance(f, dict)}

                # Map 0–10 facet scores into the historical 0–30/0–30/0–40 component scores for display.
                completeness_0_10 = facet_scores.get('Completeness', 0)
                validity_0_10 = facet_scores.get('Eligibility & Validity', 0)
                attachment_0_10 = facet_scores.get('Attachment Quality', completeness_0_10)

                completeness_score = int(round(completeness_0_10 * 3))  # 0–30
                validity_score = int(round(validity_0_10 * 3))          # 0–30
                attachment_score = int(round(attachment_0_10 * 4))      # 0–40
                overall_score = int(completeness_score + validity_score + attachment_score)

                score_entry = {
                    'wai_number': wai_number,
                    'overall_score': overall_score,
                    'completeness_score': completeness_score,
                    'validity_score': validity_score,
                    'attachment_score': attachment_score,
                    'summary': analysis.get('overall_notes', '')
                }
            else:
                continue
                
                # Add applicant information if available
                if app_data:
                    score_entry['name'] = app_data.get('name')
                    score_entry['city'] = app_data.get('city')
                    score_entry['state'] = app_data.get('state')
                    score_entry['country'] = app_data.get('country')
                
                scores.append(score_entry)
        return scores
    
    def get_top_scores(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top scoring applications.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of top scoring applications
        """
        all_scores = self.get_all_scores()
        sorted_scores = sorted(all_scores, key=lambda x: x['overall_score'], reverse=True)
        return sorted_scores[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for all applications.
        
        Returns:
            Dictionary containing statistical information
        """
        logger.info(f"Getting statistics for {self.scholarship_name}")
        logger.info(f"Scholarship directory: {self.scholarship_dir}")
        logger.info(f"Directory exists: {self.scholarship_dir.exists()}")
        
        wai_numbers = self.get_all_wai_numbers()
        logger.info(f"Found {len(wai_numbers)} WAI numbers: {wai_numbers[:5] if len(wai_numbers) > 5 else wai_numbers}")
        
        all_scores = self.get_all_scores()
        logger.info(f"Retrieved {len(all_scores)} scores")
        
        if not all_scores:
            logger.warning(f"No scores found for {self.scholarship_name}")
            return {
                'total_applications': 0,
                'average_score': 0,
                'median_score': 0,
                'min_score': 0,
                'max_score': 0,
                'score_distribution': {}
            }
        
        overall_scores = [s['overall_score'] for s in all_scores]
        
        # Calculate score distribution (by ranges)
        distribution = {
            '90-100': 0,
            '80-89': 0,
            '70-79': 0,
            '60-69': 0,
            '50-59': 0,
            '0-49': 0
        }
        
        for score in overall_scores:
            if score >= 90:
                distribution['90-100'] += 1
            elif score >= 80:
                distribution['80-89'] += 1
            elif score >= 70:
                distribution['70-79'] += 1
            elif score >= 60:
                distribution['60-69'] += 1
            elif score >= 50:
                distribution['50-59'] += 1
            else:
                distribution['0-49'] += 1
        
        return {
            'total_applications': len(all_scores),
            'average_score': round(statistics.mean(overall_scores), 2),
            'median_score': round(statistics.median(overall_scores), 2),
            'min_score': min(overall_scores),
            'max_score': max(overall_scores),
            'score_distribution': distribution
        }

# Made with Bob
