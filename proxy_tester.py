import threading
import requests

class ProxyTester:
    @staticmethod
    def test_proxies_async(proxy_list, update_callback, final_callback):
        results = {"alive": [], "dead": []}
        total = len(proxy_list)
        completed_count = [0]
        lock = threading.Lock()
        
        if total == 0:
            final_callback(results)
            return

        def worker(p):
            req_p = {"http": f"http://{p}", "https": f"http://{p}"}
            is_alive = False
            try:
                r = requests.get("https://api.ipify.org?format=json", proxies=req_p, timeout=5)
                if r.status_code == 200:
                    is_alive = True
            except:
                pass
                
            with lock:
                if is_alive:
                    results["alive"].append(p)
                else:
                    results["dead"].append(p)
                completed_count[0] += 1
                c = completed_count[0]
                
            update_callback(c, total, p, is_alive)
            
            if c == total:
                final_callback(results)
                
        for p in proxy_list:
            threading.Thread(target=worker, args=(p,), daemon=True).start()
