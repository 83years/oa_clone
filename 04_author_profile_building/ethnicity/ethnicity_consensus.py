#!/usr/bin/env python3
"""
Ethnicity Consensus Module

This module provides consensus logic for combining predictions from multiple
ethnicity inference tools:
1. ethnicseer - 12 ethnic categories (Chinese, English, French, German, Indian,
   Italian, Japanese, Korean, Middle-Eastern, Russian, Spanish, Vietnamese)
2. pyethnicity - 4 US-centric race categories (Asian, Black, Hispanic, White)
3. ethnidata - 238 country/nationality predictions with regional context
4. name2nat - 254 nationalities from Wikipedia data (global coverage)
5. raceBERT - Transformer-based race/ethnicity prediction (state-of-the-art)

The consensus algorithm:
- Maps predictions to a unified set of broad but meaningful categories
- Applies tool-specific quality weights
- Uses confidence scores as probability multipliers
- Considers regional/geographic context from ethnidata
- Returns a consensus ethnicity/region with confidence score

Unified ethnicity categories:
- East Asian (Chinese, Japanese, Korean, + ethnidata: China, Japan, Korea, etc.)
- South Asian (Indian, + ethnidata: India, Pakistan, Bangladesh, Nepal, etc.)
- Southeast Asian (Vietnamese, + ethnidata: Vietnam, Thailand, Philippines, etc.)
- Middle Eastern/North African (Middle-Eastern, + ethnidata: Egypt, Iran, Turkey, etc.)
- Hispanic/Latino (Spanish-speaking Americas)
- European (English, French, German, Italian, Russian, + ethnidata: European countries)
- Sub-Saharan African
- Other/Mixed

"""

from typing import Optional, Dict, Tuple
import json


# Mapping ethnicseer categories to unified categories
ETHNICSEER_TO_UNIFIED = {
    'chi': 'East Asian',
    'jap': 'East Asian',
    'kor': 'East Asian',
    'ind': 'South Asian',
    'vie': 'Southeast Asian',
    'mea': 'Middle Eastern/North African',
    'spa': 'Hispanic/Latino',
    'eng': 'European',
    'frn': 'European',
    'ger': 'European',
    'ita': 'European',
    'rus': 'European'
}

# Mapping pyethnicity categories to unified categories
PYETHNICITY_TO_UNIFIED = {
    'asian': 'Asian',  # General Asian, will be refined by other tools
    'black': 'African/African American',
    'hispanic': 'Hispanic/Latino',
    'white': 'European/Caucasian'
}

# Mapping ethnidata regions to unified categories
ETHNIDATA_REGION_TO_UNIFIED = {
    'Asia': 'Asian',  # Will be refined by country
    'Europe': 'European',
    'Africa': 'African',
    'Americas': None,  # Need country to distinguish Hispanic vs others
    'Oceania': 'Oceanian',
    'Middle East': 'Middle Eastern/North African'
}

