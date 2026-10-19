import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "OB V6 Exact Logic Bot is active!"

def get_order_blocks(df, pivot_len=5):
    bullish_obs = []
    bearish_obs = []
    n = len(df)
    
    for i in range(pivot_len, n - pivot_len):
        # فحص القاع المحوري (Bullish OB)
        is_pivot_low = True
        for j in range(1, pivot_len + 1):
            if df['low'].iloc[i] > df['low'].iloc[i - j] or df['low'].iloc[i] > df['low'].iloc[i + j]:
                is_pivot_low = False
                break
        
        if is_pivot_low:
            z_bottom = df['low'].iloc[i]
            z_top = (df['high'].iloc[i] + df['low'].iloc[i]) / 2
            # فحص هل المنطقة غير مختبرة (Unmitigated)
            mitigated = False
            for k in range(i + 1, n):
                if df['low'].iloc[k] < z_bottom:
                    mitigated = True
                    break
            if not mitigated:
                bullish_obs.append({'top': z_top, 'bottom': z_bottom})

        # فحص القمة المحورية (Bearish OB)
        is_pivot_high = True
        for j in range(1, pivot_len + 1):
            if df['high'].iloc[i] < df['high'].iloc[i - j] or df['high'].iloc[i] < df['high'].iloc[i + j]:
                is_pivot_high = False
                break
        
        if is_pivot_high:
            z_top = df['high'].iloc[i]
            z_bottom = (df['high'].iloc[i] + df['low'].iloc[i]) / 2
            mitigated = False
            for k in range(i + 1, n):
                if df['high'].iloc[k] > z_top:
                    mitigated = True
                    break
            if not mitigated:
                bearish_obs.append({'top': z_top, 'bottom': z_bottom})
                
    return bullish_obs, bearish_obs

async def trading_loop():
    print("=== Starting OB V6 Exact Logic Worker ===", flush=True)
    
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
            await account.deploy()
            
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        symbol = 'XAUUSD.m'
        volume = 0.01
        num_orders = 3  # 3 صفقات لكل دخول
        
        point_size = 0.01
        tp1_points = 70   
        tp2_points = 100  
        tp3_points = 150  
        
        print(f"Bot fully synchronized for {symbol}. Exact OB logic active...", flush=True)
        
        while True:
            try:
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    await asyncio.sleep(0.5)
                    continue

                candles = await account.get_historical_candles(symbol, '3m', None, 100)
                if not candles or len(candles) < 30:
                    await asyncio.sleep(2)
                    continue
                
                df = pd.DataFrame(candles)
                bull_obs, bear_obs = get_order_blocks(df, pivot_len=5)
                
                tick = await connection.get_symbol_price(symbol)
                if not tick:
                    await asyncio.sleep(0.5)
                    continue
                    
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                current_price = (bid + ask) / 2
                
                is_bullish_candle = df['close'].iloc[-1] > df['open'].iloc[-1]
                is_bearish_candle = df['close'].iloc[-1] < df['open'].iloc[-1]
                
                # فحص هل السعر الحالي يلمس أي منطقة شراء (Bullish OB) غير مختبرة
                triggered_buy = False
                buy_zone_bottom = 0
                for ob in bull_obs:
                    if ob['bottom'] <= current_price <= ob['top'] + 1.0 and is_bullish_candle:
                        triggered_buy = True
                        buy_zone_bottom = ob['bottom']
                        break

                # فحص هل السعر الحالي يلمس أي منطقة بيع (Bearish OB) غير مختبرة
                triggered_sell = False
                sell_zone_top = 0
                for ob in bear_obs:
                    if ob['bottom'] - 1.0 <= current_price <= ob['top'] and is_bearish_candle:
                        triggered_sell = True
                        sell_zone_top = ob['top']
                        break

                if triggered_buy:
                    print(f"=== OB V6 EXACT BUY SIGNAL -> OPENING 3 ORDERS ===", flush=True)
                    sl_price = round(buy_zone_bottom - 0.20, 2)
                    
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
                    await asyncio.sleep(20)
                    
                elif triggered_sell:
                    print(f"=== OB V6 EXACT SELL SIGNAL -> OPENING 3 ORDERS ===", flush=True)
                    sl_price = round(sell_zone_top + 0.20, 2)
                    
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
                    await asyncio.sleep(20)

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
