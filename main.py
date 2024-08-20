import math
import os
from datetime import date, datetime, timedelta
from replit import db
import requests


import pandas as pd
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from replit.object_storage import Client


#print(os.environ.get('REPLIT_DB_URL'))

db_url = os.environ.get('DB_URL')

# Configuration (object storage)

BUCKET_ID = os.environ.get('BUCKET_ID')
client = Client(BUCKET_ID)
OBJECT_NAME = "subscribers.json"


def calculate_growth_and_store_in_db(symbol):
    """
    This function is now adapted to calculate the growth, and then store or update it directly 
    in the Replit db inside a structured 'growth' key with individual tickers.
    """
    try:
        # Calculate dynamic dates
        today = date.today()
        start_date = today - timedelta(days=365 * 10)  # 10 years ago
        end_date = date(today.year - 1, 12, 31)  # Last day of last year

        # Key for 'growth' data in db
        growth_db_key = "growth"

        # Check if the growth section is up-to-date
        if is_db_section_up_to_date(growth_db_key):
            print(f"{growth_db_key} is up to date, skipping update.")
            return

        # Ensure 'growth' key exists in db
        if growth_db_key not in db.keys():
            db[growth_db_key] = {}

        # Check if symbol's data is already present
        if symbol in db[growth_db_key]:
            # Retrieve and calculate if outdated
            symbol_data = db[growth_db_key][symbol]
            creation_date_obj = datetime.strptime(symbol_data['creation_date'], '%Y-%m-%d').date()
            if (today - creation_date_obj).days > 365:
                prices = yf.download(symbol, start=start_date, end=end_date, progress=False)["Adj Close"]

                if not prices.empty:
                    starting_price = prices.iloc[0]
                    ending_price = prices.iloc[-1]
                    growth_rate = ((ending_price - starting_price) / starting_price) * 100

                    # Update growth data for symbol
                    db[growth_db_key][symbol] = {
                        'ticker': symbol, 
                        'growth': growth_rate, 
                        'score': 0,  # Temporary score, will update later
                        'creation_date': today.strftime('%Y-%m-%d')
                    }
                else:
                    print(f"No data found for {symbol}")
        else:
            # Calculate and store new entry
            prices = yf.download(symbol, start=start_date, end=end_date, progress=False)["Adj Close"]
            if not prices.empty:
                starting_price = prices.iloc[0]
                ending_price = prices.iloc[-1]
                growth_rate = ((ending_price - starting_price) / starting_price) * 100

                # Initially populate db with growth data for symbol
                db[growth_db_key][symbol] = {
                    'ticker': symbol, 
                    'growth': growth_rate, 
                    'score': 0,  # Temporary score, will update later
                    'creation_date': today.strftime('%Y-%m-%d')
                }
            else:
                print(f"No data found for {symbol}")

    except Exception as e:
        print(f"Error calculating growth for {symbol}: {e}")


      
def calculate_dividends_and_store_in_db(symbol):
  """
  Calculates the overall average yearly dividend for a given stock symbol and stores it in the db.
  """
  dividends_db_key = "dividends"
  
  # Check if the growth section is up-to-date
  if is_db_section_up_to_date(dividends_db_key):
      print(f"{dividends_db_key} is up to date, skipping update.")
      return
    
  try:
    today = date.today()
    if dividends_db_key not in db.keys():
        db[dividends_db_key] = {}
    symbol_data = db[dividends_db_key].get(symbol)
    if symbol_data:
        creation_date_obj = datetime.strptime(symbol_data['creation_date'], '%Y-%m-%d').date()
        if (today - creation_date_obj).days <= 365:
            return
    avg_yearly_dividend = calculate_yearly_dividends(symbol)

    if avg_yearly_dividend is not None:
        db[dividends_db_key][symbol] = {
            'ticker': symbol,
            'average_yearly_dividend': avg_yearly_dividend,
            'score': 0,  # Temporary score, will update later
            'creation_date': today.strftime('%Y-%m-%d')
        }
    else:
        print(f"No dividend data found for {symbol}")
  except Exception as e:
    print(f"Error storing dividend data for {symbol}: {e}")


