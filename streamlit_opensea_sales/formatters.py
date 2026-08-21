"""
technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.

technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text, technical diagnostic text, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text UI.
"""

from typing import Union, Tuple


def get_rarity_style(rarity: str) -> Tuple[str, str]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        rarity: technical diagnostic text technical diagnostic text (Common, Uncommon, Rare, Epic, Legendary)
    
    Returns:
        Tuple[str, str]: (hex_color, css_class)
    """
    rarity_colors = {
        'Common': ('#ffffff', 'common'),
        'Uncommon': ('#1eff00', 'uncommon'),
        'Rare': ('#0070dd', 'rare'),
        'Epic': ('#a335ee', 'epic'),
        'Legendary': ('#ff8000', 'legendary')
    }
    return rarity_colors.get(rarity, ('#ffffff', 'common'))


def format_number(
    number: float,
    show_usd: bool = False,
    gun_price: float = 0.03,
    currency: str = 'GUN',
    include_both: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        number: technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text USD
        gun_price: technical diagnostic text GUN technical diagnostic text USD (technical diagnostic text technical diagnostic text 0.03)
        currency: technical diagnostic text ('GUN' technical diagnostic text 'WGUN')
        include_both: technical diagnostic text technical diagnostic text technical diagnostic text (GUN technical diagnostic text USD)
    
    Returns:
        Union[str, Tuple[str, str]]: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text (gun_format, usd_format)
    """
    gun_formatted = ""
    usd_formatted = ""
    
    if number >= 1000000:
        gun_formatted = f"{number/1000000:.1f}M {currency}"
    elif number >= 1000:
        gun_formatted = f"{number/1000:.1f}k {currency}"
    else:
        gun_formatted = f"{number:.2f} {currency}"
        
    usd_value = number * gun_price
    if usd_value >= 1000000:
        usd_formatted = f"${usd_value/1000000:.1f}M"
    elif usd_value >= 1000:
        usd_formatted = f"${usd_value/1000:.1f}k"
    else:
        usd_formatted = f"${usd_value:.2f}"
        
    if include_both:
        return gun_formatted, usd_formatted
    return usd_formatted if show_usd else gun_formatted


def format_metric_value(
    value: float,
    show_usd: bool,
    gun_price: float,
    currency: str = 'GUN'
) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text tooltiptechnical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    technical diagnostic text technical diagnostic text technical diagnostic text, tooltip technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        value: technical diagnostic text technical diagnostic text technical diagnostic text
        show_usd: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text USD
        gun_price: technical diagnostic text GUN technical diagnostic text USD
        currency: technical diagnostic text technical diagnostic text technical diagnostic text
    
    Returns:
        str: HTML technical diagnostic text tooltip
    """
    main_value = format_number(value, show_usd, gun_price, currency=currency)
    opposite_currency = 'GUN'
    opposite_value = format_number(value, not show_usd, gun_price, currency=opposite_currency)

    return f"""
        <div class="tooltip">
            {main_value}
            <span class="tooltiptext">{opposite_value}</span>
        </div>
    """


def format_historical_metric_pair(
    gun_value: float,
    usd_value: float,
    show_usd: bool,
    currency: str = "GUN",
    usd_label: str = "USD",
    gun_label: str = "GUN"
) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text GUN/USD technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text tooltip.
    
    technical diagnostic text technical diagnostic text enriched technical diagnostic text, technical diagnostic text GUN technical diagnostic text USD — technical diagnostic text technical diagnostic text,
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text current price.
    
    Args:
        gun_value: GUN technical diagnostic text (technical diagnostic text technical diagnostic text)
        usd_value: Historical USD technical diagnostic text (technical diagnostic text technical diagnostic text)
        show_usd: technical diagnostic text True, technical diagnostic text technical diagnostic text USD, tooltip GUN
                 technical diagnostic text False, technical diagnostic text technical diagnostic text GUN, tooltip USD
        currency: technical diagnostic text technical diagnostic text technical diagnostic text GUN (technical diagnostic text 'GUN')
        usd_label: technical diagnostic text technical diagnostic text tooltip USD technical diagnostic text
        gun_label: technical diagnostic text technical diagnostic text tooltip GUN technical diagnostic text
    
    Returns:
        str: HTML technical diagnostic text tooltip, technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    """
    import math
    
    # Handle NaN/missing values
    if gun_value != gun_value:  # NaN check
        gun_value = 0
    if usd_value != usd_value:  # NaN check
        usd_value = 0
    
    # Format GUN value
    if abs(gun_value) >= 1000000:
        gun_formatted = f"{gun_value/1000000:.1f}M {currency}"
    elif abs(gun_value) >= 1000:
        gun_formatted = f"{gun_value/1000:.1f}k {currency}"
    else:
        gun_formatted = f"{gun_value:.2f} {currency}"
    
    # Format USD value
    if abs(usd_value) >= 1000000:
        usd_formatted = f"${usd_value/1000000:.1f}M"
    elif abs(usd_value) >= 1000:
        usd_formatted = f"${usd_value/1000:.1f}k"
    else:
        usd_formatted = f"${usd_value:.2f}"
    
    # Determine main and tooltip values
    if show_usd:
        if usd_value == 0:
            # USD unavailable
            main_value = gun_formatted
            tooltip_text = "USD: unavailable"
        else:
            main_value = usd_formatted
            tooltip_text = gun_formatted
    else:
        main_value = gun_formatted
        if usd_value == 0:
            tooltip_text = "USD: unavailable"
        else:
            tooltip_text = f"{usd_label}: {usd_formatted}"
    
    return f"""
        <div class="tooltip">
            {main_value}
            <span class="tooltiptext">{tooltip_text}</span>
        </div>
    """


def shorten_address(address: str, length: int = 8) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text.
    
    Args:
        address: technical diagnostic text technical diagnostic text
        length: technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text technical diagnostic text
    
    Returns:
        str: technical diagnostic text technical diagnostic text (e.g., "0x1234...abcd")
    """
    if not isinstance(address, str):
        return str(address)
    return f"{address[:length]}...{address[-length:]}"


def format_opensea_link(address: str) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text OpenSea technical diagnostic text.
    
    Args:
        address: Address technical diagnostic text technical diagnostic text technical diagnostic text
    
    Returns:
        str: URL OpenSea technical diagnostic text
    """
    return f"https://opensea.io/{address}"


def format_gunzscan_link(tx_hash: str) -> str:
    """
    technical diagnostic text technical diagnostic text technical diagnostic text gunzscan technical diagnostic text technical diagnostic text.
    
    Args:
        tx_hash: technical diagnostic text technical diagnostic text
    
    Returns:
        str: URL gunzscan technical diagnostic text
    """
    return f"https://gunzscan.io/tx/{tx_hash}"
