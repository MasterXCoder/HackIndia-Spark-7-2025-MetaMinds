import requests
import sys
import time
import re
import schedule
import json
import spacy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import os
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("btc_advisor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BTC_Advisor")

class BTCTradingAdvisor:
    def _init_(self):
        logger.info("Initializing BTCTradingAdvisor...")
        
        # Set up TensorFlow
        self.setup_tensorflow()
        
        # Load NLP model
        self.load_nlp_model()
        
        # Store the current strategy from user input
        self.current_strategy = None
        self.parsed_strategy = None
        
        # Track previous price for comparison
        self.previous_price = None
        
        # Market state
        self.market_state = {
            "current_price": None,
            "price_change_5min": None,
            "price_change_1hr": None,
            "volume_24h": None,
            "last_updated": None
        }
        
        # Price history for analysis
        self.price_history = []
        self.timestamps = []
        self.max_history_length = 1440  # 2 hours of 5-second data points
        
        # ML model parameters
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.prediction_model_trained = False
        self.lookback_period = 60  # 5 minutes of data for prediction
        
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            
        # Flag to control the main loop
        self.running = False
        
    def setup_tensorflow(self):
        """Configure TensorFlow settings"""
        try:
            # Check TensorFlow version
            logger.info(f"TensorFlow version: {tf._version_}")
            
            # Set memory growth to avoid consuming all GPU memory
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                logger.info(f"Found {len(gpus)} GPU(s)")
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            else:
                logger.info("No GPU found, using CPU")
                
            # Disable eager execution for better performance with LSTM
            tf.compat.v1.disable_eager_execution()
            
            # Set up logging level for TensorFlow
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=all, 1=info, 2=warning, 3=error
            
            logger.info("TensorFlow setup complete")
        except Exception as e:
            logger.error(f"Error setting up TensorFlow: {e}")
    
    def load_nlp_model(self):
        """Load the spaCy NLP model with error handling"""
        try:
            logger.info("Loading NLP model...")
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("NLP model loaded successfully!")
        except OSError:
            logger.warning("NLP model not found. Downloading now...")
            try:
                # If model not found, download it
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], 
                               check=True, capture_output=True)
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("NLP model downloaded and loaded successfully!")
            except Exception as e:
                logger.error(f"Failed to download NLP model: {e}")
                # Fallback to simple regex-based parsing if NLP fails
                self.nlp = None
                logger.warning("Using fallback regex-based parsing instead of NLP")
    
    def get_btc_price(self):
        """Fetch real-time BTC price data from multiple sources with failover"""
        apis = [
            {"name": "Coinbase", "url": "https://api.coinbase.com/v2/prices/BTC-USD/spot", 
             "parser": lambda r: float(r.json()["data"]["amount"])},
            {"name": "Binance", "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", 
             "parser": lambda r: float(r.json()["price"])},
            {"name": "CoinGecko", "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", 
             "parser": lambda r: float(r.json()["bitcoin"]["usd"])}
        ]
        
        for api in apis:
            try:
                logger.debug(f"Trying to fetch price from {api['name']}...")
                response = requests.get(api["url"], timeout=5)
                
                if response.status_code == 200:
                    price = api["parser"](response)
                    timestamp = datetime.now()
                    
                    # Update price history
                    self.price_history.append(price)
                    self.timestamps.append(timestamp)
                    
                    # Trim history if needed
                    if len(self.price_history) > self.max_history_length:
                        self.price_history.pop(0)
                        self.timestamps.pop(0)
                    
                    # Calculate price changes
                    if len(self.price_history) >= 60:  # 5 minutes (60 * 5 seconds)
                        self.market_state["price_change_5min"] = ((price / self.price_history[-60]) - 1) * 100
                    
                    if len(self.price_history) >= 720:  # 1 hour
                        self.market_state["price_change_1hr"] = ((price / self.price_history[0]) - 1) * 100
                    
                    # Update current price and timestamp
                    self.market_state["current_price"] = price
                    self.market_state["last_updated"] = timestamp.strftime("%H:%M:%S")
                    
                    # Save data to CSV periodically (every 100 data points)
                    if len(self.price_history) % 100 == 0:
                        self.save_data_to_csv()
                    
                    # Try to get 24h volume if available
                    try:
                        if api["name"] == "Coinbase":
                            volume_response = requests.get("https://api.coinbase.com/v2/products/BTC-USD/stats", timeout=5)
                            volume_data = volume_response.json()
                            if "data" in volume_data and "volume" in volume_data["data"]:
                                self.market_state["volume_24h"] = float(volume_data["data"]["volume"])
                    except Exception:
                        pass  # Ignore volume errors
                    
                    return price
                
            except Exception as e:
                logger.warning(f"Error fetching BTC price from {api['name']}: {e}")
        
        logger.error("Failed to fetch price from all APIs")
        return None
    
    def save_data_to_csv(self):
        """Save price history to CSV file"""
        try:
            df = pd.DataFrame({
                'timestamp': self.timestamps,
                'price': self.price_history
            })
            df.to_csv('data/btc_price_history.csv', index=False)
            logger.debug("Price history saved to CSV")
        except Exception as e:
            logger.error(f"Error saving data to CSV: {e}")
    
    def load_historical_data(self):
        """Load historical price data if available"""
        try:
            if os.path.exists('data/btc_price_history.csv'):
                df = pd.read_csv('data/btc_price_history.csv')
                # Convert timestamp strings to datetime objects
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Only load recent data (last 2 hours)
                cutoff_time = datetime.now() - timedelta(hours=2)
                df = df[df['timestamp'] > cutoff_time]
                
                if not df.empty:
                    self.timestamps = df['timestamp'].tolist()
                    self.price_history = df['price'].tolist()
                    
                    logger.info(f"Loaded {len(self.price_history)} historical price points")
                    
                    # Update market state with loaded data
                    if len(self.price_history) > 0:
                        self.market_state["current_price"] = self.price_history[-1]
                        self.market_state["last_updated"] = self.timestamps[-1].strftime("%H:%M:%S")
                        
                        if len(self.price_history) >= 60:
                            self.market_state["price_change_5min"] = ((self.price_history[-1] / self.price_history[-60]) - 1) * 100
                        
                        if len(self.price_history) >= 720:
                            self.market_state["price_change_1hr"] = ((self.price_history[-1] / self.price_history[0]) - 1) * 100
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    def build_ml_model(self):
        """Build and compile the LSTM model for price prediction"""
        try:
            logger.info("Building LSTM model for price prediction...")
            
            # Define the LSTM model
            model = Sequential()
            
            # Add LSTM layers with dropout to prevent overfitting
            model.add(LSTM(units=50, return_sequences=True, input_shape=(self.lookback_period, 1)))
            model.add(Dropout(0.2))
            
            model.add(LSTM(units=50, return_sequences=False))
            model.add(Dropout(0.2))
            
            # Output layer for price prediction
            model.add(Dense(units=1))
            
            # Compile the model
            model.compile(optimizer='adam', loss='mean_squared_error')
            
            logger.info("LSTM model built successfully")
            self.model = model
            
            return model
        except Exception as e:
            logger.error(f"Error building ML model: {e}")
            return None
    
    def preprocess_data_for_prediction(self):
        """Prepare price data for LSTM model"""
        try:
            if len(self.price_history) < self.lookback_period + 10:
                logger.warning("Not enough data for prediction yet")
                return None, None
            
            # Scale the data
            data = np.array(self.price_history).reshape(-1, 1)
            scaled_data = self.scaler.fit_transform(data)
            
            # Create sequences for LSTM
            X, y = [], []
            
            for i in range(self.lookback_period, len(scaled_data)):
                X.append(scaled_data[i - self.lookback_period:i, 0])
                y.append(scaled_data[i, 0])
            
            # Convert to numpy arrays
            X, y = np.array(X), np.array(y)
            
            # Reshape X to match LSTM input shape: [samples, time steps, features]
            X = np.reshape(X, (X.shape[0], X.shape[1], 1))
            
            return X, y
        except Exception as e:
            logger.error(f"Error preprocessing data: {e}")
            return None, None
    
    def train_prediction_model(self):
        """Train the LSTM model with current data"""
        try:
            # Ensure we have a model
            if self.model is None:
                self.build_ml_model()
            
            # Prepare data
            X, y = self.preprocess_data_for_prediction()
            if X is None or len(X) < 30:  # Need at least 30 samples for meaningful training
                logger.warning("Not enough data for model training")
                return False
            
            logger.info(f"Training model with {len(X)} samples...")
            
            # Define early stopping to prevent overfitting
            early_stopping = EarlyStopping(
                monitor='loss',
                patience=5,
                min_delta=0.001
            )
            
            # Train the model
            self.model.fit(
                X, y,
                epochs=50,
                batch_size=32,
                verbose=1,
                callbacks=[early_stopping]
            )
            
            self.prediction_model_trained = True
            logger.info("Model training completed")
            return True
        except Exception as e:
            logger.error(f"Error training prediction model: {e}")
            return False
    
    def predict_future_price(self, minutes_ahead=5):
        """Predict BTC price X minutes into the future"""
        try:
            if not self.prediction_model_trained or len(self.price_history) < self.lookback_period:
                logger.warning("Model not trained yet or insufficient data")
                return None
            
            # Get the most recent sequence
            data = np.array(self.price_history[-self.lookback_period:]).reshape(-1, 1)
            scaled_data = self.scaler.transform(data)
            
            # Prepare the input sequence
            X_test = scaled_data.reshape(1, self.lookback_period, 1)
            
            # Make the initial prediction
            predicted_scaled = self.model.predict(X_test)
            
            # For multiple steps ahead
            current_sequence = scaled_data.reshape(self.lookback_period, 1)
            
            for _ in range(minutes_ahead * 12):  # 12 data points per minute (5-second intervals)
                # Reshape the current sequence for prediction
                current_input = current_sequence.reshape(1, self.lookback_period, 1)
                
                # Predict the next value
                next_pred = self.model.predict(current_input)
                
                # Update the sequence by removing the first value and adding the prediction
                current_sequence = np.append(current_sequence[1:], next_pred)
                current_sequence = current_sequence.reshape(self.lookback_period, 1)
                
                # Store the final prediction
                predicted_scaled = next_pred
            
            # Inverse transform to get the actual price
            predicted_price = self.scaler.inverse_transform(predicted_scaled)[0][0]
            
            logger.info(f"Predicted price {minutes_ahead} minutes ahead: ${predicted_price:.2f}")
            return predicted_price
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return None
    
    def extract_numbers(self, text):
        """Extract numbers from text, handling k notation"""
        numbers = []
        
        if self.nlp is None:
            # Fallback to regex if NLP is not available
            # Match decimal numbers
            decimal_matches = re.findall(r'\b\d+\.\d+\b', text)
            for match in decimal_matches:
                numbers.append(float(match))
                
            # Match integers with potential k suffix
            int_matches = re.findall(r'\b(\d+)(?:k|K)?\b', text)
            for match in int_matches:
                if 'k' in text[text.find(match):text.find(match) + len(match) + 1].lower():
                    numbers.append(float(match) * 1000)
                else:
                    numbers.append(float(match))
                
            return numbers
        
        # Process with spaCy if available
        doc = self.nlp(text)
        
        # Extract numerical entities
        for token in doc:
            if token.like_num:
                value = token.text
                
                # Handle "k" or "K" suffix (e.g., 30k = 30,000)
                if token.i + 1 < len(doc) and doc[token.i + 1].lower_ in ['k', 'thousand']:
                    try:
                        numbers.append(float(value) * 1000)
                    except ValueError:
                        pass
                else:
                    try:
                        numbers.append(float(value))
                    except ValueError:
                        pass
        
        return numbers
    
    def parse_user_strategy(self, user_input):
        """Process user's natural language strategy using NLP"""
        try:
            # Store the raw strategy
            self.current_strategy = user_input
            
            # Initialize strategy structure
            strategy = {
                "buy_conditions": [],
                "sell_conditions": [],
                "hold_conditions": [],
                "thresholds": {}
            }
            
            if self.nlp is None:
                # Fallback to regex-based parsing
                return self._parse_with_regex(user_input)
            
            # Process with spaCy
            doc = self.nlp(user_input.lower())
            
            # Find action verbs and associated conditions
            for token in doc:
                # Identify buy/sell actions
                if token.lemma_ in ["buy", "invest", "purchase"]:
                    action = "buy"
                elif token.lemma_ in ["sell", "deinvest", "exit"]:
                    action = "sell"
                else:
                    continue
                
                # Find nearby price mentions with currency symbols
                price_found = False
                for i in range(max(0, token.i - 5), min(len(doc), token.i + 10)):
                    t = doc[i]
                    if t.is_currency or t.text == '$':
                        # Look for numbers near currency symbols
                        for j in range(max(0, i - 2), min(len(doc), i + 3)):
                            if doc[j].like_num:
                                price_str = doc[j].text
                                # Handle k notation (e.g., "30k")
                                if j + 1 < len(doc) and doc[j + 1].text.lower() == 'k':
                                    price = float(price_str) * 1000
                                else:
                                    try:
                                        price = float(price_str.replace(',', ''))
                                    except ValueError:
                                        continue
                                
                                if action == "buy":
                                    strategy["thresholds"]["buy_price"] = price
                                else:
                                    strategy["thresholds"]["sell_price"] = price
                                price_found = True
                                break
                    if price_found:
                        break
            
            # Extract percentage-based conditions using regex (more reliable than NLP for this)
            pct_pattern = r"(\b(?:buy|sell|invest|deinvest)\b).?(\b\d+(?:\.\d+)?)\s(%|percent)"
            pct_matches = re.finditer(pct_pattern, user_input.lower())
            for match in pct_matches:
                action, value, _ = match.groups()
                pct = float(value)
                
                if action in ["buy", "invest"]:
                    # Check context for price direction
                    if any(word in user_input.lower() for word in ["drops", "falls", "decreases", "down", "declining"]):
                        strategy["buy_conditions"].append(f"price_drop_pct:{pct}")
                    elif any(word in user_input.lower() for word in ["rises", "increases", "up", "climbing", "growing"]):
                        strategy["buy_conditions"].append(f"price_rise_pct:{pct}")
                elif action in ["sell", "deinvest"]:
                    if any(word in user_input.lower() for word in ["drops", "falls", "decreases", "down", "declining"]):
                        strategy["sell_conditions"].append(f"price_drop_pct:{pct}")
                    elif any(word in user_input.lower() for word in ["rises", "increases", "up", "climbing", "growing"]):
                        strategy["sell_conditions"].append(f"price_rise_pct:{pct}")
            
            # Check for time windows
            if re.search(r"1\s*min|one\s*minute", user_input, re.IGNORECASE):
                strategy["timeframe"] = "1min"
            elif re.search(r"5\s*min|five\s*minutes", user_input, re.IGNORECASE):
                strategy["timeframe"] = "5min"
            elif re.search(r"1\s*hour|one\s*hour", user_input, re.IGNORECASE):
                strategy["timeframe"] = "1hour"
            else:
                # Default to 5min
                strategy["timeframe"] = "5min"
            
            logger.info(f"Parsed strategy: {json.dumps(strategy, indent=2)}")
            self.parsed_strategy = strategy
            return strategy
            
        except Exception as e:
            logger.error(f"Error parsing user strategy: {e}")
            # Fallback to regex parsing
            return self._parse_with_regex(user_input)
    
    def _parse_with_regex(self, user_input):
        """Fallback method to parse strategy using regex when NLP fails"""
        try:
            strategy = {
                "buy_conditions": [],
                "sell_conditions": [],
                "hold_conditions": [],
                "thresholds": {}
            }
            
            # Extract price thresholds
            buy_price_pattern = r"(?:buy|invest|purchase).?\$\s(\d+(?:,\d+)*(?:\.\d+)?|\d+(?:\.\d+)?k)"
            buy_matches = re.findall(buy_price_pattern, user_input.lower())
            
            for match in buy_matches:
                price_str = match.replace(',', '')
                if 'k' in price_str.lower():
                    price = float(price_str.lower().replace('k', '')) * 1000
                else:
                    price = float(price_str)
                strategy["thresholds"]["buy_price"] = price
            
            sell_price_pattern = r"(?:sell|deinvest|exit).?\$\s(\d+(?:,\d+)*(?:\.\d+)?|\d+(?:\.\d+)?k)"
            sell_matches = re.findall(sell_price_pattern, user_input.lower())
            
            for match in sell_matches:
                price_str = match.replace(',', '')
                if 'k' in price_str.lower():
                    price = float(price_str.lower().replace('k', '')) * 1000
                else:
                    price = float(price_str)
                strategy["thresholds"]["sell_price"] = price
            
            # Extract percentage movements
            pct_pattern = r"(buy|sell|invest|deinvest).?(rise|drop|fall|increase|decrease|up|down|grows|declines).?(\d+(?:\.\d+)?)\s*(%|percent)"
            pct_matches = re.finditer(pct_pattern, user_input.lower())
            
            for match in pct_matches:
                action, direction, value, _ = match.groups()
                pct = float(value)
                
                if action in ["buy", "invest"]:
                    if direction in ["drop", "fall", "decrease", "down", "declines"]:
                        strategy["buy_conditions"].append(f"price_drop_pct:{pct}")
                    elif direction in ["rise", "increase", "up", "grows"]:
                        strategy["buy_conditions"].append(f"price_rise_pct:{pct}")
                elif action in ["sell", "deinvest"]:
                    if direction in ["drop", "fall", "decrease", "down", "declines"]:
                        strategy["sell_conditions"].append(f"price_drop_pct:{pct}")
                    elif direction in ["rise", "increase", "up", "grows"]:
                        strategy["sell_conditions"].append(f"price_rise_pct:{pct}")
            
            # Check for time windows
            if re.search(r"1\s*min|one\s*minute", user_input, re.IGNORECASE):
                strategy["timeframe"] = "1min"
            elif re.search(r"5\s*min|five\s*minutes", user_input, re.IGNORECASE):
                strategy["timeframe"] = "5min"
            elif re.search(r"1\s*hour|one\s*hour", user_input, re.IGNORECASE):
                strategy["timeframe"] = "1hour"
            else:
                # Default to 5min
                strategy["timeframe"] = "5min"
            
            logger.info(f"Parsed strategy with regex: {json.dumps(strategy, indent=2)}")
            self.parsed_strategy = strategy
            return strategy
            
        except Exception as e:
            logger.error(f"Error in regex parsing: {e}")
            return {
                "buy_conditions": [],
                "sell_conditions": [],
                "hold_conditions": [],
                "thresholds": {},
                "timeframe": "5min"
            }
    
    def evaluate_strategy(self, current_price):
        """Evaluate the current market against user's strategy"""
        if not self.current_strategy:
            return "NO_STRATEGY", ["No strategy has been defined"]
        
        if not current_price or not self.previous_price:
            self.previous_price = current_price
            return "HOLD", ["Not enough data yet"]
        
        # Use cached parsed strategy if available
        strategy = self.parsed_strategy
        if not strategy:
            strategy = self.parse_user_strategy(self.current_strategy)
        
        # Calculate current price change percentage
        price_change_pct = ((current_price / self.previous_price) - 1) * 100
        
        # Decision logic based on strategy
        decision = "HOLD"  # Default is to hold
        reasons = []
        
        # Add market context information
        reasons.append(f"Current price: ${current_price:.2f}")
        if self.market_state["price_change_5min"] is not None:
            reasons.append(f"5-minute price change: {self.market_state['price_change_5min']:.2f}%")
        if self.market_state["price_change_1hr"] is not None:
            reasons.append(f"1-hour price change: {self.market_state['price_change_1hr']:.2f}%")
        
        # Get price prediction if model is trained
        if self.prediction_model_trained:
            prediction_5min = self.predict_future_price(5)
            if prediction_5min:
                predicted_change = ((prediction_5min / current_price) - 1) * 100
                reasons.append(f"Predicted price in 5 minutes: ${prediction_5min:.2f} ({predicted_change:+.2f}%)")
        
        # Check price thresholds
        if "thresholds" in strategy:
            if "buy_price" in strategy["thresholds"] and current_price <= strategy["thresholds"]["buy_price"]:
                reasons.append(f"Current price ${current_price:.2f} <= buy threshold ${strategy['thresholds']['buy_price']:.2f}")
                decision = "INVEST"
            if "sell_price" in strategy["thresholds"] and current_price >= strategy["thresholds"]["sell_price"]:
                reasons.append(f"Current price ${current_price:.2f} >= sell threshold ${strategy['thresholds']['sell_price']:.2f}")
                decision = "DEINVEST"
        
        # Check price change conditions
        for condition in strategy.get("buy_conditions", []):
            if condition.startswith("price_drop_pct:"):
                threshold = float(condition.split(":")[1])
                # Check if price dropped by specified percentage
                if price_change_pct <= -threshold:
                    reasons.append(f"Price dropped by {abs(price_change_pct):.2f}% which exceeds {threshold}% threshold")
                    decision = "INVEST"
            elif condition.startswith("price_rise_pct:"):
                threshold = float(condition.split(":")[1])
                if price_change_pct >= threshold:
                    reasons.append(f"Price rose by {price_change_pct:.2f}% which exceeds {threshold}% threshold")
                    decision = "INVEST"
        
        for condition in strategy.get("sell_conditions", []):
            if condition.startswith("price_drop_pct:"):
                threshold = float(condition.split(":")[1])
                if price_change_pct <= -threshold:
                    reasons.append(f"Price dropped by {abs(price_change_pct):.2f}% which exceeds {threshold}% threshold")
                    decision = "DEINVEST"
            elif condition.startswith("price_rise_pct:"):
                threshold = float(condition.split(":")[1])
                if price_change_pct >= threshold:
                    reasons.append(f"Price rose by {price_change_pct:.2f}% which exceeds {threshold}% threshold")
                    decision = "DEINVEST"
        
        return decision, reasons
    
    def check_market(self):
        """Regularly check the market and evaluate the strategy"""
        try:
            # Get the current price
            current_price = self.get_btc_price()
            
            # Initialize previous_price if needed
            if self.previous_price is None and current_price is not None:
                self.previous_price = current_price
                logger.info(f"Initial price: ${current_price:.2f}")
                return
            
            # Skip evaluation if we couldn't get the price
            if current_price is None:
                logger.warning("Skipping strategy evaluation due to missing price data")
                return
            
            # Evaluate the strategy
            decision, reasons = self.evaluate_strategy(current_price)
            
            # Log the decision and reasons
            logger.info(f"Decision: {decision}")
            for reason in reasons:
                logger.info(f"  - {reason}")
            
            # Store the current price for the next comparison
            self.previous_price = current_price
            
            # Trigger model training if we have enough data and haven't trained yet
            if len(self.price_history) >= self.lookback_period + 50 and not self.prediction_model_trained:
                logger.info("Starting initial model training...")
                # Train in a separate thread to avoid blocking
                threading.Thread(target=self.train_prediction_model).start()
            
            # Retrain model periodically (every 100 new data points)
            elif self.prediction_model_trained and len(self.price_history) % 100 == 0:
                logger.info("Retraining prediction model with new data...")
                threading.Thread(target=self.train_prediction_model).start()
                
        except Exception as e:
            logger.error(f"Error in market check: {e}")
    
    def plot_price_history(self):
        """Generate and save price history plot"""
        try:
            if len(self.price_history) < 2:
                logger.warning("Not enough data to generate plot")
                return
            
            plt.figure(figsize=(12, 6))
            
            # Convert timestamps to matplotlib-friendly format
            if isinstance(self.timestamps[0], str):
                plot_times = [datetime.strptime(t, "%Y-%m-%d %H:%M:%S") for t in self.timestamps]
            else:
                plot_times = self.timestamps
                
            # Plot price history
            plt.plot(plot_times, self.price_history, 'b-', label='BTC Price')
            
            # Add moving averages if we have enough data
            if len(self.price_history) >= 12:  # 1-minute moving average
                ma_1min = pd.Series(self.price_history).rolling(window=12).mean()
                plt.plot(plot_times, ma_1min, 'r-', label='1-min MA')
                
            if len(self.price_history) >= 60:  # 5-minute moving average
                ma_5min = pd.Series(self.price_history).rolling(window=60).mean()
                plt.plot(plot_times, ma_5min, 'g-', label='5-min MA')
            
            # Add buy/sell strategy thresholds if available
            if self.parsed_strategy and "thresholds" in self.parsed_strategy:
                if "buy_price" in self.parsed_strategy["thresholds"]:
                    buy_price = self.parsed_strategy["thresholds"]["buy_price"]
                    plt.axhline(y=buy_price, color='g', linestyle='--', label=f'Buy at ${buy_price}')
                    
                if "sell_price" in self.parsed_strategy["thresholds"]:
                    sell_price = self.parsed_strategy["thresholds"]["sell_price"]
                    plt.axhline(y=sell_price, color='r', linestyle='--', label=f'Sell at ${sell_price}')
            
            # Add predicted price if model is trained
            if self.prediction_model_trained:
                predicted_price = self.predict_future_price(5)  # 5 minutes ahead
                if predicted_price:
                    plt.plot(plot_times[-1] + timedelta(minutes=5), predicted_price, 'mo', markersize=8, label='5-min Prediction')
            
            # Add chart details
            plt.title('Bitcoin Price History')
            plt.xlabel('Time')
            plt.ylabel('Price (USD)')
            plt.grid(True)
            plt.legend(loc='best')
            
            # Format x-axis to show time
            plt.gcf().autofmt_xdate()
            
            # Save the plot
            plt.savefig('data/btc_price_chart.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info("Price history chart saved to data/btc_price_chart.png")
        except Exception as e:
            logger.error(f"Error generating price history plot: {e}")
    
    def start(self):
        """Start the trading advisor"""
        logger.info("Starting BTCTradingAdvisor...")
        
        # Load historical data if available
        self.load_historical_data()
        
        # Start monitoring BTC price
        self.running = True
        
        # Schedule regular market checks
        schedule.every(5).seconds.do(self.check_market)
        
        # Schedule model retraining
        schedule.every(1).hours.do(lambda: threading.Thread(target=self.train_prediction_model).start())
        
        # Schedule chart generation
        schedule.every(15).minutes.do(self.plot_price_history)
        
        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt detected, stopping advisor...")
                self.stop()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
    
    def stop(self):
        """Stop the trading advisor"""
        logger.info("Stopping BTCTradingAdvisor...")
        self.running = False
        
        # Final save of data
        self.save_data_to_csv()
        
        # Generate final chart
        self.plot_price_history()
        
        logger.info("BTC Trading Advisor stopped")

    def get_market_summary(self):
        """Get a summary of current market conditions"""
        if not self.market_state["current_price"]:
            return "Market data not available yet. Please try again later."
        
        summary = []
        summary.append(f"Current BTC Price: ${self.market_state['current_price']:.2f}")
        
        if self.market_state["price_change_5min"] is not None:
            summary.append(f"5-minute change: {self.market_state['price_change_5min']:+.2f}%")
            
        if self.market_state["price_change_1hr"] is not None:
            summary.append(f"1-hour change: {self.market_state['price_change_1hr']:+.2f}%")
            
        if self.market_state["volume_24h"] is not None:
            summary.append(f"24-hour volume: ${self.market_state['volume_24h']:,.2f}")
            
        if self.prediction_model_trained:
            prediction_5min = self.predict_future_price(5)
            if prediction_5min:
                predicted_change = ((prediction_5min / self.market_state["current_price"]) - 1) * 100
                summary.append(f"Predicted price (5 min): ${prediction_5min:.2f} ({predicted_change:+.2f}%)")
                
        if self.current_strategy:
            decision, _ = self.evaluate_strategy(self.market_state["current_price"])
            summary.append(f"Current strategy decision: {decision}")
            
        summary.append(f"Last updated: {self.market_state['last_updated']}")
        
        return "\n".join(summary)
    
    def save_model(self):
        """Save the trained ML model"""
        if self.model and self.prediction_model_trained:
            try:
                # Create models directory if it doesn't exist
                if not os.path.exists('models'):
                    os.makedirs('models')
                
                # Save the model and scaler
                self.model.save('models/btc_price_model.h5')
                
                # Save the scaler
                with open('models/scaler.pkl', 'wb') as f:
                    import pickle
                    pickle.dump(self.scaler, f)
                
                logger.info("Model and scaler saved successfully")
                return True
            except Exception as e:
                logger.error(f"Error saving model: {e}")
                return False
        return False
    
    def load_model(self):
        """Load a previously trained ML model"""
        try:
            # Check if model file exists
            if os.path.exists('models/btc_price_model.h5') and os.path.exists('models/scaler.pkl'):
                # Load the model
                self.model = tf.keras.models.load_model('models/btc_price_model.h5')
                
                # Load the scaler
                with open('models/scaler.pkl', 'rb') as f:
                    import pickle
                    self.scaler = pickle.load(f)
                
                self.prediction_model_trained = True
                logger.info("Model and scaler loaded successfully")
                return True
            else:
                logger.info("No saved model found")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def export_data(self, format='csv'):
        """Export collected price data in the specified format"""
        try:
            if len(self.price_history) < 1:
                logger.warning("No data to export")
                return False
            
            # Create exports directory if it doesn't exist
            if not os.path.exists('exports'):
                os.makedirs('exports')
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == 'csv':
                df = pd.DataFrame({
                    'timestamp': self.timestamps,
                    'price': self.price_history
                })
                
                filename = f'exports/btc_data_{timestamp}.csv'
                df.to_csv(filename, index=False)
                logger.info(f"Data exported to {filename}")
                return filename
                
            elif format.lower() == 'json':
                data = {
                    'data': [
                        {'timestamp': str(ts), 'price': price} 
                        for ts, price in zip(self.timestamps, self.price_history)
                    ],
                    'metadata': {
                        'export_time': datetime.now().isoformat(),
                        'data_points': len(self.price_history),
                        'time_range': f"{str(self.timestamps[0])} to {str(self.timestamps[-1])}"
                    }
                }
                
                filename = f'exports/btc_data_{timestamp}.json'
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Data exported to {filename}")
                return filename
                
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False

# Web Interface using Flask
def create_web_interface():
    """Create a Flask web interface for the BTC Trading Advisor"""
    try:
        from flask import Flask, render_template, request, jsonify, send_file
        
        app = Flask(__name__)
        
        # Create BTC advisor instance
        advisor = BTCTradingAdvisor()
        
        # Start advisor in a separate thread
        advisor_thread = threading.Thread(target=advisor.start)
        advisor_thread.daemon = True
        advisor_thread.start()
        
        @app.route('/')
        def index():
            return render_template('index.html')
        
        @app.route('/api/market-data')
        def market_data():
            return jsonify(advisor.market_state)
        
        @app.route('/api/price-history')
        def price_history():
            history = {
                'timestamps': [str(ts) for ts in advisor.timestamps],
                'prices': advisor.price_history
            }
            return jsonify(history)
        
        @app.route('/api/submit-strategy', methods=['POST'])
        def submit_strategy():
            strategy = request.form.get('strategy')
            if not strategy:
                return jsonify({'status': 'error', 'message': 'No strategy provided'})
            
            parsed = advisor.parse_user_strategy(strategy)
            return jsonify({
                'status': 'success', 
                'strategy': parsed,
                'message': 'Strategy submitted successfully'
            })
        
        @app.route('/api/get-summary')
        def get_summary():
            summary = advisor.get_market_summary()
            return jsonify({'summary': summary})
        
        @app.route('/api/get-chart')
        def get_chart():
            # Generate a fresh chart
            advisor.plot_price_history()
            return send_file('data/btc_price_chart.png', mimetype='image/png')
        
        @app.route('/api/export-data')
        def export_data():
            format = request.args.get('format', 'csv')
            filepath = advisor.export_data(format)
            if filepath:
                return send_file(filepath, as_attachment=True)
            else:
                return jsonify({'status': 'error', 'message': 'Failed to export data'})
        
        return app
    
    except Exception as e:
        logger.error(f"Error creating web interface: {e}")
        return None

# Main application entry point
if __name__ == "__main__":
    try:
        # Check if web interface is requested
        if "--web" in sys.argv:
            import sys
            app = create_web_interface()
            if app:
                logger.info("Starting web interface on http://localhost:5000")
                app.run(host="0.0.0.0", port=5000, debug=False)
            else:
                logger.error("Failed to create web interface")
        else:
            # Command-line interface
            advisor = BTCTradingAdvisor()
            
            # Add CLI commands processing
            import argparse
            
            parser = argparse.ArgumentParser(description='BTC Trading Advisor')
            parser.add_argument('--strategy', help='Set trading strategy')
            parser.add_argument('--monitor', action='store_true', help='Start monitoring mode')
            parser.add_argument('--export', choices=['csv', 'json'], help='Export data in specified format')
            
            args = parser.parse_args()
            
            if args.strategy:
                advisor.parse_user_strategy(args.strategy)
                print(f"Strategy set: {args.strategy}")
                
            if args.export:
                # First collect some data
                print("Collecting price data before export...")
                for _ in range(10):
                    advisor.get_btc_price()
                    time.sleep(5)
                
                # Export the data
                filepath = advisor.export_data(args.export)
                if filepath:
                    print(f"Data exported to {filepath}")
                else:
                    print("Failed to export data")
            
            if args.monitor or not (args.strategy or args.export):
                print("Starting BTC price monitoring...")
                advisor.start()
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")