def calculate_yearly_dividends(symbol):
  """Calculates the overall average yearly dividend for a given stock symbol.

  Args:
      symbol: The stock ticker symbol.

  Returns:
      The overall average yearly dividend, or None if an error occurs or no dividend data is found.
  """
  try:
      ticker = yf.Ticker(symbol)
      dividend_history = ticker.dividends

      if dividend_history.empty:
          return None

      yearly_dividend_sum = dividend_history.resample('YE').sum()

      # Calculate total dividend and number of years
      total_dividend = yearly_dividend_sum.sum()
      num_years = len(yearly_dividend_sum)

      # Calculate and return the overall average 
      return total_dividend / num_years if num_years > 0 else None

  except Exception as e:
      print(f"Error calculating yearly dividends for {symbol}: {e}")
      return None


def calculate_marketcap_and_store_in_db(symbol):
  """
  Calculates market cap of a given stock symbol and stores it in the db.
  """
  try:
      today = date.today()
      marketcap_db_key = "marketcap"

      # Check if the marketcap section is up-to-date
      if is_db_section_up_to_date(marketcap_db_key):
          print(f"{marketcap_db_key} is up to date, skipping update.")
          return
        
      if marketcap_db_key not in db.keys():
          db[marketcap_db_key] = {}
        
      if symbol in db[marketcap_db_key]:
        # Retrieve and calculate if outdated
        symbol_data = db[marketcap_db_key][symbol]
        creation_date_obj = datetime.strptime(symbol_data['creation_date'], '%Y-%m-%d').date()
        if (today - creation_date_obj).days > 30:
          company_info = yf.Ticker(symbol).info
          if "marketCap" in company_info and company_info["marketCap"] is not None:
              market_cap = company_info["marketCap"]
              db[marketcap_db_key][symbol] = {
                  'ticker': symbol,
                  'marketCap': market_cap,
                  'score': 0,  # Temporary score, will update later
                  'creation_date': date.today().strftime('%Y-%m-%d')
              }
      else:
          # Logic for adding a new symbol to the marketcap database
          company_info = yf.Ticker(symbol).info
          if "marketCap" in company_info and company_info["marketCap"] is not None:
              market_cap = company_info["marketCap"]
              db[marketcap_db_key][symbol] = {
                  'ticker': symbol,
                  'marketCap': market_cap,
                  'score': 0,  # Temporary score, will update later
                  'creation_date': date.today().strftime('%Y-%m-%d')
              }

  except Exception as e:
      print(f"Error calculating market cap for {symbol}: {e}")

    

def calculate_gnumber_and_store_in_db(symbol):
  """
  Checks Graham Number against current price, and stores the company if G-Number is higher,
  only if the data is older than 30 days.
  Args:
      symbol: A ticker symbol as a string.
  """
  gnumber_db_key = "gnumber"
  
  # Check if the growth section is up-to-date
  if is_db_section_up_to_date(gnumber_db_key):
      print(f"{gnumber_db_key} is up to date, skipping update.")
      return
    
  try:
      today = date.today()

      if gnumber_db_key not in db.keys():
          db[gnumber_db_key] = {}

      # Check if data is outdated
      symbol_data = db[gnumber_db_key].get(symbol)
      if symbol_data:
          creation_date_obj = datetime.strptime(symbol_data['Creation Date'], '%Y-%m-%d').date()
          if (today - creation_date_obj).days <= 1:
              # Data is not outdated, no need to update
              return

      data = yf.Ticker(symbol)
      datainfo = data.info
      # Check for necessary data
      if "netIncomeToCommon" not in datainfo or "sharesOutstanding" not in datainfo or "bookValue" not in datainfo:
          print(f"Necessary data missing for {symbol}")
          return
      earningpershare = datainfo.get("netIncomeToCommon", 0) / datainfo.get("sharesOutstanding", 1)
      bookvaluepershare = datainfo.get("bookValue", 0) / datainfo.get("sharesOutstanding", 1)

      if earningpershare <= 0 or bookvaluepershare <= 0:
          print(f"Invalid EPS or Book Value per Share for {symbol}")
          return

      gnumber = math.sqrt(22.5 * earningpershare * bookvaluepershare) * 10000
      current_price = yf.download(symbol, progress=False, period="1d")["Close"].iloc[-1]  # Use -1 to get the latest closing price

      if gnumber > current_price:
          db[gnumber_db_key][symbol] = {
              "GNumber": gnumber,
              "Current Price": current_price,
              "score": 0,  # Placeholder score
              "Creation Date": today.strftime("%Y-%m-%d")
          }

  except Exception as e:
      print(f"Error processing {symbol}: {e}")


    
