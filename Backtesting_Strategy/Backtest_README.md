# What problem are we solving?
Independent traders have developed custom stock entry strategies (e.g., on Chartink or similar platforms) but lack access to affordable, flexible tools to rigorously backtest those strategies against historical data. Without validation, they risk deploying unproven logic in live markets, leading to avoidable losses.

<br><br>

# What you have to do in high level first?

- Convert all your strategy of the particular dashboard in Python from claude
- Get the API Key and TOTP_SECRET from any broker. I used the Angelone here.
- What is the process to get that - https://smartapi.angelbroking.com/
- In the redirection on the next screen to obtain the API key, you can put this - https://127.0.0.1 https://127.0.0.1
- After this, you can see the API key, but in order to get the TOTP check the top nav of the same screen from there you can take


<br><br>


# Make this changes in codebase
- Download this codebase and put that into some new folder
- Change the location of this file in the code according to your folder where you saved this codebase
- First import the libraries and after that run this in your terminal -   
    1. pip install pyotp pandas numpy requests pytz  
    2. pip install smartapi-python pyotp
- Now lets say if your total setup is ready then in order to get the desired result run this command - python nse_backtest.py
 

<br><br>

# Limitations
- Stock Selection: This backtest code currently supports only FNO (Futures and Options) stocks. If you intend to trade smallcap stocks, you will need to modify the stock list accordingly time to time.
- Timeframe Support: The tool is optimized for 5-minute candles of last 30 days. If you wish to use smaller timeframes, you may need to adjust the date range accordingly to ensure sufficient historical data is available for accurate backtesting.




