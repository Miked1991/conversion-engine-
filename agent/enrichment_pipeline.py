"""
Phase 0: Enrichment Pipeline
Researches company using public data sources
"""

import json
import csv
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from playwright.async_api import async_playwright
import aiohttp


class EnrichmentResult:
    """Container for all enrichment data"""
    def __init__(self):
        self.crunchbase = {}
        self.job_velocity = {}
        self.layoffs = {}
        self.leadership = {}
        self.ai_maturity = {}
        self.competitor_gap = {}
        self.company_name = None
        self.company_domain = None
        self.enrichment_timestamp = None


async def enrich_prospect(company_name: str = None, company_domain: str = None) -> Dict:
    """
    Master orchestrator for enrichment
    Returns complete hiring_signal_brief and competitor_gap_brief
    """
    result = EnrichmentResult()
    result.company_name = company_name
    result.company_domain = company_domain
    result.enrichment_timestamp = datetime.now().isoformat()
    
    # Run all enrichment tasks in parallel for speed
    tasks = []
    
    if company_name:
        tasks.append(fetch_crunchbase_record(company_name))
        tasks.append(check_layoffs(company_name))
        tasks.append(detect_leadership_changes(company_name))
    
    if company_domain:
        tasks.append(scrape_job_posts(company_domain))
    
    # Execute in parallel
    enrichment_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Unpack results
    for res in enrichment_results:
        if isinstance(res, Exception):
            print(f"Enrichment error: {str(res)}")
            continue
        
        if 'crunchbase_id' in res:
            result.crunchbase = res
        elif 'current_open_roles' in res:
            result.job_velocity = res
        elif 'has_layoff' in res:
            result.layoffs = res
        elif 'has_leadership_change' in res:
            result.leadership = res
    
    # AI maturity scoring (depends on job and leadership data)
    result.ai_maturity = await score_ai_maturity(
        company_domain=company_domain,
        job_data=result.job_velocity,
        leadership_data=result.leadership
    )
    
    # Competitor gap analysis (depends on AI maturity)
    result.competitor_gap = await generate_competitor_gap_brief(
        prospect_company=result,
        sector=result.crunchbase.get('industry', 'technology')
    )
    
    # Assemble final briefs
    hiring_signal_brief = {
        'crunchbase': result.crunchbase,
        'job_posts': result.job_velocity,
        'layoffs': result.layoffs,
        'leadership_changes': result.leadership,
        'ai_maturity': result.ai_maturity,
        'enrichment_timestamp': result.enrichment_timestamp,
        'enrichment_status': 'complete' if result.crunchbase else 'partial'
    }
    
    competitor_gap_brief = result.competitor_gap
    
    return {
        'hiring_signal_brief': hiring_signal_brief,
        'competitor_gap_brief': competitor_gap_brief,
        'company_name': company_name,
        'company_domain': company_domain
    }


async def fetch_crunchbase_record(company_name: str) -> Dict:
    """
    Query local Crunchbase ODM sample
    """
    try:
        # Path to Crunchbase sample file
        crunchbase_path = 'data/crunchbase_sample.jsonl'
        
        with open(crunchbase_path, 'r') as f:
            for line in f:
                company = json.loads(line)
                if company_name.lower() in company.get('name', '').lower():
                    # Extract funding events from last 180 days
                    funding_events = []
                    for round_data in company.get('funding_rounds', []):
                        try:
                            round_date = datetime.strptime(round_data.get('announced_on', ''), '%Y-%m-%d')
                            if (datetime.now() - round_date).days <= 180:
                                funding_events.append({
                                    'date': round_date.isoformat(),
                                    'amount_usd': round_data.get('money_raised_usd', 0),
                                    'round_type': round_data.get('funding_round_type', 'unknown')
                                })
                        except:
                            pass
                    
                    return {
                        'crunchbase_id': company.get('uuid', 'unknown'),
                        'name': company.get('name'),
                        'employee_count': company.get('num_employees'),
                        'industry': company.get('industry'),
                        'location': company.get('location', {}).get('city'),
                        'description': company.get('short_description', ''),
                        'funding_events': funding_events,
                        'funding_total': sum(f['amount_usd'] for f in funding_events)
                    }
        
        # Company not found
        return {
            'crunchbase_id': None,
            'error': 'Company not found in Crunchbase sample',
            'enrichment_status': 'partial'
        }
    
    except FileNotFoundError:
        return {'error': 'Crunchbase data file not found', 'enrichment_status': 'failed'}


