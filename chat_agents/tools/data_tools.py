"""Data access tools for scholarship results.

This module provides tools for agents to query scholarship application data,
including CSV summaries and JSON analysis files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

import pandas as pd

logger = logging.getLogger(__name__)


class ScholarshipDataTools:
    """Tools for accessing scholarship application data."""
    
    def __init__(self, outputs_dir: Path = Path("outputs")):
        """Initialize data tools.
        
        Args:
            outputs_dir: Base outputs directory containing scholarship data.
        """
        self.outputs_dir = outputs_dir
        self.logger = logging.getLogger(__name__)
    
    def get_summary_df(self, scholarship: str) -> Optional[pd.DataFrame]:
        """Load summary CSV for a scholarship.
        
        Args:
            scholarship: Scholarship name (e.g., "Delaney_Wings").
            
        Returns:
            DataFrame with summary data, or None if not found.
        """
        csv_path = self.outputs_dir / scholarship / "summary.csv"
        
        if not csv_path.exists():
            self.logger.error(f"Summary CSV not found: {csv_path}")
            return None
        
        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Loaded {len(df)} applicants from {scholarship}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading CSV: {e}")
            return None
    
    def get_applicant_by_wai(self, wai_number: str, scholarship: str) -> Optional[Dict[str, Any]]:
        """Get applicant data by WAI number.
        
        Args:
            wai_number: WAI application number.
            scholarship: Scholarship name.
            
        Returns:
            Dictionary with applicant data, or None if not found.
        """
        df = self.get_summary_df(scholarship)
        if df is None:
            return None
        
        # Convert WAI number to string for comparison
        df['wai_number'] = df['wai_number'].astype(str)
        
        result = df[df['wai_number'] == str(wai_number)]
        
        if result.empty:
            self.logger.warning(f"WAI {wai_number} not found in {scholarship}")
            return None
        
        return result.iloc[0].to_dict()
    
    def search_by_name(self, name: str, scholarship: str) -> List[Dict[str, Any]]:
        """Search applicants by name (case-insensitive partial match).
        
        Args:
            name: Name to search for.
            scholarship: Scholarship name.
            
        Returns:
            List of matching applicant dictionaries.
        """
        df = self.get_summary_df(scholarship)
        if df is None:
            return []
        
        # Case-insensitive partial match
        mask = df['name'].str.contains(name, case=False, na=False)
        results = df[mask]
        
        return results.to_dict('records')
    
    def get_top_applicants(self, n: int, scholarship: str, 
                          score_type: str = "final_score") -> List[Dict[str, Any]]:
        """Get top N applicants by score.
        
        Args:
            n: Number of top applicants to return.
            scholarship: Scholarship name.
            score_type: Score column to sort by (default: "final_score").
            
        Returns:
            List of top applicant dictionaries.
        """
        df = self.get_summary_df(scholarship)
        if df is None:
            return []
        
        if score_type not in df.columns:
            self.logger.error(f"Score type '{score_type}' not found in data")
            return []
        
        # Sort by score descending and get top N
        top_df = df.nlargest(n, score_type)
        
        return top_df.to_dict('records')
    
    def get_statistics(self, scholarship: str) -> Optional[Dict[str, Any]]:
        """Get summary statistics for a scholarship.
        
        Args:
            scholarship: Scholarship name.
            
        Returns:
            Dictionary with statistics, or None if data not found.
        """
        df = self.get_summary_df(scholarship)
        if df is None:
            return None
        
        stats = {
            "total_applicants": len(df),
            "complete_applications": int(df['complete'].sum()) if 'complete' in df.columns else 0,
            "average_scores": {
                "final_score": float(df['final_score'].mean()),
                "application_score": float(df['application_score'].mean()),
                "recommendation_score": float(df['recommendation_score'].mean()),
                "academic_score": float(df['academic_score'].mean()),
                "essay_score": float(df['essay_score'].mean())
            },
            "score_ranges": {
                "final_score": {
                    "min": float(df['final_score'].min()),
                    "max": float(df['final_score'].max())
                }
            }
        }
        
        return stats
    
    def load_analysis_file(self, wai_number: str, scholarship: str, 
                          analysis_type: str) -> Optional[Dict[str, Any]]:
        """Load analysis JSON file for an applicant.
        
        Args:
            wai_number: WAI application number.
            scholarship: Scholarship name.
            analysis_type: Type of analysis ("application", "recommendation", 
                          "academic", "essay").
            
        Returns:
            Dictionary with analysis data, or None if not found.
        """
        filename = f"{analysis_type}_analysis.json"
        file_path = self.outputs_dir / scholarship / wai_number / filename
        
        if not file_path.exists():
            self.logger.warning(f"Analysis file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.logger.error(f"Error loading analysis file: {e}")
            return None
    
    def get_application_data(self, wai_number: str, scholarship: str) -> Optional[Dict[str, Any]]:
        """Load application data JSON for an applicant.
        
        Args:
            wai_number: WAI application number.
            scholarship: Scholarship name.
            
        Returns:
            Dictionary with application data, or None if not found.
        """
        file_path = self.outputs_dir / scholarship / wai_number / "application_data.json"
        
        if not file_path.exists():
            self.logger.warning(f"Application data not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.logger.error(f"Error loading application data: {e}")
            return None
    
    def list_attachments(self, wai_number: str, scholarship: str) -> List[str]:
        """List attachment files for an applicant.
        
        Args:
            wai_number: WAI application number.
            scholarship: Scholarship name.
            
        Returns:
            List of attachment filenames.
        """
        attachments_dir = self.outputs_dir / scholarship / wai_number / "attachments"
        
        if not attachments_dir.exists():
            self.logger.warning(f"Attachments directory not found: {attachments_dir}")
            return []
        
        # Get all .txt files except processing summary
        txt_files = [f.name for f in attachments_dir.glob("*.txt")]
        
        return sorted(txt_files)
    
    def get_processing_summary(self, wai_number: str, scholarship: str) -> Optional[Dict[str, Any]]:
        """Get attachment processing summary.
        
        Args:
            wai_number: WAI application number.
            scholarship: Scholarship name.
            
        Returns:
            Dictionary with processing summary, or None if not found.
        """
        summary_path = self.outputs_dir / scholarship / wai_number / "attachments" / "_processing_summary.json"
        
        if not summary_path.exists():
            self.logger.warning(f"Processing summary not found: {summary_path}")
            return None
        
        try:
            with open(summary_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.logger.error(f"Error loading processing summary: {e}")
            return None


# Made with Bob