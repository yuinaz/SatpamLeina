# Windows notifier for SatpamBot
# Usage: pip install win10toast requests
# python tools/windows_notifier.py --url https://<host>/heartbeat --interval 60
import argparse, time, requests, sys
try:
    from win10toast import ToastNotifier
except Exception as e:
    print("Please install win10toast: pip install win10toast"); sys.exit(1)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', required=True)
    p.add_argument('--interval', type=int, default=60)
    p.add_argument('--grace', type=int, default=120)
    args = p.parse_args()
    toaster = ToastNotifier()
    last_state = None
    while True:
        try:
            r = requests.get(args.url, timeout=8).json()
            ok = r.get('ok') and r.get('data')
            online=False
            if ok:
                ts=r['data'].get('ts',0); age=int(time.time())-int(ts)
                online = age <= args.grace
            if last_state is None or online != last_state:
                toaster.show_toast("SatpamBot", "Online" if online else "Offline", duration=5, threaded=True)
                last_state = online
        except Exception:
            if last_state is not False:
                toaster.show_toast("SatpamBot", "Offline (error)", duration=5, threaded=True)
                last_state=False
        time.sleep(max(10,args.interval))

if __name__=='__main__': main()
