#!/usr/bin/env python3
"""
Country code mapping for genderComputer compatibility.

Maps ISO 3166-1 alpha-2 country codes to country names expected by genderComputer.
The mapping prioritizes country names that genderComputer has specific data for.
"""

# ISO 3166-1 alpha-2 to genderComputer country name mapping
ISO_TO_GENDER_COMPUTER = {
    # Countries with specific name lists in genderComputer
    'AF': 'Afghanistan',
    'AL': 'Albania',
    'AU': 'Australia',
    'BE': 'Belgium',
    'BR': 'Brazil',
    'CA': 'Canada',
    'CZ': 'Czech Republic',
    'FI': 'Finland',
    'GR': 'Greece',
    'HU': 'Hungary',
    'IN': 'India',
    'IR': 'Iran',
    'IE': 'Ireland',
    'IL': 'Israel',
    'IT': 'Italy',
    'JP': 'Japan',
    'LV': 'Latvia',
    'NO': 'Norway',
    'PL': 'Poland',
    'RO': 'Romania',
    'RU': 'Russia',
    'SI': 'Slovenia',
    'SO': 'Somalia',
    'ES': 'Spain',
    'SE': 'Sweden',
    'TR': 'Turkey',
    'GB': 'UK',
    'UA': 'Ukraine',
    'US': 'USA',

    # Countries in the gender.c database (countriesOrder)
    'MT': 'Malta',
    'PT': 'Portugal',
    'FR': 'France',
    'LU': 'Luxembourg',
    'NL': 'The Netherlands',
    'DE': 'Germany',
    'AT': 'Austria',
    'CH': 'Switzerland',
    'IS': 'Iceland',
    'DK': 'Denmark',
    'EE': 'Estonia',
    'LT': 'Lithuania',
    'SK': 'Slovakia',
    'BG': 'Bulgaria',
    'BA': 'Bosnia and Herzegovina',
    'HR': 'Croatia',
    'XK': 'Kosovo',
    'MK': 'Macedonia (FYROM)',
    'ME': 'Montenegro',
    'RS': 'Serbia',
    'BY': 'Belarus',
    'MD': 'Moldova',
    'AM': 'Armenia',
    'AZ': 'Azerbaijan',
    'GE': 'Georgia',
    'KZ': 'Kazakhstan',
    'CN': 'China',
    'KR': 'Korea',
    'KP': 'Korea',
    'VN': 'Vietnam',

    # Arabia/Persia region (normalised by genderComputer)
    'DZ': 'Algeria',
    'BH': 'Bahrain',
    'KM': 'Comoros',
    'DJ': 'Djibouti',
    'EG': 'Egypt',
    'IQ': 'Iraq',
    'JO': 'Jordan',
    'KW': 'Kuwait',
    'LB': 'Lebanon',
    'LY': 'Libya',
    'MR': 'Mauritania',
    'MA': 'Morocco',
    'OM': 'Oman',
    'PS': 'Palestine',
    'QA': 'Qatar',
    'SA': 'Saudi Arabia',
    'SD': 'Sudan',
    'SY': 'Syria',
    'TN': 'Tunisia',
    'AE': 'United Arab Emirates',
    'YE': 'Yemen',

    # India/Sri Lanka region (normalised by genderComputer)
    'BD': 'Bangladesh',
    'PK': 'Pakistan',
    'LK': 'Sri Lanka',

    # Other countries (will use 'other countries' in gender.c)
    'AR': 'Argentina',
    'BO': 'Bolivia',
    'CL': 'Chile',
    'CO': 'Colombia',
    'CR': 'Costa Rica',
    'CU': 'Cuba',
    'DO': 'Dominican Republic',
    'EC': 'Ecuador',
    'SV': 'El Salvador',
    'GT': 'Guatemala',
    'HN': 'Honduras',
    'MX': 'Mexico',
    'NI': 'Nicaragua',
    'PA': 'Panama',
    'PY': 'Paraguay',
    'PE': 'Peru',
    'UY': 'Uruguay',
    'VE': 'Venezuela',

    # Africa
    'AO': 'Angola',
    'BJ': 'Benin',
    'BW': 'Botswana',
    'BF': 'Burkina Faso',
    'BI': 'Burundi',
    'CM': 'Cameroon',
    'CV': 'Cape Verde',
    'CF': 'Central African Republic',
    'TD': 'Chad',
    'CG': 'Congo',
    'CD': 'Democratic Republic of the Congo',
    'CI': 'Ivory Coast',
    'ER': 'Eritrea',
    'ET': 'Ethiopia',
    'GA': 'Gabon',
    'GM': 'Gambia',
    'GH': 'Ghana',
    'GN': 'Guinea',
    'GW': 'Guinea-Bissau',
    'KE': 'Kenya',
    'LS': 'Lesotho',
    'LR': 'Liberia',
    'MG': 'Madagascar',
    'MW': 'Malawi',
    'ML': 'Mali',
    'MU': 'Mauritius',
    'MZ': 'Mozambique',
    'NA': 'Namibia',
    'NE': 'Niger',
    'NG': 'Nigeria',
    'RW': 'Rwanda',
    'SN': 'Senegal',
    'SL': 'Sierra Leone',
    'ZA': 'South Africa',
    'SS': 'South Sudan',
    'TZ': 'Tanzania',
    'TG': 'Togo',
    'UG': 'Uganda',
    'ZM': 'Zambia',
    'ZW': 'Zimbabwe',

    # Asia
    'KH': 'Cambodia',
    'ID': 'Indonesia',
    'LA': 'Laos',
    'MY': 'Malaysia',
    'MM': 'Myanmar',
    'NP': 'Nepal',
    'PH': 'Philippines',
    'SG': 'Singapore',
    'TH': 'Thailand',
    'TL': 'East Timor',
    'BN': 'Brunei',
    'BT': 'Bhutan',
    'MN': 'Mongolia',
    'TW': 'Taiwan',
    'HK': 'Hong Kong',
    'MO': 'Macau',

    # Central Asia
    'KG': 'Kyrgyzstan',
    'TJ': 'Tajikistan',
    'TM': 'Turkmenistan',
    'UZ': 'Uzbekistan',

    # Oceania
    'FJ': 'Fiji',
    'PG': 'Papua New Guinea',
    'NZ': 'New Zealand',
    'WS': 'Samoa',
    'TO': 'Tonga',
    'VU': 'Vanuatu',
    'SB': 'Solomon Islands',

    # Caribbean
    'BS': 'Bahamas',
    'BB': 'Barbados',
    'BZ': 'Belize',
    'GY': 'Guyana',
    'HT': 'Haiti',
    'JM': 'Jamaica',
    'SR': 'Suriname',
    'TT': 'Trinidad and Tobago',
    'AW': 'Aruba',
    'PR': 'Puerto Rico',
    'VG': 'British Virgin Islands',

    # Europe (additional)
    'AD': 'Andorra',
    'CY': 'Cyprus',
    'FO': 'Faroe Islands',
    'GI': 'Gibraltar',
    'GL': 'Greenland',
    'IM': 'Isle of Man',
    'LI': 'Liechtenstein',
    'MC': 'Monaco',
    'SM': 'San Marino',
    'VA': 'Vatican City',
}


def get_country_name(country_code):
    """
    Convert an ISO 3166-1 alpha-2 country code to a genderComputer-compatible country name.

    Args:
        country_code (str): 2-letter ISO country code (e.g., 'US', 'GB', 'CN')

    Returns:
        str: Country name compatible with genderComputer, or None if code not found
    """
    if not country_code:
        return None

    # Convert to uppercase to handle any case variations
    country_code = country_code.upper().strip()

    return ISO_TO_GENDER_COMPUTER.get(country_code, None)
