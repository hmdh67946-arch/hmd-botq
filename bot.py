import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "OB V6 Accurate Bot is running safely!"

async def trading_loop():
    print("=== Starting OB V6 Safe Worker ===", flush=True)
    
    token = (
        os.environ.get('METIAPI_TOKEN') or 
        os.environ.get('METAAPI_TOKEN') or 
        os.environ.get('TOKEN')
    )
    account_id = '7b045775-a813-4c07-ae98-9d1945aefe1c'
    
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
            
        print("Waiting for synchronization...", flush=True)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        symbol = 'XAUUSD.m'
        volume = 0.01
        num_orders = 3  # 3 صفقات لكل دخول بدقة
        
        # إعدادات النقاط الصحيحة للذهب
        point_size = 0.01
        tp1_points = 70   
        tp2_points = 100  
        tp3_points = 150  
        
        print(f"Bot fully synchronized for {symbol}. Safe monitoring active...", flush=True)
        
        while True:
            try:
                # مراقبة الصفقات المفتوحة لعدم تكرار الدخول
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    await asyncio.sleep(0.5)
                    continue

                # جلب الشموع لتحليل مناطق Order Blocks
                candles = await account.get_historical_candles(symbol, '3m', None, 40)
                if not candles or len(candles) < 20:
                    await asyncio.sleep(2)
                    continue
                
                df = pd.DataFrame(candles)
                highs = df['high']
                lows = df['low']
                closes = df['close']
                opens = df['open']
                hl2 = (highs + lows) / 2
                
                pivot_len = 5
                zone_bottom = lows.iloc[-pivot_len]
                zone_resistance = highs.iloc[-pivot_len]
                
                tick = await connection.get_symbol_price(symbol)
                if not tick:
                    await asyncio.sleep(0.5)
                    continue
                    
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                current_price = (bid + ask) / 2
                
                is_bullish = closes.iloc[-1] > opens.iloc[-1]
                is_bearish = closes.iloc[-1] < opens.iloc[-1]
                
                touch_support = abs(current_price - zone_bottom) < 2.0
                touch_resistance = abs(current_price - zone_resistance) < 2.0

                buy_signal = touch_support and is_bullish
                sell_signal = touch_resistance and is_bearish

                if buy_signal:
                    print(f"=== OB V6 BUY SIGNAL -> OPENING 3 ORDERS ===", flush=True)
                    sl_price = round(zone_bottom - 0.20, 2)
                    
                    tp_prices = [
                        round(ask + (tp1_points * point_size), 2),
                        round(ask + (tp2_points * point_size), 2),
                        round(ask + (tp3_points * point_size), 2)
                    ]
                    
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=sl_price, take_profit=tp_prices[i])
                        for i in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                    await asyncio.sleep(15)
                    
                elif sell_signal:
                    print(f"=== OB V6 SELL SIGNAL -> OPENING 3 ORDERS ===", flush=True)
                    sl_price = round(zone_resistance + 0.20, 2)
                    
                    tp_prices = [
                        round(bid - (tp1_points * point_size), 2),
                        round(bid - (tp2_points * point_size), 2),
                        round(bid - (tp3_points * point_size), 2)
                    ]
                    
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=sl_price, take_profit=tp_prices[i])
                        for i in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)
                    await asyncio.sleep(15)

                await asyncio.sleep(1)

            except Exception as loop_err:
                print(f"Loop error: {loop_err}", flush=True)
                await asyncio.sleep(2)

    except Exception as e:
        print(f"Critical error: {e}", flush=True)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(trading_loop())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=port)
