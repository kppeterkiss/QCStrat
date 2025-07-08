def detect_candlestick_patterns(highs, lows, closes, opens):
    """Detect various candlestick patterns"""
    patterns = {}
    
    # Single candlestick patterns
    # Doji
    body = abs(closes[-1] - opens[-1])
    wick = highs[-1] - max(opens[-1], closes[-1])
    tail = min(opens[-1], closes[-1]) - lows[-1]
    if body <= 0.1 * (highs[-1] - lows[-1]):
        patterns['doji'] = True
        # Dragonfly doji
        if wick <= 0.1 * (highs[-1] - lows[-1]) and tail >= 0.7 * (highs[-1] - lows[-1]):
            patterns['dragonfly_doji'] = True
        # Gravestone doji
        if wick >= 0.7 * (highs[-1] - lows[-1]) and tail <= 0.1 * (highs[-1] - lows[-1]):
            patterns['gravestone_doji'] = True

    # Hammer
    if tail >= 2 * body and wick <= 0.1 * (highs[-1] - lows[-1]):
        patterns['hammer'] = True

    # Inverted Hammer
    if wick >= 2 * body and tail <= 0.1 * (highs[-1] - lows[-1]):
        patterns['inverted_hammer'] = True

    # Shooting Star
    if wick >= 2 * body and tail <= body and opens[-1] < closes[-1]:
        patterns['shooting_star'] = True

    # Spinning Top
    if 0.3 <= body/(highs[-1] - lows[-1]) <= 0.7:
        patterns['spinning_top'] = True

    # Marubozu
    if wick <= 0.1 * body and tail <= 0.1 * body:
        patterns['bearish_marubozu'] = closes[-1] < opens[-1]

    # Two candlestick patterns
    # Bullish Engulfing
    if closes[-1] > opens[-1] and opens[-1] < closes[-2] and closes[-1] > opens[-2] and opens[-2] > closes[-2]:
        patterns['bullish_engulfing'] = True

    # Bearish Engulfing
    if closes[-1] < opens[-1] and opens[-1] > closes[-2] and closes[-1] < opens[-2] and opens[-2] < closes[-2]:
        patterns['bearish_engulfing'] = True

    # Bullish Harami
    if closes[-2] < opens[-2] and opens[-1] > closes[-1] and \
       opens[-1] <= closes[-2] and closes[-1] >= opens[-2]:
        patterns['bullish_harami'] = True
        # Bullish Harami Cross
        if abs(opens[-1] - closes[-1]) <= 0.1 * (highs[-1] - lows[-1]):
            patterns['bullish_harami_cross'] = True

    # Bearish Harami
    if closes[-2] > opens[-2] and opens[-1] < closes[-1] and \
       opens[-1] >= closes[-2] and closes[-1] <= opens[-2]:
        patterns['bearish_harami'] = True
        # Bearish Harami Cross
        if abs(opens[-1] - closes[-1]) <= 0.1 * (highs[-1] - lows[-1]):
            patterns['bearish_harami_cross'] = True

    # Piercing Line
    if closes[-2] < opens[-2] and closes[-1] > opens[-1] and \
       opens[-1] < lows[-2] and closes[-1] > (opens[-2] + closes[-2])/2:
        patterns['piercing_line'] = True

    # Chart Patterns (requires more historical data)
    if len(highs) >= 20:
        # Head and Shoulders
        left_shoulder = max(highs[-20:-15])
        head = max(highs[-15:-10])
        right_shoulder = max(highs[-10:-5])
        if head > left_shoulder and head > right_shoulder and \
           abs(left_shoulder - right_shoulder)/left_shoulder < 0.02:
            patterns['head_and_shoulders'] = True

        # Bull Flag
        if all(highs[i] < highs[i-1] for i in range(-1, -6, -1)) and \
           all(lows[i] < lows[i-1] for i in range(-1, -6, -1)):
            patterns['bull_flag'] = True

        # Ascending Triangle
        resistance = max(highs[-20:])
        if all(lows[i] > lows[i-1] for i in range(-1, -10, -1)) and \
           all(abs(highs[i] - resistance) < 0.02 * resistance for i in range(-1, -10, -1)):
            patterns['ascending_triangle'] = True

        # Descending Triangle
        support = min(lows[-20:])
        if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
           all(abs(lows[i] - support) < 0.02 * support for i in range(-1, -10, -1)):
            patterns['descending_triangle'] = True

        # Rising Wedge
        if all(highs[i] > highs[i-1] for i in range(-1, -10, -1)) and \
           all(lows[i] > lows[i-1] for i in range(-1, -10, -1)):
            patterns['rising_wedge'] = True

        # Falling Wedge
        if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
           all(lows[i] < lows[i-1] for i in range(-1, -10, -1)):
            patterns['falling_wedge'] = True

        # Cup and Handle
        cup_bottom = min(lows[-20:-10])
        if all(lows[i] > cup_bottom for i in range(-9, -1)):
            patterns['cup_and_handle'] = True

        # Megaphone
        if all(highs[i] > highs[i-1] for i in range(-1, -10, -1)) and \
           all(lows[i] < lows[i-1] for i in range(-1, -10, -1)):
            patterns['megaphone'] = True

        # Pennant
        if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
           all(lows[i] > lows[i-1] for i in range(-1, -10, -1)):
            patterns['pennant'] = True

    return patterns 