# Mapping ethnidata countries to more specific categories
ETHNIDATA_COUNTRY_REFINEMENT = {
    # East Asian countries
    'China': 'East Asian',
    'Japan': 'East Asian',
    'Korea': 'East Asian',
    'Taiwan': 'East Asian',
    'Hong Kong': 'East Asian',
    'Macau': 'East Asian',
    'Mongolia': 'East Asian',

    # South Asian countries
    'India': 'South Asian',
    'Pakistan': 'South Asian',
    'Bangladesh': 'South Asian',
    'Nepal': 'South Asian',
    'Sri Lanka': 'South Asian',
    'Bhutan': 'South Asian',
    'Afghanistan': 'South Asian',
    'Maldives': 'South Asian',

    # Southeast Asian countries
    'Vietnam': 'Southeast Asian',
    'Thailand': 'Southeast Asian',
    'Philippines': 'Southeast Asian',
    'Indonesia': 'Southeast Asian',
    'Malaysia': 'Southeast Asian',
    'Singapore': 'Southeast Asian',
    'Myanmar': 'Southeast Asian',
    'Cambodia': 'Southeast Asian',
    'Laos': 'Southeast Asian',
    'Brunei': 'Southeast Asian',
    'Timor-Leste': 'Southeast Asian',

    # Middle Eastern/North African countries
    'Egypt': 'Middle Eastern/North African',
    'Iran': 'Middle Eastern/North African',
    'Turkey': 'Middle Eastern/North African',
    'Saudi Arabia': 'Middle Eastern/North African',
    'Iraq': 'Middle Eastern/North African',
    'Syria': 'Middle Eastern/North African',
    'Jordan': 'Middle Eastern/North African',
    'Lebanon': 'Middle Eastern/North African',
    'Israel': 'Middle Eastern/North African',
    'Palestine': 'Middle Eastern/North African',
    'Yemen': 'Middle Eastern/North African',
    'Oman': 'Middle Eastern/North African',
    'UAE': 'Middle Eastern/North African',
    'Kuwait': 'Middle Eastern/North African',
    'Bahrain': 'Middle Eastern/North African',
    'Qatar': 'Middle Eastern/North African',
    'Morocco': 'Middle Eastern/North African',
    'Algeria': 'Middle Eastern/North African',
    'Tunisia': 'Middle Eastern/North African',
    'Libya': 'Middle Eastern/North African',

    # Hispanic/Latino countries
    'Mexico': 'Hispanic/Latino',
    'Spain': 'Hispanic/Latino',
    'Argentina': 'Hispanic/Latino',
    'Colombia': 'Hispanic/Latino',
    'Peru': 'Hispanic/Latino',
    'Venezuela': 'Hispanic/Latino',
    'Chile': 'Hispanic/Latino',
    'Ecuador': 'Hispanic/Latino',
    'Guatemala': 'Hispanic/Latino',
    'Cuba': 'Hispanic/Latino',
    'Bolivia': 'Hispanic/Latino',
    'Dominican Republic': 'Hispanic/Latino',
    'Honduras': 'Hispanic/Latino',
    'Paraguay': 'Hispanic/Latino',
    'El Salvador': 'Hispanic/Latino',
    'Nicaragua': 'Hispanic/Latino',
    'Costa Rica': 'Hispanic/Latino',
    'Panama': 'Hispanic/Latino',
    'Uruguay': 'Hispanic/Latino',
    'Puerto Rico': 'Hispanic/Latino',

    # Sub-Saharan African countries (major ones)
    'Nigeria': 'Sub-Saharan African',
    'Ethiopia': 'Sub-Saharan African',
    'South Africa': 'Sub-Saharan African',
    'Kenya': 'Sub-Saharan African',
    'Tanzania': 'Sub-Saharan African',
    'Uganda': 'Sub-Saharan African',
    'Ghana': 'Sub-Saharan African',
    'Mozambique': 'Sub-Saharan African',
    'Madagascar': 'Sub-Saharan African',
    'Cameroon': 'Sub-Saharan African',
    'Angola': 'Sub-Saharan African',
    'Mali': 'Sub-Saharan African',
    'Burkina Faso': 'Sub-Saharan African',
    'Niger': 'Sub-Saharan African',
    'Senegal': 'Sub-Saharan African',
    'Somalia': 'Sub-Saharan African',
    'Chad': 'Sub-Saharan African',
    'Zimbabwe': 'Sub-Saharan African',
    'Guinea': 'Sub-Saharan African',
    'Rwanda': 'Sub-Saharan African',
    'Benin': 'Sub-Saharan African',
    'Burundi': 'Sub-Saharan African',
    'South Sudan': 'Sub-Saharan African',
    'Sierra Leone': 'Sub-Saharan African',
    'Togo': 'Sub-Saharan African',
    'Liberia': 'Sub-Saharan African',
    'Mauritania': 'Sub-Saharan African',
    'Congo': 'Sub-Saharan African',
    'Namibia': 'Sub-Saharan African',
    'Botswana': 'Sub-Saharan African',
    'Gabon': 'Sub-Saharan African',
}


