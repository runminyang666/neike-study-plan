import http.server
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime, timedelta
import os

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        if self.path.startswith('/api/sync'):
            self.handle_sync()
        else:
            super().do_GET()
    
    def handle_sync(self):
        try:
            # Parse date parameter
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            today = datetime.now()
            
            # Default to yesterday if no date specified
            if 'date' in params:
                target_date = datetime.strptime(params['date'][0], '%Y-%m-%d')
            else:
                target_date = today - timedelta(days=1)
            
            date_str = target_date.strftime('%Y-%m-%d')
            
            # Fetch the calendar page for the target date
            url = f'https://toashore.cn/public/apps/calendar/online/index.html?date={date_str}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')
            
            # Parse the daily plan content
            tasks = self.parse_daily_plan(html)
            
            result = {
                'date': date_str,
                'tasks': tasks,
                'success': True
            }
            
        except Exception as e:
            result = {
                'date': date_str if 'date_str' in dir() else '',
                'tasks': [],
                'success': False,
                'error': str(e)
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    
    def parse_daily_plan(self, html):
        """Parse the daily plan section from the calendar HTML."""
        tasks = []
        
        # Find the "当天每日计划" section
        # Look for patterns like "6.21 内科-循环系统疾病"
        # The content appears between "当天每日计划" and "本周课程安排" or "最近获取时间"
        
        plan_section = ''
        plan_match = re.search(r'当天每日计划(.+?)本周课程安排', html, re.DOTALL)
        if plan_match:
            plan_section = plan_match.group(1)
        
        # Extract date header like "2026年6月21日 全天"
        if plan_section:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '\n', plan_section)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            for line in lines:
                # Skip date headers and section titles
                if any(skip in line for skip in ['全天', '当天每日计划', '直播安排', '直播', '预习']):
                    if '直播安排' in line or '直播' in line or '预习' in line:
                        tasks.append(line)
                    continue
                # Skip short lines and pure numbers
                if len(line) < 4:
                    continue
                tasks.append(line)
        
        # If no tasks found, try broader search
        if not tasks:
            text = re.sub(r'<[^>]+>', '\n', html)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            found_plan = False
            for line in lines:
                if '当天每日计划' in line:
                    found_plan = True
                    continue
                if found_plan:
                    if '本周课程安排' in line or '最近获取时间' in line:
                        break
                    if len(line) >= 4 and line != '搜索':
                        tasks.append(line)
        
        return tasks

if __name__ == '__main__':
    port = 8080
    server = http.server.HTTPServer(('127.0.0.1', port), ProxyHandler)
    print(f'Server running at http://127.0.0.1:{port}')
    server.serve_forever()
