import asyncio, json, os, subprocess, tempfile, time, urllib.request
import websockets

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
user_data = os.path.join(tempfile.gettempdir(), 'edge_bench_phase2_baseline')

cmd = [
    edge_path,
    '--headless=new',
    '--remote-debugging-port=9229',
    f'--user-data-dir={user_data}',
    '--no-first-run',
    '--no-default-browser-check',
    'http://127.0.0.1:8000/?trace=1'
]

proc = subprocess.Popen(cmd)
time.sleep(3)

async def main():
    res = urllib.request.urlopen('http://localhost:9229/json')
    tabs = json.loads(res.read().decode())
    target_tab = next(t for t in tabs if '127.0.0.1:8000' in t.get('url', ''))
    ws_url = target_tab['webSocketDebuggerUrl']

    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        await asyncio.sleep(2.5) # boot settle

        msg_id = 10
        async def call(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cur_id = msg_id
            req = {'id': cur_id, 'method': method}
            if params:
                req['params'] = params
            await ws.send(json.dumps(req))
            while True:
                resp = await ws.recv()
                d = json.loads(resp)
                if d.get('id') == cur_id:
                    return d.get('result', {})

        async def eval_js(expr, await_promise=False):
            res = await call('Runtime.evaluate', {
                'expression': expr,
                'awaitPromise': await_promise,
                'returnByValue': True
            })
            return res.get('result', {}).get('value')

        print("=== 2.1 Running ForgeBench.run() 3 times ===")
        bench_runs = []
        for i in range(3):
            print(f"Run {i+1}/3 starting...")
            # make sure sidebar is closed or in initial state
            await eval_js("if (window.isSidebarVisible && window.isSidebarVisible()) window.setSidebarOpen(false);")
            await asyncio.sleep(1.0)
            data = await eval_js("window.ForgeBench.run()", await_promise=True)
            bench_runs.append(data)
            print(f"Run {i+1} complete!")
            await asyncio.sleep(1.5)

        print("=== 2.2 Idle and DOM reports ===")
        await asyncio.sleep(3.0) # touch nothing for 3s
        idle_anims = await eval_js("window.ForgeSmooth.idleReport()")
        dom_report = await eval_js("window.ForgeSmooth.domReport()")
        trace_idle = await eval_js("window.ForgeTrace && window.ForgeTrace.idleCheck ? window.ForgeTrace.idleCheck() : 'no idleCheck'")

        print("=== 2.3 Typing test (S7) ===")
        # Open app.js in editor
        await eval_js("window.openFile('app/static/app.js')", await_promise=True)
        await asyncio.sleep(1.0)
        # Record typing
        typing_js = """
        (async function() {
            const editor = document.getElementById('editor');
            if (!editor || editor.disabled) return { error: 'editor is read-only or not found' };
            editor.focus();
            const stop = window.ForgeSmooth.record('typing');
            for (let i = 0; i < 40; i++) {
                editor.value += 'x';
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                editor.dispatchEvent(new KeyboardEvent('keydown', { key: 'x', bubbles: true }));
                editor.dispatchEvent(new KeyboardEvent('keyup', { key: 'x', bubbles: true }));
                await new Promise(r => setTimeout(r, 16));
            }
            const res = stop();
            return res;
        })()
        """
        typing_result = await eval_js(typing_js, await_promise=True)
        print("Typing result:", typing_result)

        print("=== 2.4 Throttled baseline (6x CPU slowdown) ===")
        await call('Emulation.setCPUThrottlingRate', {'rate': 6})
        await asyncio.sleep(1.0)
        print("Starting 6x throttled bench...")
        throttled_run = await eval_js("window.ForgeBench.run()", await_promise=True)
        print("6x throttled bench complete!")
        await call('Emulation.setCPUThrottlingRate', {'rate': 1}) # restore

        print("=== 2.5 Backend baseline API measurements ===")
        api_timings_js = """
        (async function() {
            const endpoints = [
                '/api/status',
                '/api/fs/tree',
                '/api/git/changes',
                '/api/fs/read?path=' + encodeURIComponent('app/static/app.js')
            ];
            const results = {};
            for (const ep of endpoints) {
                const t0 = performance.now();
                const res = await fetch(ep);
                await res.text();
                results[ep] = Math.round((performance.now() - t0) * 10) / 10;
            }
            return results;
        })()
        """
        api_timings = await eval_js(api_timings_js, await_promise=True)
        print("API timings:", api_timings)

        # Freeze check verify
        verify_morph = await eval_js("window.ForgeSmooth.verifyMotion(window.__baseline_motion || '')")

        out_data = {
            'bench_runs': bench_runs,
            'idle_anims': idle_anims,
            'dom_report': dom_report,
            'trace_idle': trace_idle,
            'typing_result': typing_result,
            'throttled_run': throttled_run,
            'api_timings': api_timings
        }

        with open('baseline_raw.json', 'w', encoding='utf8') as f:
            json.dump(out_data, f, indent=2)
        print("Saved baseline_raw.json successfully!")

try:
    asyncio.run(main())
finally:
    proc.terminate()