def get_tool_weight(tool_name: str, ethnicity: Optional[str] = None) -> float:
    """
    Get the base weight for a tool, optionally adjusted for specific ethnicities.

    Args:
        tool_name (str): Name of the tool ('ethnicseer', 'pyethnicity', 'ethnidata')
        ethnicity (str, optional): The predicted ethnicity for context

    Returns:
        float: Weight for this tool's prediction
    """
    base_weights = {
        'ethnicseer': 1.2,      # High quality, 12 ethnic categories, 84% accuracy
        'pyethnicity': 1.0,     # Good for US names, US-centric categories
        'ethnidata': 0.8,       # Granular nationality data, but needs mapping
        'name2nat': 0.9,        # Global, 254 nationalities, 55% top-1 accuracy
        'racebert': 1.3         # State-of-the-art, 86% f1-score, transformer-based
    }

    weight = base_weights.get(tool_name, 1.0)

    # Boost pyethnicity for African American (unique category)
    if tool_name == 'pyethnicity' and ethnicity == 'African/African American':
        weight *= 1.3

    # Boost ethnidata for specific regional predictions
    if tool_name == 'ethnidata' and ethnicity in ['Middle Eastern/North African', 'Sub-Saharan African']:
        weight *= 1.2

    return weight


def map_ethnicseer_to_unified(ethnicity: str, confidence: float) -> Tuple[Optional[str], float]:
    """
    Map ethnicseer prediction to unified category.

    Args:
        ethnicity: ethnicseer ethnicity code
        confidence: confidence score

    Returns:
        Tuple of (unified_ethnicity, confidence)
    """
    unified = ETHNICSEER_TO_UNIFIED.get(ethnicity)
    return (unified, confidence) if unified else (None, 0.0)


def map_pyethnicity_to_unified(race_probs: Dict[str, float]) -> Tuple[Optional[str], float]:
    """
    Map pyethnicity race probabilities to unified category.

    Args:
        race_probs: Dictionary of {race: probability}

    Returns:
        Tuple of (unified_ethnicity, confidence)
    """
    if not race_probs:
        return (None, 0.0)

    # Find highest probability race
    max_race = max(race_probs, key=race_probs.get)
    max_prob = race_probs[max_race]

    # Only accept if probability > 0.5
    if max_prob < 0.5:
        return (None, 0.0)

    unified = PYETHNICITY_TO_UNIFIED.get(max_race)
    return (unified, max_prob) if unified else (None, 0.0)


def map_ethnidata_to_unified(country: Optional[str], region: Optional[str],
                             confidence: float) -> Tuple[Optional[str], float]:
    """
    Map ethnidata prediction to unified category.

    Args:
        country: Predicted country name
        region: Predicted region
        confidence: Confidence score

    Returns:
        Tuple of (unified_ethnicity, confidence)
    """
    if not country and not region:
        return (None, 0.0)

    # First try country-specific mapping
    if country and country in ETHNIDATA_COUNTRY_REFINEMENT:
        return (ETHNIDATA_COUNTRY_REFINEMENT[country], confidence)

    # Fall back to region mapping
    if region and region in ETHNIDATA_REGION_TO_UNIFIED:
        unified = ETHNIDATA_REGION_TO_UNIFIED[region]
        return (unified, confidence * 0.7) if unified else (None, 0.0)  # Lower confidence for region-only

    return (None, 0.0)