def calculate_current_ratio(symbol):
  """
  Calculates the current ratio of a company by retrieving its balance sheet data from Yahoo Finance.

  Args:
      symbol (str): The ticker symbol of the company.

  Returns:
      tuple: A tuple containing the current ratio, current assets, and current liabilities, or None if an error occurs.
  """
  try:
      data = yf.Ticker(symbol).balance_sheet

      # Fetching Current Assets and Current Liabilities
      total_assets_row = data[data.index == 'Current Assets']
      total_liabilities_row = data[data.index == 'Current Liabilities']

      if total_assets_row.empty or total_liabilities_row.empty:
        return None

      current_assets = float(total_assets_row.iloc[0, 0])
      current_liabilities = float(total_liabilities_row.iloc[0, 0])

      if current_liabilities == 0:
          print(f"Current liabilities for {symbol} is zero")
          return None  # Avoid division by zero

      current_ratio = current_assets / current_liabilities

      return current_ratio, current_assets, current_liabilities
  except Exception as e:
      print(f"Error calculating current ratio for {symbol}: {e}")
      return None


def calculate_health_and_store_in_db(symbol):
  """
  Calculates the health (using the current ratio as a metric) of a company and stores or updates
  the record in the Replit db within a 'health' key, considering the freshness of existing data.

  Args:
  symbol (str): The ticker symbol of the company.
  """
  health_db_key = "health"
  # Check if the health section is up-to-date
  if is_db_section_up_to_date(health_db_key):
      print(f"{health_db_key} is up to date, skipping update.")
      return
    
  try:
      today = date.today()
      # Ensure 'health' key exists in db
      if health_db_key not in db.keys():
          db[health_db_key] = {}
      # Check if symbol's data is already present and fresh
      if symbol in db[health_db_key]:
          symbol_data = db[health_db_key][symbol]
          creation_date_obj = datetime.strptime(symbol_data['Creation Date'], '%Y-%m-%d').date()
          if (today - creation_date_obj).days <= 30:
              # Data is fresh, no need to update
              return
      # Calculate health
      result = calculate_current_ratio(symbol)
      if result is not None:
          current_ratio, current_assets, current_liabilities = result
          if current_ratio > 2:
            db[health_db_key][symbol] = {
                "Ticker": symbol,
                "Health": current_ratio,
                "Current Assets": current_assets,
                "Current Liabilities": current_liabilities,
                "Creation Date": today.strftime('%Y-%m-%d'),
                "score": 0  # Placeholder for score, to be updated later
            }
      else:
          print(f"Could not calculate health for {symbol}")
  except Exception as e:
      print(f"Error processing health for {symbol}: {e}")

    

def assign_scores(update_db=True):
  """
  Assigns scores to each ticker based on their growth, with the highest growth receiving the highest score.
  """
  #growth
  growth_data = db["growth"]
  sorted_tickers = sorted(growth_data.items(), key=lambda x: x[1]['growth'], reverse=True)
  total_tickers = len(sorted_tickers)
  # Assigning scores based on inverse position
  for rank, (ticker, data) in enumerate(sorted_tickers, start=1):
      inverse_score = total_tickers - rank + 1
      data['score'] = inverse_score
      if update_db:
          db["growth"][ticker] = data
  
  #dividend
  dividend_data = db["dividends"]
  # Calculate scores inversely related to rank (bigger dividend -> lower rank number -> higher score)
  scored_dividend_tickers = sorted(dividend_data.items(), key=lambda x: x[1]['average_yearly_dividend'], reverse=True)
  highest_dividend_score = len(scored_dividend_tickers)  # Start scores from the total count of items
  for rank, (ticker, data) in enumerate(scored_dividend_tickers, start=1):
      # Assign scores such that the biggest payer has the highest score
      data['score'] = highest_dividend_score - rank + 1
      if update_db:
          dividend_data[ticker] = data

  # MarketCap
  marketcap_data = db["marketcap"]
  sorted_tickers_by_marketcap = sorted(marketcap_data.items(), key=lambda x: x[1]['marketCap'], reverse=True)
  for rank, (ticker, data) in enumerate(sorted_tickers_by_marketcap, start=1):
      inverse_score = len(sorted_tickers_by_marketcap) - rank + 1
      data['score'] = inverse_score
      if update_db:
          db["marketcap"][ticker] = data

  # GNumber
  gnumber_data = db["gnumber"]
  sorted_gnumbers = sorted(gnumber_data.items(), key=lambda x: x[1]['GNumber'], reverse=True)
  total_gnumbers = len(sorted_gnumbers)
  for rank, (ticker, data) in enumerate(sorted_gnumbers, start=1):
      inverse_score = total_gnumbers - rank + 1
      data['score'] = inverse_score
      if update_db:
          db["gnumber"][ticker] = data

  # Health - Added scoring based on Current Ratio
  health_data = db["health"]
  sorted_health_tickers = sorted(health_data.items(), key=lambda x: x[1].get('Health', -float('inf')), reverse=True)
  total_health_tickers = len(sorted_health_tickers)
  for rank, (ticker, data) in enumerate(sorted_health_tickers, start=1):
      score = total_health_tickers - rank + 1  # Higher current ratio gets higher score
      data['score'] = score
      if update_db:
          db["health"][ticker] = data


