import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "M3 Scalping Bot is active and running!"

async def trading_loop():
    print("=== Starting M3 Scalper Worker ===", flush=True)
    
    # تثبيت التوكن ورقم الحساب مباشرة داخل الكود لضمان عدم حدوث أي خطأ
    token = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJiOTIzZTc1NmFiOWViMTFkMWZlZmM2MzY1NjQzYThhOCIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOjdiMDQ1Nzc1LWE4MTMtNGMwNy1hZTk4LTlkMTk0NWFlZmUxYyJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDo3YjA0NTc3NS1hODEzLTRjMDctYWU5OC05ZDE5NDVhZWZlMWMiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6ndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc2VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOjdiMDQ1Nzc1LWE4MTMtNGMwNy1hZTk4LTlkMTk0NWFlZmUxYyJdfSx7ImlkIjoibWV0YWFwaS1yZWFsLXRpbWUtc3RyZWFtaW5nLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6ndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc2VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOjdiMDQ1Nzc1LWE4MTMtNGMwNy1hZTk4LTlkMTk0NWFlZmUxYyJdfSx7ImlkIjoibWV0YXN0YXRzLWFwaSIsIm1ldGhvZHMiOlsibWV0YXN0YXRzLWFwaTpyZXN0pwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDo3YjA0NTc3NS1hODEzLTRjMDctYWU5OC05ZDE5NDVhZWZlMWMiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6N2IwNDU3NzUtYTgxMy00YzA3LWFlOTgtOWQxOTQ1YWVmZTFjIl19XSwiaWdub3JlUmF0ZUxpbWl0cyI6ZmFsc2UsInRva2VuSWQiOiIyMDIxMDIxMyIsImltcGVyc29uYXRlZCI6ZmFsc2UsInJlYWxVc2VySWQiOiJiOTIzZTc1NmFiOWViMTFkMWZlZmM2MzY1NjQzYThhOCIsImlhdCI6MTc5MjEwNjMyNCwiZXhwIjoxNzk5ODgyMzI0f.gvzgJ5sPHBF6KW1AG-Owa-_h2zFGwryeavhjqy9Tk5_1D-uTD5ev1MBmV7PE9m6naccNKyVzyRlfLXGajAz6PVbbwNmRKUu2947v6eRjV3tsP8D2LvRwJ-sZZ-DDEl_CULnI6QYNU1O-4de42soC0QVpiEMoeWIRYlNpgxC4tG6Dz-vLCHJ9-9IgtO5G3TbBoDvek8zH8AaXVWyOhM4fpJ4ZvpBRq_3Mu6kAy6vyVWzrdlJiPjeTv15R7_Tg7LtsNuL8IeutFEwoFl5PfHmv9FmZO0f4ipiX3AaPiITHdLja7r_znhoqj3eSx1tpzxS9E_XMawRj0eo_CrFKyNBHRKn6wg2vu1arQMDIhXQy6LWwF3gScTyQUb1mxFERrXFiIwraEEKL4j_WwgPYfGoLqUfhxwZFFz42kZSRKGm218NwsKzDPKL5umhM3gJ8S7hJu26qboN7UmBs1f8mGjf_9b3Dt291xeLsel8gz_2aX80uCZEgvfEgtGFIQV9YTJ7SGhi3oQTFk0SKsa06fxEWEVFhNhTO9_FC6z8ZXOc1h2MuABgZ_gaLl9Sn4h1DreQLmNyYWuK1JC9OPF7uvp3aFnzvrcJMLcrU6zBL3a8poJhq4xgStsi0kAv4gESYWMELtz70qnenSAYgLAJdXr5IdGuA6cASc6qRyNnqoBAx-5o"
    account_id = '7b045775-a813-4c07-ae98-9d1945aefe1c'

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
        
        symbol = 'XAUUSD.m'
        volume = 0.01
        num_orders = 5
        target_profit = 0.15  # إجمالي الربح المستهدف (0.03$ لكل صفقة)
        max_loss = -5.00      # حد الخسارة
        
        last_price = None
        print(f"Bot successfully initialized for M3 ({symbol}). Running lightning-fast loop...", flush=True)
        
        while True:
            try:
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol'] == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    if total_net_profit >= target_profit or total_net_profit <= max_loss:
                        print(f"[TARGET HIT] Net PnL: {total_net_profit:.2f}$. Closing all positions...", flush=True)
                        close_tasks = [connection.close_position(p.get('id')) for p in group_positions]
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                        await asyncio.sleep(0.5)
                    
                    await asyncio.sleep(0.1)
                    continue

                candles = await account.get_historical_candles(symbol, '3m', None, 30)
                if not candles or len(candles) < 15:
                    await asyncio.sleep(1)
                    continue
                
                df = pd.DataFrame(candles)
                close = df['close']
                
                ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
                ema13 = close.ewm(span=13, adjust=False).mean().iloc[-1]
                
                tick = await connection.get_symbol_price(symbol)
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                current_price = (bid + ask) / 2
                spread = ask - bid
                
                if spread > 0.50 or last_price is None:
                    last_price = current_price
                    await asyncio.sleep(0.2)
                    continue

                price_change = current_price - last_price
                
                buy_condition = (ema5 > ema13) and (price_change >= 0.06)
                sell_condition = (ema5 < ema13) and (price_change <= -0.06)

                if buy_condition:
                    print(f"=== BUY SIGNAL -> OPENING 5 ORDERS ===", flush=True)
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                    last_price = current_price
                    
                elif sell_condition:
                    print(f"=== SELL SIGNAL -> OPENING 5 ORDERS ===", flush=True)
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)
                    last_price = current_price

                last_price = current_price
                await asyncio.sleep(0.2)

            except Exception as loop_err:
                print(f"Loop error: {loop_err}", flush=True)
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Critical error: {e}", flush=True)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(trading_loop())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    # تشغيل حلقة المهام بشكل آمن لمنع خطأ status 1
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    
    app.run(host='0.0.0.0', port=port)
