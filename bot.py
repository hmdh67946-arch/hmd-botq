import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "Gold Scalping Cashback Bot (M1) is active!"

async def trading_loop():
    print("=== Starting Gold Scalping Cashback Bot Worker ===", flush=True)
    
    token = (
        os.environ.get('METIAPI_TOKEN') or 
        os.environ.get('METAAPI_TOKEN') or 
        os.environ.get('TOKEN')
    )
    account_id = '0f7c93b4-3c22-47c3-8be2-f9eaaf46a3f5'
    
    if not token:
        print("ERROR: MetaApi Token is missing!", flush=True)
        return

    try:
        metaapi = MetaApi(token)
        print(f"Connecting to MetaApi account: {account_id}...", flush=True)
        account = await metaapi.metatrader_account_api.get_account(account_id)
        
        if account.state != 'DEPLOYED':
            print("Deploying account...", flush=True)
            await account.deploy()
            
        print("Waiting for RPC connection...", flush=True)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        symbol = 'XAUUSD.ecn'
        volume = 0.01
        num_orders = 5
        target_profit = 0.05  # هدف صافي الربح للمجموعة بالدولار
        max_loss = -5.00      # حد الخسارة للمجموعة بالدولار
        
        print(f"Bot successfully initialized for {symbol}. Starting trading loop...", flush=True)
        
        while True:
            try:
                # 1. التحقق من الصفقات المفتوحة الحالية (إدارة الأرباح والخسائر للمجموعة)
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    if total_net_profit >= target_profit or total_net_profit <= max_loss:
                        action_type = "TAKE PROFIT" if total_net_profit >= target_profit else "STOP LOSS"
                        print(f"[{action_type}] Group net PnL reached: {total_net_profit:.2f}$. Closing all positions...", flush=True)
                        
                        for p in group_positions:
                            try:
                                await connection.close_position(p.get('id'))
                            except Exception as close_err:
                                print(f"Error closing position: {close_err}", flush=True)
                        
                        print("Group closed. Entering cooldown...", flush=True)
                        await asyncio.sleep(10)
                    
                    await asyncio.sleep(2)
                    continue

                # 2. البحث عن إشارة دخول جديدة على فريم M1
                candles = await connection.get_historical_candles(symbol, '1m', 100)
                if not candles or len(candles) < 60:
                    await asyncio.sleep(10)
                    continue
                
                df = pd.DataFrame(candles)
                close = df['close']
                
                ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
                ema13 = close.ewm(span=13, adjust=False).mean().iloc[-1]
                ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
                
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                
                current_price = close.iloc[-1]
                prev_candle_bullish = df['close'].iloc[-2] > df['open'].iloc[-2]
                prev_candle_bearish = df['close'].iloc[-2] < df['open'].iloc[-2]
                
                tick = await connection.get_symbol_price(symbol)
                spread = tick.get('ask', 0) - tick.get('bid', 0)
                max_allowed_spread = 0.50
                
                if spread > max_allowed_spread:
                    await asyncio.sleep(5)
                    continue

                buy_condition = (
                    ema5 > ema13 and
                    current_price > ema50 and
                    current_rsi > 55 and
                    prev_candle_bullish
                )

                sell_condition = (
                    ema5 < ema13 and
                    current_price < ema50 and
                    current_rsi < 45 and
                    prev_candle_bearish
                )

                if buy_condition:
                    print(f"=== BUY SIGNAL DETECTED on {symbol} ===", flush=True)
                    for i in range(num_orders):
                        try:
                            res = await connection.create_market_buy_order(
                                symbol=symbol,
                                volume=volume,
                                stop_loss=0,
                                take_profit=0
                            )
                            print(f"-> Buy Order {i+1}/{num_orders} opened.", flush=True)
                        except Exception as ord_err:
                            print(f"-> Failed buy order: {ord_err}", flush=True)
                        await asyncio.sleep(0.3)
                        
                elif sell_condition:
                    print(f"=== SELL SIGNAL DETECTED on {symbol} ===", flush=True)
                    for i in range(num_orders):
                        try:
                            res = await connection.create_market_sell_order(
                                symbol=symbol,
                                volume=volume,
                                stop_loss=0,
                                take_profit=0
                            )
                            print(f"-> Sell Order {i+1}/{num_orders} opened.", flush=True)
                        except Exception as ord_err:
                            print(f"-> Failed sell order: {ord_err}", flush=True)
                        await asyncio.sleep(0.3)

                await asyncio.sleep(15)

            except Exception as loop_err:
                print(f"Error in trading loop: {loop_err}", flush=True)
                await asyncio.sleep(10)

    except Exception as e:
        print(f"Critical MetaApi Error: {e}", flush=True)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(trading_loop())

if __name__ == '__main__':
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