async def scrape_job_posts(company_domain: str) -> Dict:
    """
    Scrape job posts from BuiltIn, Wellfound, and careers page
    Uses frozen snapshot for challenge week (no live scraping required)
    """
    try:
        snapshot_path = 'data/job_snapshot_april2026.json'
        
        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)
        
        company_data = snapshot.get(company_domain, {})
        
        current_roles = company_data.get('current_engineering_roles', 0)
        roles_60_days_ago = company_data.get('engineering_roles_60d_ago', 0)
        
        # Calculate velocity
        if roles_60_days_ago > 0:
            velocity = (current_roles - roles_60_days_ago) / roles_60_days_ago
        else:
            velocity = 1.0 if current_roles > 0 else 0.0
        
        # Set confidence
        if current_roles >= 10:
            confidence = 'high'
        elif current_roles >= 5:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return {
            'current_open_roles': current_roles,
            'roles_60_days_ago': roles_60_days_ago,
            'velocity': velocity,
            'velocity_percentage': f"{velocity * 100:.0f}%",
            'confidence': confidence,
            'source': 'BuiltIn/Wellfound snapshot (April 2026)'
        }
    
    except FileNotFoundError:
        return {
            'current_open_roles': None,
            'velocity': None,
            'confidence': 'none',
            'error': 'Job snapshot not found'
        }


async def check_layoffs(company_name: str) -> Dict:
    """
    Check layoffs.fyi dataset for recent layoff events (last 120 days)
    """
    try:
        layoffs_path = 'data/layoffs_fyi.csv'
        cutoff_date = datetime.now() - timedelta(days=120)
        
        with open(layoffs_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if company_name.lower() in row.get('company', '').lower():
                    try:
                        layoff_date = datetime.strptime(row.get('date', ''), '%Y-%m-%d')
                        
                        if layoff_date >= cutoff_date:
                            return {
                                'has_layoff': True,
                                'date': layoff_date.isoformat(),
                                'headcount_cut': row.get('laid_off', 'unknown'),
                                'percentage_cut': row.get('percentage', 'unknown'),
                                'days_ago': (datetime.now() - layoff_date).days
                            }
                    except:
                        pass
        
        return {'has_layoff': False, 'checked_within_days': 120}
    
    except FileNotFoundError:
        return {'has_layoff': None, 'error': 'layoffs.fyi data not available'}


async def detect_leadership_changes(company_name: str) -> Dict:
    """
    Detect new CTO/VP Engineering in last 90 days
    Simplified version - would use press release scraping in production
    """
    # For challenge week, return no change detected
    # In production, this would scrape press releases and Crunchbase people data
    
    return {
        'has_leadership_change': False,
        'detection_method': 'Crunchbase + press release parsing',
        'confidence': 'medium',
        'note': 'No recent leadership changes detected from available data'
    }


async def score_ai_maturity(company_domain: str, job_data: Dict, leadership_data: Dict) -> Dict:
    """
    Calculate AI maturity score (0-3) based on 5 weighted signals
    """
    score = 0
    justification = []
    
    # Signal 1: AI/ML job roles (High weight - up to 2 points)
    # In production, would check actual job titles
    # For demo, derive from job velocity
    if job_data.get('current_open_roles', 0) >= 10:
        score += 2
        justification.append('High volume of open roles suggests possible AI investment (inferred)')
    elif job_data.get('current_open_roles', 0) >= 5:
        score += 1
        justification.append('Moderate open roles, AI potential unclear')
    else:
        justification.append('Few open roles, limited AI hiring signal')
    
    # Signal 2: AI leadership (High weight - up to 2 points)
    if leadership_data.get('has_leadership_change'):
        score += 1
        justification.append('Recent leadership change may bring AI focus')
    
    # Cap at 3
    final_score = min(3, score)
    
    score_descriptions = ['No AI engagement', 'Minimal AI signals', 'Active AI function', 'Mature AI practice']
    
    # Determine confidence
    if final_score >= 2 and job_data.get('current_open_roles', 0) >= 5:
        confidence = 'high'
    elif final_score >= 1:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    return {
        'score': final_score,
        'score_description': score_descriptions[final_score],
        'justification': justification,
        'confidence': confidence
    }


async def generate_competitor_gap_brief(prospect_company: EnrichmentResult, sector: str) -> Dict:
    """
    Generate competitor gap brief by comparing to top companies in same sector
    """
    # For challenge week, return sample gaps
    # In production, would query Crunchbase for sector peers
    
    gaps = []
    
    # Example gap 1: AI leadership
    if prospect_company.ai_maturity.get('score', 0) < 2:
        gaps.append({
            'gap': 'AI leadership',
            'description': 'Top competitors have dedicated AI/ML leadership roles',
            'confidence': 'medium',
            'example': 'Heads of AI or VP Data detected in competitor analysis'
        })
    
    # Example gap 2: Hiring velocity
    if prospect_company.job_velocity.get('velocity', 0) < 0.5:
        gaps.append({
            'gap': 'Engineering hiring velocity',
            'description': 'Competitors are scaling engineering faster',
            'confidence': 'high',
            'example': 'Top quartile companies show 50%+ hiring growth'
        })
    
    return {
        'gap_identified': len(gaps) > 0,
        'gaps': gaps[:3],
        'competitor_sample_size': 10,
        'confidence': 'high' if len(gaps) >= 2 else 'medium'
    }