def common_symbols():
  # Constants for the database keys
  DB_KEYS = ['growth', 'dividends', 'health', 'gnumber', 'marketcap']
  # Initialize a dictionary for the common symbols
  common_symbols_db = {}
  # Step 1: Fetch symbols from each database and store in a set for comparison
  symbol_sets = [set(db[key].keys()) for key in DB_KEYS if key in db.keys()]
  # Step 2: Identify common symbols across all databases
  common_symbols_set = set.intersection(*symbol_sets)
  # Iterate through each common symbol to gather scores
  for symbol in common_symbols_set:
      # Initialize dictionary to store scores and total score
      symbol_data = {'total_score': 0}
      # Gather and sum scores for the symbol from each category
      for db_key in DB_KEYS:
          # Safety check if symbol exists in the category
          if symbol in db[db_key]:
              score = db[db_key][symbol].get('score', 0)
              symbol_data[db_key] = score
              symbol_data['total_score'] += score
          else:
              # In case the symbol is not found in one of the databases, which shouldn't happen as we've filtered common symbols
              symbol_data[db_key] = 0
      # Step 3: Store symbol data in the common symbols dictionary
      common_symbols_db[symbol] = symbol_data
  # Step 4: Update db with the common symbols and their scores
  db['common_symbols'] = common_symbols_db

  post_common_symbols_data(common_symbols_db)


def send_email():
  subscribers = fetch_data()
  print(subscribers)

  my_email = 'mda.learn@gmail.com'
  password = os.environ.get('EMAIL_PASSWORD')

  for subscriber in subscribers:  # Iterate directly over list
      email = subscriber.get('email')  # Access email from subscriber dict
      name = subscriber.get('username', 'subscriber')  # Default to 'subscriber' if username not found

      # Fetch common symbols data from another project's database
      try:
          common_symbols_db = db['common_symbols']
          # Assuming it returns a list of dictionaries representing each symbol, convert it to a Pandas DataFrame
          common_symbols_df = pd.DataFrame.from_dict(common_symbols_db, orient='index')
          print(common_symbols_df)
          top_symbols_html = common_symbols_df.to_html(index=True)  # Convert to HTML table
      except Exception as e:  # Catching all exceptions to handle both connection and conversion errors
          top_symbols_html = "<p>No common symbols data found for today.</p>"

      # Construct the HTML message with subscriber's name
      html_message = f"""
      <html>
      <head></head>
      <body>
          <p>Hi {name},</p>

          <p>Here are the stocks trading for less than their true value that I found today:</p>
          {top_symbols_html.replace('<td>', '<td style="text-align: center;">')}  

          <p>Pick one and start growing your future wealth!</p>

          <p>Oracle of Omaha</p><br>
          <small><i>This is for informational purposes only. For financial advice, consult a professional.</i></small><br>
          <small><i>We are in beta testing, please answer this 3 simple multiple choice <a href="https://forms.gle/5TZuPSrTDgxcpNx1A">questions</a> to help us improve.</i></small><br>
          <small><i>Click <a href="https://oracleofomaha.replit.app">here</a> to unsubscribe.</i></small>
      </body>
      </html>
      """

      # Construct the message (MIMEMultipart for mixed content)
      message = MIMEMultipart('alternative')  # 'alternative' allows for both text and html
      message['Subject'] = "Oracle of Omaha - check today stocks opportunities!" 
      message['From'] = my_email
      message['To'] = email

      # Attach the HTML part
      html_part = MIMEText(html_message, 'html')   
      message.attach(html_part)

      # Send the email using smtplib
      with smtplib.SMTP('smtp.gmail.com', 587) as connection:
          connection.starttls()
          connection.login(user=my_email, password=password)
          connection.sendmail(
              from_addr=my_email,
              to_addrs=email,
              msg=message.as_string()  # Convert to string for sending
          )



