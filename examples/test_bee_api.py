#!/usr/bin/env python3
"""Example script to test the Bee Agents API.

This script demonstrates how to use the Scholarship Analysis API
to retrieve various types of data.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

import requests
import json
from typing import Optional


class ScholarshipAPIClient:
    """Client for interacting with the Scholarship Analysis API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> dict:
        """Check API health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_top_scores(self, limit: int = 10) -> dict:
        """Get top scoring applications.
        
        Args:
            limit: Number of top scores to return
            
        Returns:
            Dictionary with top scores
        """
        response = requests.get(f"{self.base_url}/top_scores?limit={limit}")
        response.raise_for_status()
        return response.json()
    
    def get_score(self, wai_number: str) -> dict:
        """Get score for a specific application.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary with application score
        """
        response = requests.get(f"{self.base_url}/score/{wai_number}")
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self) -> dict:
        """Get statistics for all applications.
        
        Returns:
            Dictionary with statistics
        """
        response = requests.get(f"{self.base_url}/statistics")
        response.raise_for_status()
        return response.json()
    
    def get_application_analysis(self, wai_number: str) -> dict:
        """Get detailed application analysis.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary with application analysis
        """
        response = requests.get(f"{self.base_url}/application/{wai_number}")
        response.raise_for_status()
        return response.json()
    
    def get_academic_analysis(self, wai_number: str) -> Optional[dict]:
        """Get academic analysis.
        
        Args:
            wai_number: WAI application number
            
        Returns:
            Dictionary with academic analysis, or None if not found
        """
        try:
            response = requests.get(f"{self.base_url}/academic/{wai_number}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def get_essay_analysis(self, wai_number: str, essay_number: int) -> Optional[dict]:
        """Get essay analysis.
        
        Args:
            wai_number: WAI application number
            essay_number: Essay number (1 or 2)
            
        Returns:
            Dictionary with essay analysis, or None if not found
        """
        try:
            response = requests.get(f"{self.base_url}/essay/{wai_number}/{essay_number}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    def get_recommendation_analysis(self, wai_number: str, rec_number: int) -> Optional[dict]:
        """Get recommendation analysis.
        
        Args:
            wai_number: WAI application number
            rec_number: Recommendation number (1 or 2)
            
        Returns:
            Dictionary with recommendation analysis, or None if not found
        """
        try:
            response = requests.get(f"{self.base_url}/recommendation/{wai_number}/{rec_number}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise


def main():
    """Main function to demonstrate API usage."""
    print("=" * 80)
    print("Scholarship Analysis API - Test Script")
    print("=" * 80)
    print()
    
    # Initialize client
    client = ScholarshipAPIClient("http://localhost:8000")
    
    # 1. Health Check
    print("1. Health Check")
    print("-" * 80)
    try:
        health = client.health_check()
        print(f"✓ API is healthy")
        print(f"  Scholarship: {health['scholarship']}")
        print(f"  Total Applications: {health['total_applications']}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return
    print()
    
    # 2. Get Statistics
    print("2. Statistics")
    print("-" * 80)
    try:
        stats = client.get_statistics()
        print(f"Scholarship: {stats['scholarship']}")
        print(f"Total Applications: {stats['total_applications']}")
        print(f"Average Score: {stats['average_score']:.2f}")
        print(f"Median Score: {stats['median_score']:.2f}")
        print(f"Score Range: {stats['min_score']} - {stats['max_score']}")
        print(f"\nScore Distribution:")
        for range_name, count in stats['score_distribution'].items():
            print(f"  {range_name}: {count} applications")
    except Exception as e:
        print(f"✗ Failed to get statistics: {e}")
    print()
    
    # 3. Get Top Scores
    print("3. Top 5 Scores")
    print("-" * 80)
    try:
        top_scores = client.get_top_scores(limit=5)
        print(f"Top {len(top_scores['top_scores'])} applications:")
        for i, score in enumerate(top_scores['top_scores'], 1):
            print(f"\n{i}. WAI {score['wai_number']}: {score['overall_score']}/100")
            print(f"   Completeness: {score['completeness_score']}/30")
            print(f"   Validity: {score['validity_score']}/30")
            print(f"   Attachments: {score['attachment_score']}/40")
            print(f"   Summary: {score['summary'][:80]}...")
    except Exception as e:
        print(f"✗ Failed to get top scores: {e}")
    print()
    
    # 4. Get Specific Application Analysis
    print("4. Detailed Application Analysis")
    print("-" * 80)
    try:
        # Use the first WAI number from top scores
        top_scores = client.get_top_scores(limit=1)
        if top_scores['top_scores']:
            wai_number = top_scores['top_scores'][0]['wai_number']
            print(f"Analyzing WAI {wai_number}...")
            print()
            
            # Get application analysis
            analysis = client.get_application_analysis(wai_number)
            print(f"Summary: {analysis['summary']}")
            print(f"\nScores:")
            print(f"  Overall: {analysis['scores']['overall_score']}/100")
            print(f"  Completeness: {analysis['scores']['completeness_score']}/30")
            print(f"  Validity: {analysis['scores']['validity_score']}/30")
            print(f"  Attachments: {analysis['scores']['attachment_score']}/40")
            
            print(f"\nScore Breakdown:")
            print(f"  Completeness: {analysis['score_breakdown']['completeness_reasoning'][:100]}...")
            print(f"  Validity: {analysis['score_breakdown']['validity_reasoning'][:100]}...")
            print(f"  Attachments: {analysis['score_breakdown']['attachment_reasoning'][:100]}...")
            
            if analysis['completeness_issues']:
                print(f"\nCompleteness Issues:")
                for issue in analysis['completeness_issues']:
                    print(f"  - {issue}")
            
            if analysis['validity_issues']:
                print(f"\nValidity Issues:")
                for issue in analysis['validity_issues']:
                    print(f"  - {issue}")
            
            print(f"\nAttachment Status: {analysis['attachment_status']}")
            print(f"Processed: {analysis['processed_date']}")
            print(f"Source File: {analysis['source_file']}")
            
            # Try to get academic analysis
            print(f"\n--- Academic Analysis ---")
            academic = client.get_academic_analysis(wai_number)
            if academic:
                print(f"Summary: {academic['academic_summary'][:100]}...")
                if academic.get('gpa'):
                    print(f"GPA: {academic['gpa']}")
            else:
                print("Academic analysis not available")
            
            # Try to get essay analyses
            print(f"\n--- Essay Analyses ---")
            for essay_num in [1, 2]:
                essay = client.get_essay_analysis(wai_number, essay_num)
                if essay:
                    print(f"\nEssay {essay_num}:")
                    print(f"  Summary: {essay['summary'][:80]}...")
                    if essay.get('score'):
                        print(f"  Score: {essay['score']}")
                else:
                    print(f"\nEssay {essay_num}: Not available")
            
            # Try to get recommendation analyses
            print(f"\n--- Recommendation Analyses ---")
            for rec_num in [1, 2]:
                rec = client.get_recommendation_analysis(wai_number, rec_num)
                if rec:
                    print(f"\nRecommendation {rec_num}:")
                    print(f"  Summary: {rec['summary'][:80]}...")
                    if rec.get('score'):
                        print(f"  Score: {rec['score']}")
                else:
                    print(f"\nRecommendation {rec_num}: Not available")
        else:
            print("No applications found")
    except Exception as e:
        print(f"✗ Failed to get application analysis: {e}")
    print()
    
    print("=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()

# Made with Bob
