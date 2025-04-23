import requests
import datetime
import time
import os
import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

API_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"

# Function to fetch market data from CoinGecko with rate-limiting handling
def get_market_data(coin_id, start_date, end_date):
    """Fetch historical prices and market caps from CoinGecko with better rate-limit handling."""
    start_timestamp = int(time.mktime(datetime.datetime.strptime(start_date, "%Y-%m-%d").timetuple()))
    end_timestamp = int(time.mktime(datetime.datetime.strptime(end_date, "%Y-%m-%d").timetuple()))

    url = API_URL.format(coin_id=coin_id)
    params = {
        'vs_currency': 'usd',
        'from': start_timestamp,
        'to': end_timestamp
    }

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise error if response code is not 200
            
            # Check rate limit headers
            remaining = int(response.headers.get('X-RateLimit-Remaining', 1))
            reset_time = int(response.headers.get('X-RateLimit-Reset', time.time()))
            if remaining == 0:
                sleep_time = reset_time - time.time()
                print(f"Rate limit exceeded, sleeping for {int(sleep_time) + 10} seconds...")
                time.sleep(sleep_time + 10)  # Sleep until reset time + a buffer
                continue  # Retry the request after sleep

            data = response.json()
            if 'prices' in data and 'market_caps' in data:
                return data['prices'], data['market_caps']
            else:
                print(f"Error: No valid data found for {coin_id}.")
                return None, None
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {coin_id}, attempt {attempt+1} of {retries}: {e}")
            if attempt < retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"Failed to fetch data for {coin_id} after {retries} attempts.")
                return None, None
    return None, None

# Function to extract required metrics
def extract_price_cap_metrics(prices, market_caps):
    """Calculate required price and market cap metrics."""
    if not prices or not market_caps:
        return None  # Return None if no data is available

    price_start = prices[0][1]
    price_end = prices[-1][1]

    market_cap_start = market_caps[0][1]
    market_cap_end = market_caps[-1][1]

    prices_only = [p[1] for p in prices]
    caps_only = [c[1] for c in market_caps]

    highest_price = max(prices_only)
    lowest_price = min(prices_only)

    price_change = price_end - price_start
    market_cap_change = market_cap_end - market_cap_start

    return {
        'start_price': price_start,
        'end_price': price_end,
        'highest_price': highest_price,
        'lowest_price': lowest_price,
        'price_change': price_change,
        'start_cap': market_cap_start,
        'end_cap': market_cap_end,
        'market_cap_change': market_cap_change,
        'prices': prices,
        'market_caps': market_caps
    }

# Function to save results to CSV
def save_results_to_csv(results, coin_id, start_date, end_date):
    """Save results to CSV for general metrics."""
    os.makedirs('result_csv', exist_ok=True)

    with open(f'result_csv/{coin_id}_results.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        if file.tell() == 0:  # Write headers only if file is empty
            writer.writerow(['Coin Name', 'Start Price', 'End Price', 'Highest Price', 'Lowest Price',
                             'Price Change', 'Start Market Cap', 'End Market Cap', 'Market Cap Change'])
        writer.writerow([coin_id, results['start_price'], results['end_price'], results['highest_price'],
                         results['lowest_price'], results['price_change'], results['start_cap'],
                         results['end_cap'], results['market_cap_change']])

# Function to save histogram image (candlestick chart)
def save_histogram_image(prices, market_caps, coin_id, start_date, end_date):
    """Save a histogram image (candlestick chart) for price and market cap."""
    os.makedirs('result_histogram', exist_ok=True)

    # Prepare data for plotting
    dates = [datetime.datetime.utcfromtimestamp(p[0] / 1000) for p in prices]
    prices_only = [p[1] for p in prices]
    caps_only = [c[1] for c in market_caps]

    # Create a figure and axis
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot Price as line
    ax1.plot(dates, prices_only, color='tab:blue', label='Price', linewidth=2)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price (USD)', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Create a second y-axis for Market Cap
    ax2 = ax1.twinx()
    ax2.plot(dates, caps_only, color='tab:green', label='Market Cap', linewidth=2)
    ax2.set_ylabel('Market Cap (USD)', color='tab:green')
    ax2.tick_params(axis='y', labelcolor='tab:green')

    # Format date ticks on x-axis
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_minor_locator(mdates.DayLocator())
    plt.xticks(rotation=45)

    # Add a title
    plt.title(f"Price and Market Cap for {coin_id} from {start_date} to {end_date}")

    # Save the chart as an image
    plt.tight_layout()
    plt.savefig(f'result_histogram/{coin_id}_histogram.png')

# Main function to read the input file and process data
def main():
    # Read the file line by line
    with open("input.txt", "r") as f:
        lines = f.readlines()

    for line in lines:
        if not line.strip():
            continue
        try:
            coin_id, start_date = line.strip().split()
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = start_dt + datetime.timedelta(days=7)
            end_date = end_dt.strftime("%Y-%m-%d")

            print(f"Fetching data for {coin_id} from {start_date} to {end_date}...")
            prices, market_caps = get_market_data(coin_id, start_date, end_date)

            if not prices or not market_caps:
                print(f"No data found for {coin_id} between {start_date} and {end_date}.")
                continue

            # Extract metrics
            metrics = extract_price_cap_metrics(prices, market_caps)

            if metrics:
                # Save the results to CSV
                save_results_to_csv(metrics, coin_id, start_date, end_date)
                # Save histogram chart (candlestick)
                save_histogram_image(prices, market_caps, coin_id, start_date, end_date)
                print(f"Results for {coin_id} saved to CSV and histogram chart.")
            else:
                print(f"No valid data found for {coin_id}.")

            # Sleep for 5 seconds to avoid hitting rate limits
            time.sleep(5)

        except Exception as e:
            print(f"Error processing line '{line.strip()}': {e}")

if __name__ == "__main__":
    main()