# Function to check if a db section is up to date
def is_db_section_up_to_date(section_key, update_interval_days=None):
  """
  Check if a database section is up to date.
  Parameters:
      section_key (str): The key for the section in the database.
      update_interval_days (int, optional): Override the default update interval for specific sections. Defaults to None.
  Returns:
      bool: True if the section is up to date, else False.
  """
  # Dynamic update intervals based on the section being checked
  update_intervals = {
      'marketcap': 30,
      'health': 30,
      'dividends': 365,
      'growth': 365,
      'gnumber': 1
  }
  if update_interval_days is None:
      update_interval_days = update_intervals.get(section_key, 30)  # Default to 30 days if not specified
  last_update_key = f'{section_key}_last_update'
  if last_update_key in db.keys():
      last_update_date = datetime.strptime(db[last_update_key], '%Y-%m-%d').date()
      if (date.today() - last_update_date).days < update_interval_days:
          return True
  else:
    # This is the condition for when the update key doesn't exist, implying a first creation scenario.
    mark_db_section_as_updated(section_key)  # Ensure an update date is set on first check
    return False


# Function to mark a db section as updated
def mark_db_section_as_updated(section_key):
    last_update_key = f'{section_key}_last_update'
    db[last_update_key] = date.today().strftime('%Y-%m-%d')


def fetch_data():
  url = 'https://omaha-proxy.replit.app/get_subscribers'  # Replace with your actual URL
  response = requests.get(url)
  if response.status_code == 200:
      return response.json()  # Parse and return JSON data if request was successful
  else:
      return None  # Handle errors or invalid responses as necessary
    
def post_common_symbols_data(data):
  common_symbols_data = [{key: {'total_score': value["total_score"], "growth": value["growth"], "dividends": value["dividends"], "health": value["health"], "gnumber": value['gnumber'], 'marketcap': value['marketcap']}} for key, value in data.items()]
  # Convert to JSON formatted string
  content_to_post = json.dumps(common_symbols_data, indent=4)
  url = os.environ.get('POST_COMMON_SYMBOLS')
  headers = {'Content-Type': 'application/json'}
  try:
      response = requests.post(url, json=content_to_post, headers=headers)
      if response.status_code == 200:
          print('Data successfully sent to the server.')
      else:
          print(f'Failed to send data. Status Code: {response.status_code}. Response: {response.text}')
  except Exception as e:
      print(f"An error occurred while sending data: {e}")


def post_gnumber_data():
  """Sends 'gnumber' data to the server as JSON."""
  gnumber_data = db.get("gnumber")  
  if gnumber_data:
    gnumber_data_dict = []
    for ticker, data in gnumber_data.items():
        # Round GNumber and Current Price to 2 decimal places using round()
        rounded_gnumber = round(data['GNumber'], 2)
        rounded_price = round(data['Current Price'], 2)

        # Create the dictionary with rounded values
        data_dict = {
            'ticker': ticker,
            'GNumber': rounded_gnumber,
            'Current Price': rounded_price,
            'score': data['score']
        }
        gnumber_data_dict.append(data_dict)
    content_to_post = json.dumps(gnumber_data_dict, indent=4)
    url = os.environ.get('POST_GNUMBER_URL')  # Replace with your actual URL
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=content_to_post, headers=headers)
        if response.status_code == 200:
            print('GNumber data successfully sent to the server.')
        else:
            print(f'Failed to send GNumber data. Status Code: {response.status_code}. Response: {response.text}')
    except Exception as e:
        print(f"An error occurred while sending GNumber data: {e}")
  else:
    print("The 'gnumber' section does not exist in the database.")


