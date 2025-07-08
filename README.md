# QuantConnect Local Development Guide

This guide will help you set up and run your QuantConnect project locally. The project implements a technical analysis-based trading strategy using various indicators and patterns.

## Prerequisites

1. Python 3.8 or higher
2. Git
3. QuantConnect CLI (optional, for direct deployment)

## Setup Instructions

1. **Install Required Python Packages**
   ```bash
   pip install -r requirements.txt
   ```

2. **Project Structure**
   ```
   QCStrat/
   ├── main.py                    # Main algorithm implementation
   ├── models/                    # Trading strategy models
   │   ├── __init__.py
   │   ├── technical_alpha.py     # Technical analysis alpha model
   │   └── portfolio_construction.py # Portfolio construction model
   ├── indicators/                # Technical indicators
   │   ├── __init__.py
   │   ├── indicator_strength.py  # Indicator performance tracking
   │   ├── technical_indicators.py # Basic technical indicators
   │   └── candlestick_patterns.py # Candlestick pattern detection
   ├── requirements.txt           # Python dependencies
   └── README.md                  # This file
   ```

3. **Running Locally**

   a. **Using QuantConnect CLI (Recommended)**
   ```bash
   # Install QuantConnect CLI
   pip install quantconnect-cli

   # Login to your QuantConnect account
   qc login

   # Run the project locally
   qc run --project QCStrat
   ```

   b. **Using QuantConnect Research Environment**
   - Log in to your QuantConnect account
   - Go to the Research tab
   - Create a new research notebook
   - Copy the contents of `main.py` into the notebook
   - Run the code in the notebook environment

4. **Deploying to QuantConnect**
   ```bash
   # Deploy the project to QuantConnect
   qc deploy --project QCStrat
   ```

## Strategy Overview

The strategy implements a technical analysis-based trading system that:

1. Uses multiple technical indicators:
   - Trendlines
   - Support/Resistance levels
   - Fibonacci levels
   - Candlestick patterns
   - Volume analysis

2. Generates trading signals based on:
   - Pattern recognition
   - Trend analysis
   - Volume confirmation
   - Multiple timeframe analysis

3. Implements risk management through:
   - Position sizing
   - Stop-loss levels
   - Portfolio diversification

## Configuration

The strategy can be configured by modifying the following parameters:

- In `models/technical_alpha.py`:
  - `lookback_period`: Period for calculating indicators (default: 30 days)
  - `period`: Moving average period (default: 20)
  - `rebalancingPeriod`: Time between portfolio rebalancing (default: 1 hour)

- In `indicators/indicator_strength.py`:
  - `lookback_period`: Period for evaluating indicator performance (default: 30 days)

## Troubleshooting

1. **Common Issues**
   - If you encounter dependency issues, try:
     ```bash
     pip install --upgrade -r requirements.txt
     ```
   - If the QuantConnect CLI fails to connect, check your internet connection and try:
     ```bash
     qc logout
     qc login
     ```

2. **Getting Help**
   - Visit the [QuantConnect Documentation](https://www.quantconnect.com/docs)
   - Join the [QuantConnect Community](https://www.quantconnect.com/forum)
   - Contact QuantConnect Support

## License

This project is licensed under the MIT License - see the LICENSE file for details. 