def map_name2nat_to_unified(nationality: Optional[str], probability: Optional[float]) -> Tuple[Optional[str], float]:
    """
    Map name2nat nationality prediction to unified category.

    Args:
        nationality: Predicted nationality (e.g., 'American', 'Chinese', 'Indian')
        probability: Confidence probability

    Returns:
        Tuple of (unified_ethnicity, confidence)
    """
    if not nationality or not probability:
        return (None, 0.0)

    # Map nationality to unified categories using ethnidata country mapping
    unified = ETHNIDATA_COUNTRY_REFINEMENT.get(nationality)
    if unified:
        return (unified, probability)

    # Try common nationality name variations
    if 'American' in nationality:
        return ('North American', probability * 0.7)
    elif 'English' in nationality or 'British' in nationality:
        return ('European', probability * 0.9)
    elif 'Japanese' in nationality:
        return ('East Asian', probability)
    elif 'Korean' in nationality:
        return ('East Asian', probability)
    elif 'Indian' in nationality:
        return ('South Asian', probability)
    elif 'French' in nationality or 'German' in nationality or 'Italian' in nationality:
        return ('European', probability)

    return (None, 0.0)


def map_racebert_to_unified(race: Optional[str], score: Optional[float]) -> Tuple[Optional[str], float]:
    """
    Map raceBERT race prediction to unified category.

    Args:
        race: Predicted race (e.g., 'nh_white', 'nh_black', 'nh_api', 'hispanic')
        score: Confidence score

    Returns:
        Tuple of (unified_ethnicity, confidence)
    """
    if not race or not score:
        return (None, 0.0)

    # raceBERT uses census-style categories
    racebert_mapping = {
        'nh_white': 'European/Caucasian',
        'nh_black': 'African/African American',
        'nh_api': 'Asian/Pacific Islander',
        'nh_aian': 'Native American',
        'nh_2prace': 'Mixed',
        'hispanic': 'Hispanic/Latino'
    }

    unified = racebert_mapping.get(race)
    return (unified, score) if unified else (None, 0.0)


def calculate_consensus(
    ethnicseer_ethnicity: Optional[str] = None,
    ethnicseer_confidence: Optional[float] = None,
    pyethnicity_asian: Optional[float] = None,
    pyethnicity_black: Optional[float] = None,
    pyethnicity_hispanic: Optional[float] = None,
    pyethnicity_white: Optional[float] = None,
    ethnidata_country: Optional[str] = None,
    ethnidata_region: Optional[str] = None,
    ethnidata_confidence: Optional[float] = None,
    name2nat_nationality: Optional[str] = None,
    name2nat_probability: Optional[float] = None,
    racebert_race: Optional[str] = None,
    racebert_score: Optional[float] = None
) -> Tuple[Optional[str], float, Dict[str, float]]:
    """
    Calculate consensus ethnicity from multiple tool predictions.

    Args:
        ethnicseer_ethnicity: ethnicseer ethnic category code
        ethnicseer_confidence: ethnicseer confidence score
        pyethnicity_asian: probability of Asian
        pyethnicity_black: probability of Black
        pyethnicity_hispanic: probability of Hispanic
        pyethnicity_white: probability of White
        ethnidata_country: predicted country name
        ethnidata_region: predicted region
        ethnidata_confidence: ethnidata confidence score
        name2nat_nationality: name2nat predicted nationality
        name2nat_probability: name2nat prediction probability
        racebert_race: raceBERT predicted race category
        racebert_score: raceBERT prediction score

    Returns:
        Tuple of (consensus_ethnicity, confidence, vote_weights)
    """
    votes = {}  # ethnicity -> weight

    # Process ethnicseer
    if ethnicseer_ethnicity:
        unified, conf = map_ethnicseer_to_unified(ethnicseer_ethnicity, ethnicseer_confidence or 1.0)
        if unified:
            weight = get_tool_weight('ethnicseer', unified) * conf
            votes[unified] = votes.get(unified, 0.0) + weight

    # Process pyethnicity
    race_probs = {}
    if pyethnicity_asian is not None:
        race_probs['asian'] = pyethnicity_asian
    if pyethnicity_black is not None:
        race_probs['black'] = pyethnicity_black
    if pyethnicity_hispanic is not None:
        race_probs['hispanic'] = pyethnicity_hispanic
    if pyethnicity_white is not None:
        race_probs['white'] = pyethnicity_white

    if race_probs:
        unified, conf = map_pyethnicity_to_unified(race_probs)
        if unified:
            weight = get_tool_weight('pyethnicity', unified) * conf
            votes[unified] = votes.get(unified, 0.0) + weight

    # Process ethnidata
    if ethnidata_country or ethnidata_region:
        unified, conf = map_ethnidata_to_unified(
            ethnidata_country,
            ethnidata_region,
            ethnidata_confidence or 0.0
        )
        if unified:
            weight = get_tool_weight('ethnidata', unified) * conf
            votes[unified] = votes.get(unified, 0.0) + weight

    # Process name2nat
    if name2nat_nationality:
        unified, conf = map_name2nat_to_unified(name2nat_nationality, name2nat_probability or 0.0)
        if unified:
            weight = get_tool_weight('name2nat', unified) * conf
            votes[unified] = votes.get(unified, 0.0) + weight

    # Process raceBERT
    if racebert_race:
        unified, conf = map_racebert_to_unified(racebert_race, racebert_score or 0.0)
        if unified:
            weight = get_tool_weight('racebert', unified) * conf
            votes[unified] = votes.get(unified, 0.0) + weight

    # If no valid predictions, return None
    if not votes:
        return (None, 0.0, {})

    # Find consensus (highest weighted vote)
    consensus = max(votes, key=votes.get)

    # Calculate confidence as normalized weight
    total_weight = sum(votes.values())
    confidence = votes[consensus] / total_weight if total_weight > 0 else 0.0

    # Normalize votes to percentages for reporting
    vote_percentages = {k: (v / total_weight * 100) for k, v in votes.items()}

    return (consensus, confidence, vote_percentages)


