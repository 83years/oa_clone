#!/usr/bin/env python3
"""
Gender consensus logic for combining results from multiple gender inference tools.

This module provides functions to:
1. Weight gender predictions based on population specificity
2. Combine multiple predictions into a consensus result
3. Calculate confidence scores for the consensus

Population-specific tools get higher weight for their target populations:
- genderpred-in: India
- persian-gender-detection: Iran
- genderizer3: Turkey (and general multilingual)
- chicksexer: General with cultural context
- genderComputer: General
- gender-guesser: General
- namesex: General - Chinese 
"""

from typing import Dict, Optional, Tuple, List
import logging


def get_tool_weight(tool_name: str, country: Optional[str] = None) -> float:
    """
    Get the weight for a specific tool based on the author's country.

    Population-specific tools get higher weights for their target populations.

    Args:
        tool_name (str): Name of the gender inference tool
        country (str, optional): Country of the author

    Returns:
        float: Weight value (0.0 to 2.0)
    """
    if country:
        country_lower = country.lower()

        if tool_name == 'genderpred_in' and 'india' in country_lower:
            return 2.0
        elif tool_name == 'persian' and 'iran' in country_lower:
            return 2.0
        elif tool_name == 'genderizer3' and 'turkey' in country_lower:
            return 1.5

    base_weights = {
        'gendercomputer': 1.2,
        'genderguesser': 1.0,
        'chicksexer': 1.3,
        'gpt': 1.5,
        'genderpred_in': 0.8,
        'namesex': 1.0,
        'persian': 0.5,
        'genderizer3': 0.9
    }

    return base_weights.get(tool_name, 1.0)


def normalize_gender(gender_value: Optional[str]) -> Optional[str]:
    """
    Normalize gender values from different tools to standard format.

    Args:
        gender_value (str, optional): Gender value from a tool

    Returns:
        str or None: Normalized gender ('male', 'female', or None for unknown/uncertain)
    """
    if not gender_value:
        return None

    gender_lower = gender_value.lower().strip()

    if gender_lower in ['male', 'm', '1']:
        return 'male'
    elif gender_lower in ['female', 'f', '0']:
        return 'female'
    elif gender_lower in ['mostly_male']:
        return 'male'
    elif gender_lower in ['mostly_female']:
        return 'female'
    else:
        return None


def calculate_consensus(
    gendercomputer: Optional[str] = None,
    genderguesser: Optional[str] = None,
    gpt: Optional[str] = None,
    gpt_prob: Optional[float] = None,
    genderpred_in: Optional[str] = None,
    genderpred_in_male_prob: Optional[float] = None,
    genderpred_in_female_prob: Optional[float] = None,
    namesex: Optional[str] = None,
    namesex_prob: Optional[float] = None,
    persian: Optional[str] = None,
    genderizer3: Optional[str] = None,
    chicksexer: Optional[str] = None,
    chicksexer_male_prob: Optional[float] = None,
    chicksexer_female_prob: Optional[float] = None,
    country: Optional[str] = None
) -> Tuple[Optional[str], float, Dict[str, int]]:
    """
    Calculate consensus gender from multiple tool predictions.

    This function:
    1. Normalizes all gender predictions
    2. Applies population-specific weights
    3. Incorporates probability scores where available
    4. Calculates weighted votes for male/female
    5. Returns consensus gender, confidence score, and vote breakdown

    Args:
        gendercomputer (str, optional): genderComputer prediction
        genderguesser (str, optional): gender-guesser prediction
        gpt (str, optional): ChatGPT prediction
        gpt_prob (float, optional): ChatGPT probability score
        genderpred_in (str, optional): genderpred-in prediction
        genderpred_in_male_prob (float, optional): genderpred-in male probability
        genderpred_in_female_prob (float, optional): genderpred-in female probability
        namesex (str, optional): namesex prediction
        namesex_prob (float, optional): namesex probability score
        persian (str, optional): persian-gender-detection prediction
        genderizer3 (str, optional): genderizer3 prediction
        chicksexer (str, optional): chicksexer prediction
        chicksexer_male_prob (float, optional): chicksexer male probability
        chicksexer_female_prob (float, optional): chicksexer female probability
        country (str, optional): Author's country for population-specific weighting

    Returns:
        tuple: (consensus_gender, confidence, vote_breakdown)
            - consensus_gender (str or None): 'male', 'female', or None if uncertain
            - confidence (float): Confidence score (0.0 to 1.0)
            - vote_breakdown (dict): {'male': weight, 'female': weight, 'unknown': weight}
    """
    logger = logging.getLogger(__name__)

    male_votes = 0.0
    female_votes = 0.0
    unknown_votes = 0.0
    total_weight = 0.0

    tools = {
        'gendercomputer': (gendercomputer, None, None),
        'genderguesser': (genderguesser, None, None),
        'gpt': (gpt, gpt_prob, None),
        'genderpred_in': (genderpred_in, genderpred_in_male_prob, genderpred_in_female_prob),
        'namesex': (namesex, namesex_prob, None),
        'persian': (persian, None, None),
        'genderizer3': (genderizer3, None, None),
        'chicksexer': (chicksexer, chicksexer_male_prob, chicksexer_female_prob)
    }

    for tool_name, (prediction, male_prob, female_prob) in tools.items():
        base_weight = get_tool_weight(tool_name, country)

        normalized = normalize_gender(prediction)

        if normalized == 'male':
            prob_multiplier = male_prob if male_prob and male_prob > 0 else 1.0
            male_votes += base_weight * prob_multiplier
            total_weight += base_weight
        elif normalized == 'female':
            prob_multiplier = female_prob if female_prob and female_prob > 0 else 1.0
            female_votes += base_weight * prob_multiplier
            total_weight += base_weight
        else:
            unknown_votes += base_weight * 0.5
            total_weight += base_weight

    if total_weight == 0:
        return None, 0.0, {'male': 0, 'female': 0, 'unknown': 0}

    male_ratio = male_votes / total_weight
    female_ratio = female_votes / total_weight

    threshold = 0.5

    if male_ratio > threshold and male_ratio > female_ratio:
        consensus = 'male'
        confidence = male_ratio
    elif female_ratio > threshold and female_ratio > male_ratio:
        consensus = 'female'
        confidence = female_ratio
    else:
        consensus = None
        confidence = max(male_ratio, female_ratio)

    vote_breakdown = {
        'male': round(male_votes, 2),
        'female': round(female_votes, 2),
        'unknown': round(unknown_votes, 2)
    }

    return consensus, round(confidence, 4), vote_breakdown