def post_growth_data():
  """Sends 'growth' data to the server as JSON."""
  growth_data = db["growth"]  # Assuming 'growth' is a dictionary in your Replit db
  content_to_post = json.dumps(growth_data, indent=4)
  url = os.environ.get('POST_GROWTH_URL')  # Replace with your actual URL
  headers = {'Content-Type': 'application/json'}
  try:
      response = requests.post(url, json=content_to_post, headers=headers)
      if response.status_code == 200:
          print('Growth data successfully sent to the server.')
      else:
          print(f'Failed to send growth data. Status Code: {response.status_code}. Response: {response.text}')
  except Exception as e:
      print(f"An error occurred while sending growth data: {e}")


def post_dividends_data():
  """Sends 'dividends' data to the server as JSON."""
  dividends_data = db["dividends"]
  content_to_post = json.dumps(dividends_data, indent=4)
  url = os.environ.get('POST_DIVIDENDS_URL')  # Replace with your actual URL
  headers = {'Content-Type': 'application/json'}
  try:
      response = requests.post(url, json=content_to_post, headers=headers)
      if response.status_code == 200:
          print('Dividends data successfully sent to the server.')
      else:
          print(f'Failed to send dividends data. Status Code: {response.status_code}. Response: {response.text}')
  except Exception as e:
      print(f"An error occurred while sending dividends data: {e}")


def post_health_data():
  """Sends 'health' data to the server as JSON."""
  health_data = db["health"]
  content_to_post = json.dumps(health_data, indent=4)
  url = os.environ.get('POST_HEALTH_URL')  # Replace with your actual URL
  headers = {'Content-Type': 'application/json'}
  try:
      response = requests.post(url, json=content_to_post, headers=headers)
      if response.status_code == 200:
          print('Health data successfully sent to the server.')
      else:
          print(f'Failed to send health data. Status Code: {response.status_code}. Response: {response.text}')
  except Exception as e:
      print(f"An error occurred while sending health data: {e}")


def post_marketcap_data():
  """Sends 'marketcap' data to the server as JSON."""
  marketcap_data = db["marketcap"]
  content_to_post = json.dumps(marketcap_data, indent=4)
  url = os.environ.get('POST_MARKETCAP_URL')  # Replace with your actual URL
  headers = {'Content-Type': 'application/json'}
  try:
      response = requests.post(url, json=content_to_post, headers=headers)
      if response.status_code == 200:
          print('MarketCap data successfully sent to the server.')
      else:
          print(f'Failed to send MarketCap data. Status Code: {response.status_code}. Response: {response.text}')
  except Exception as e:
      print(f"An error occurred while sending MarketCap data: {e}")


# # ==================== MAIN SCRIPT ====================

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
sp500_df = pd.read_html(url)[0]
sp500_symbols = sp500_df["Symbol"].to_list()

test = ['SNA', 'EG', 'AIZ', 'UHS', 'RL', 'GL', 'CMA', 'MTB', 'NVR', 'BG', 'AMD', 'TSLA', 'META']

# if not is_db_section_up_to_date("marketcap"):
#   for ticker in sp500_symbols:
#       calculate_marketcap_and_store_in_db(ticker)
#   mark_db_section_as_updated("marketcap")
#   assign_scores()
#   post_marketcap_data()


# if not is_db_section_up_to_date("health"):
#   for ticker in sp500_symbols:
#       calculate_health_and_store_in_db(ticker)
#   mark_db_section_as_updated("health")
#   assign_scores()
#   post_health_data()

# if not is_db_section_up_to_date("growth"):
#   for ticker in sp500_symbols:
#       calculate_growth_and_store_in_db(ticker)
#   mark_db_section_as_updated("growth")
#   assign_scores()
#   post_growth_data()

# if not is_db_section_up_to_date("dividends"):
#   for ticker in sp500_symbols:
#       calculate_dividends_and_store_in_db(ticker)
#   mark_db_section_as_updated("dividends")
#   assign_scores()
#   post_dividends_data()

# if not is_db_section_up_to_date("gnumber"):
#   for ticker in sp500_symbols:
#       calculate_gnumber_and_store_in_db(ticker)
#   mark_db_section_as_updated("gnumber")
#   assign_scores()
#   post_gnumber_data()


# common_symbols()
# send_email()
post_gnumber_data()