def main():
    """
    Test function to demonstrate consensus calculation.
    """
    # Example 1: Chinese name
    print("Example 1: Wei Wang (Chinese name)")
    consensus, confidence, votes = calculate_consensus(
        ethnicseer_ethnicity='chi',
        ethnicseer_confidence=0.999,
        pyethnicity_asian=0.9999,
        pyethnicity_black=0.00002,
        pyethnicity_hispanic=0.00005,
        pyethnicity_white=0.00003,
        ethnidata_country='China',
        ethnidata_region='Asia',
        ethnidata_confidence=0.95
    )
    print(f"  Consensus: {consensus}")
    print(f"  Confidence: {confidence:.3f}")
    print(f"  Votes: {json.dumps(votes, indent=4)}")
    print()

    # Example 2: Indian name
    print("Example 2: Rajesh Kumar (Indian name)")
    consensus, confidence, votes = calculate_consensus(
        ethnicseer_ethnicity='ind',
        ethnicseer_confidence=0.9998,
        pyethnicity_asian=0.85,
        pyethnicity_black=0.05,
        pyethnicity_hispanic=0.05,
        pyethnicity_white=0.05,
        ethnidata_country='India',
        ethnidata_region='Asia',
        ethnidata_confidence=0.88
    )
    print(f"  Consensus: {consensus}")
    print(f"  Confidence: {confidence:.3f}")
    print(f"  Votes: {json.dumps(votes, indent=4)}")
    print()

    # Example 3: Hispanic name
    print("Example 3: Maria Garcia (Hispanic name)")
    consensus, confidence, votes = calculate_consensus(
        ethnicseer_ethnicity='spa',
        ethnicseer_confidence=0.95,
        pyethnicity_asian=0.005,
        pyethnicity_black=0.001,
        pyethnicity_hispanic=0.994,
        pyethnicity_white=0.0002,
        ethnidata_country='Spain',
        ethnidata_region='Europe',
        ethnidata_confidence=0.82
    )
    print(f"  Consensus: {consensus}")
    print(f"  Confidence: {confidence:.3f}")
    print(f"  Votes: {json.dumps(votes, indent=4)}")
    print()


if __name__ == '__main__':
    main()