def apply_consensus_to_batch(
    batch: List[Tuple],
    column_indices: Dict[str, int]
) -> List[Tuple[Optional[str], float, str]]:
    """
    Apply consensus logic to a batch of author records.

    Args:
        batch (list): List of tuples containing author data
        column_indices (dict): Mapping of column names to their indices in the batch tuples

    Returns:
        list: List of tuples (consensus_gender, confidence, vote_breakdown_json)
    """
    results = []

    for row in batch:
        kwargs = {}

        if 'gendercomputer_gender' in column_indices:
            kwargs['gendercomputer'] = row[column_indices['gendercomputer_gender']]

        if 'genderguesser_gender' in column_indices:
            kwargs['genderguesser'] = row[column_indices['genderguesser_gender']]

        if 'gpt_gender' in column_indices:
            kwargs['gpt'] = row[column_indices['gpt_gender']]
        if 'gpt_probability' in column_indices:
            kwargs['gpt_prob'] = row[column_indices['gpt_probability']]

        if 'genderpred_in_gender' in column_indices:
            kwargs['genderpred_in'] = row[column_indices['genderpred_in_gender']]
        if 'genderpred_in_male_prob' in column_indices:
            kwargs['genderpred_in_male_prob'] = row[column_indices['genderpred_in_male_prob']]
        if 'genderpred_in_female_prob' in column_indices:
            kwargs['genderpred_in_female_prob'] = row[column_indices['genderpred_in_female_prob']]

        if 'namesex_gender' in column_indices:
            kwargs['namesex'] = row[column_indices['namesex_gender']]
        if 'namesex_prob' in column_indices:
            kwargs['namesex_prob'] = row[column_indices['namesex_prob']]

        if 'persian_gender' in column_indices:
            kwargs['persian'] = row[column_indices['persian_gender']]

        if 'genderizer3_gender' in column_indices:
            kwargs['genderizer3'] = row[column_indices['genderizer3_gender']]

        if 'chicksexer_gender' in column_indices:
            kwargs['chicksexer'] = row[column_indices['chicksexer_gender']]
        if 'chicksexer_male_prob' in column_indices:
            kwargs['chicksexer_male_prob'] = row[column_indices['chicksexer_male_prob']]
        if 'chicksexer_female_prob' in column_indices:
            kwargs['chicksexer_female_prob'] = row[column_indices['chicksexer_female_prob']]

        if 'country_name' in column_indices:
            kwargs['country'] = row[column_indices['country_name']]

        consensus, confidence, votes = calculate_consensus(**kwargs)

        vote_json = str(votes)

        results.append((consensus if consensus else '', confidence, vote_json))

    return results


if __name__ == '__main__':
    import json

    test_cases = [
        {
            'name': 'All agree on male',
            'data': {
                'gendercomputer': 'male',
                'genderguesser': 'male',
                'chicksexer': 'male',
                'country': 'USA'
            }
        },
        {
            'name': 'Indian name with genderpred-in',
            'data': {
                'gendercomputer': 'male',
                'genderguesser': 'unknown',
                'genderpred_in': 'female',
                'genderpred_in_female_prob': 0.95,
                'country': 'India'
            }
        },
        {
            'name': 'Iranian name with persian-gender-detection',
            'data': {
                'gendercomputer': 'male',
                'persian': 'female',
                'country': 'Iran'
            }
        },
        {
            'name': 'Split decision',
            'data': {
                'gendercomputer': 'male',
                'genderguesser': 'female',
                'chicksexer': 'male',
                'country': 'UK'
            }
        }
    ]

    print("GENDER CONSENSUS TESTING")
    print("="*70)

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {json.dumps(test['data'], indent=2)}")

        consensus, confidence, votes = calculate_consensus(**test['data'])

        print(f"Result: {consensus} (confidence: {confidence:.2f})")
        print(f"Votes: {votes}")
        print("-"*70)
